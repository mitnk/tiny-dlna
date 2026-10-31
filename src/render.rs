//! `tiny-render`: a DLNA media renderer that plays streams with mpv.

use std::io::{Cursor, Read};
use std::path::{Path, PathBuf};
use std::process::{self, Child, Command, Stdio};
use std::thread;
use std::time::Instant;

use clap::Parser;
use log::{LevelFilter, debug, error, info};
use tiny_http::{Header, Method, Request, Response, Server, StatusCode};

use crate::{HTTP_LOG, config, ssdp, xml};

const PORT_DEFAULT: u16 = 59876;
const MAX_BODY: u64 = 1 << 20;

#[derive(Parser)]
#[command(
    name = "tiny-render",
    version,
    about = "A tiny DLNA media renderer (plays with mpv)"
)]
struct Args {
    /// Enable HTTP and SSDP server logs
    #[arg(long)]
    http_logs: bool,
    /// Enable debug logs
    #[arg(short, long)]
    verbose: bool,
    /// Specify render name
    #[arg(long)]
    name: Option<String>,
    /// Server port
    #[arg(long)]
    port: Option<u16>,
    /// Dump streaming to a file (stream recording)
    #[arg(long, value_name = "FILE")]
    dump_to: Option<PathBuf>,
}

fn friendly_name(name: Option<&str>, recording: bool) -> String {
    match (name, recording) {
        (None, false) => "Tiny Render".into(),
        (None, true) => "Tiny Recorder".into(),
        (Some(n), false) => n.into(),
        (Some(n), true) => format!("{n} (Recorder)"),
    }
}

pub fn main() {
    let args = Args::parse();

    let app_level = if args.verbose {
        LevelFilter::Debug
    } else {
        LevelFilter::Info
    };
    let net_level = if args.http_logs {
        LevelFilter::Debug
    } else {
        LevelFilter::Error
    };
    crate::init_logging(&[
        ("tiny_dlna", app_level),
        ("tiny_dlna::ssdp", net_level),
        (HTTP_LOG, net_level),
    ]);

    let dump_to = args.dump_to.as_deref().map(absolute);
    if let Some(path) = dump_to.as_ref().filter(|p| p.exists()) {
        error!("target file exists: {}", path.display());
        process::exit(1);
    }

    let port = match args.port {
        Some(p) if p != 0 => p,
        _ => PORT_DEFAULT + u16::from(dump_to.is_some()),
    };
    let server = match Server::http(("0.0.0.0", port)) {
        Ok(s) => s,
        Err(e) => {
            error!("failed to listen on port {port}: {e}");
            process::exit(1);
        }
    };

    let name = friendly_name(args.name.as_deref(), dump_to.is_some());
    let uuid = config::render_uuid(port);
    {
        let uuid = uuid.clone();
        ctrlc::set_handler(move || {
            debug!("got killing signal");
            config::unregister_render(&uuid);
            process::exit(0);
        })
        .expect("failed to install signal handler");
    }
    config::register_render(&uuid, &name, port);

    thread::spawn(ssdp::serve_forever);

    info!("Starting DLNA Receiver: {name}");
    if let Some(path) = &dump_to {
        info!("Recording stream to {}", path.display());
    }

    let mut render = Render {
        friendly_name: name,
        uuid,
        dump_to,
        media: Media::default(),
        started_at: None,
        player: Player::default(),
    };
    for request in server.incoming_requests() {
        render.handle(request);
    }
}

fn absolute(path: &Path) -> PathBuf {
    std::path::absolute(path).unwrap_or_else(|_| path.to_path_buf())
}

#[derive(Default, Debug, PartialEq)]
struct Media {
    uri: String,
    srt: String,
    title: String,
}

#[derive(Default)]
struct Player {
    child: Option<Child>,
}

impl Player {
    fn play(&mut self, media: &Media, dump_to: Option<&Path>) -> std::io::Result<()> {
        self.stop();
        let mut cmd = Command::new("mpv");
        cmd.args(["--quiet", "--screen=1", "--no-terminal"]);
        if let Some(path) = dump_to {
            cmd.arg(format!("--stream-record={}", path.display()));
        }
        if !media.title.is_empty() {
            cmd.arg(format!("--title={}", media.title));
        }
        if !media.srt.is_empty() {
            cmd.arg(format!("--sub-file={}", media.srt));
        }
        // `--` keeps a hostile URI from being parsed as an mpv option.
        cmd.arg("--").arg(&media.uri);
        debug!("running: {cmd:?}");
        self.child = Some(cmd.stdin(Stdio::null()).stderr(Stdio::null()).spawn()?);
        Ok(())
    }

    fn stop(&mut self) {
        let Some(mut child) = self.child.take() else {
            return;
        };
        terminate(&mut child);
        // Reap in the background so the old mpv doesn't linger as a zombie.
        thread::spawn(move || child.wait());
    }
}

#[cfg(unix)]
fn terminate(child: &mut Child) {
    // SIGTERM lets mpv shut down cleanly (and finish a stream recording).
    unsafe {
        libc::kill(child.id() as libc::pid_t, libc::SIGTERM);
    }
}

#[cfg(not(unix))]
fn terminate(child: &mut Child) {
    let _ = child.kill();
}

struct Render {
    friendly_name: String,
    uuid: String,
    dump_to: Option<PathBuf>,
    media: Media,
    started_at: Option<Instant>,
    player: Player,
}

type Resp = Response<Cursor<Vec<u8>>>;

fn header(name: &str, value: &str) -> Header {
    Header::from_bytes(name.as_bytes(), value.as_bytes()).expect("valid header")
}

fn respond(status: u16, content_type: &str, body: impl Into<Vec<u8>>) -> Resp {
    let body = body.into();
    let len = body.len();
    Response::new(
        StatusCode(status),
        vec![
            header("Content-Type", content_type),
            header("Server", &format!("UPnP/1.0 TinyRender/{}", crate::VERSION)),
        ],
        Cursor::new(body),
        Some(len),
        None,
    )
}

fn xml_ok(body: impl Into<Vec<u8>>) -> Resp {
    respond(200, "text/xml; charset=utf-8", body)
}

fn text(status: u16, body: &str) -> Resp {
    respond(status, "text/plain; charset=utf-8", body)
}

impl Render {
    fn handle(&mut self, mut request: Request) {
        let method = request.method().clone();
        let url = request.url().to_string();
        let path = url.split('?').next().unwrap_or_default();
        let is_get = matches!(method, Method::Get | Method::Head);

        let mut exit_after = false;
        let resp = match path {
            "/description.xml" if is_get => {
                xml_ok(xml::description(&self.friendly_name, &self.uuid))
            }
            "/dlna/AVTransport.xml" if is_get => xml_ok(xml::AVTRANSPORT_SCPD),
            "/dlna/RenderingControl.xml" if is_get => xml_ok(xml::RENDERING_CONTROL_SCPD),
            "/dlna/ConnectionManager.xml" if is_get => xml_ok(xml::CONNECTION_MANAGER_SCPD),
            "/AVTransport/control" if method == Method::Post => {
                let (resp, exit) = self.control(&mut request);
                exit_after = exit;
                resp
            }
            "/description.xml"
            | "/dlna/AVTransport.xml"
            | "/dlna/RenderingControl.xml"
            | "/dlna/ConnectionManager.xml"
            | "/AVTransport/control" => text(405, "Method Not Allowed"),
            _ => text(404, "Not Found"),
        };

        let remote = request
            .remote_addr()
            .map(|a| a.ip().to_string())
            .unwrap_or_default();
        log::info!(target: HTTP_LOG, "{remote} \"{method} {url}\" {}", resp.status_code().0);
        if let Err(e) = request.respond(resp) {
            debug!("failed to send response: {e}");
        }

        if exit_after {
            config::unregister_render(&self.uuid);
            info!("stopping the recorder as a whole; mpv process is left open");
            process::exit(0);
        }
    }

    /// Handle an AVTransport SOAP action. The flag asks the caller to exit
    /// after responding: a recorder records one stream, then quits.
    fn control(&mut self, request: &mut Request) -> (Resp, bool) {
        let mut raw = Vec::new();
        if let Err(e) = request.as_reader().take(MAX_BODY).read_to_end(&mut raw) {
            error!("failed to read request body: {e}");
            return (text(400, "Bad Request"), false);
        }
        let body = String::from_utf8_lossy(&raw);
        let soap_action = request
            .headers()
            .iter()
            .find(|h| h.field.equiv("SOAPACTION"))
            .map(|h| h.value.as_str().to_string());
        let recording_done = self.started_at.is_some() && self.dump_to.is_some();

        match soap_action_name(soap_action.as_deref(), &body).as_deref() {
            Some("SetAVTransportURI") => match parse_set_av_transport_uri(&body) {
                Ok(media) => {
                    debug!("Action: SetAV: {}", media.uri);
                    debug!("Title: {} SRT: {}", media.title, media.srt);
                    self.media = media;
                    (xml_ok(xml::SET_AV_TRANSPORT_URI_RESPONSE), false)
                }
                Err(e) => {
                    error!("bad SetAVTransportURI request: {e}");
                    (text(400, "Bad Request"), false)
                }
            },
            Some("Play") => {
                if recording_done {
                    return (xml_ok(xml::PLAY_RESPONSE), true);
                }
                debug!("action: Play: {}", self.media.uri);
                if self.media.uri.is_empty() {
                    error!("Play requested without a media URI");
                    return (text(500, "No Media"), false);
                }
                if let Err(e) = self.player.play(&self.media, self.dump_to.as_deref()) {
                    error!("failed to run mpv: {e}");
                    return (text(500, "Failed To Start Player"), false);
                }
                self.started_at = Some(Instant::now());
                (xml_ok(xml::PLAY_RESPONSE), false)
            }
            Some("GetPositionInfo") => {
                // Approximation: time since Play; mpv isn't queried.
                debug!("action: GetPositionInfo");
                let secs = self.started_at.map_or(0, |t| t.elapsed().as_secs());
                (
                    xml_ok(xml::position_info_response(&track_time(secs))),
                    false,
                )
            }
            Some("GetTransportInfo") => {
                debug!("action: GetTransportInfo");
                (xml_ok(xml::TRANSPORT_INFO_RESPONSE), false)
            }
            Some("Stop") => {
                debug!("stopping");
                if recording_done {
                    return (xml_ok(xml::STOP_RESPONSE), true);
                }
                self.media = Media::default();
                self.started_at = None;
                self.player.stop();
                (xml_ok(xml::STOP_RESPONSE), false)
            }
            Some("Seek") => {
                debug!("action: Seek");
                (xml_ok(xml::SEEK_RESPONSE), false)
            }
            _ => {
                error!("action not supported: {body}");
                (text(500, "Action Not Supported"), false)
            }
        }
    }
}

fn track_time(secs: u64) -> String {
    format!("{}:{:02}:{:02}", secs / 3600, secs % 3600 / 60, secs % 60)
}

/// The action name, from the SOAPACTION header (`"urn:...:AVTransport:1#Play"`)
/// or else from the first element inside the SOAP body.
fn soap_action_name(header: Option<&str>, body: &str) -> Option<String> {
    if let Some(name) = header
        .and_then(|h| h.trim().trim_matches('"').rsplit_once('#'))
        .map(|(_, name)| name.trim())
        .filter(|name| !name.is_empty())
    {
        return Some(name.to_string());
    }
    let doc = roxmltree::Document::parse(body.trim()).ok()?;
    let soap_body = doc.descendants().find(|n| n.has_tag_name("Body"))?;
    let action = soap_body.children().find(|n| n.is_element())?;
    Some(action.tag_name().name().to_string())
}

fn element_text<'a>(doc: &'a roxmltree::Document, name: &str) -> &'a str {
    doc.descendants()
        .find(|n| n.tag_name().name() == name)
        .and_then(|n| n.text())
        .unwrap_or_default()
}

fn parse_set_av_transport_uri(body: &str) -> Result<Media, roxmltree::Error> {
    let doc = roxmltree::Document::parse(body.trim())?;
    let uri = element_text(&doc, "CurrentURI").trim().to_string();
    let metadata = element_text(&doc, "CurrentURIMetaData");
    if metadata.trim().is_empty() {
        debug!("no metadata");
        return Ok(Media {
            uri,
            ..Media::default()
        });
    }
    let (title, srt) = parse_didl(metadata);
    Ok(Media { uri, srt, title })
}

const NS_DIDL: &str = "urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/";
const NS_DC: &str = "http://purl.org/dc/elements/1.1/";
const NS_SEC: &str = "http://www.sec.co.kr/";
const NS_PV: &str = "http://www.pv.com/pvns/";

/// Title and subtitle URL from DIDL-Lite metadata. Senders are sloppy here
/// (double-escaped XML, raw `&` in URLs), so invalid metadata is normalized
/// and retried, and as a last resort the title is found by plain text search.
fn parse_didl(metadata: &str) -> (String, String) {
    if let Ok(doc) = roxmltree::Document::parse(metadata.trim()) {
        return didl_fields(&doc);
    }
    let unescaped = xml::unescape(metadata);
    let normalized = unescaped.replace('&', "&amp;");
    match roxmltree::Document::parse(normalized.trim()) {
        Ok(doc) => didl_fields(&doc),
        Err(e) => {
            debug!("metadata is not valid XML ({e}), searching for title only");
            (title_by_search(&unescaped), String::new())
        }
    }
}

/// `(title, subtitle URL)` from a parsed DIDL-Lite document.
fn didl_fields(doc: &roxmltree::Document) -> (String, String) {
    let find = |ns: &str, name: &str| {
        doc.descendants()
            .filter(|n| n.has_tag_name((ns, name)))
            .find_map(|n| n.text().map(str::trim).filter(|t| !t.is_empty()))
            .map(str::to_string)
    };
    let title = find(NS_DC, "title").unwrap_or_default();
    let srt = find(NS_SEC, "CaptionInfoEx")
        .or_else(|| find(NS_SEC, "CaptionInfo"))
        .or_else(|| find(NS_PV, "subtitleFileUri"))
        .or_else(|| {
            doc.descendants()
                .filter(|n| n.has_tag_name((NS_DIDL, "res")))
                .filter(|n| {
                    n.attribute("type") == Some("text/subtitle")
                        || n.attribute("protocolInfo")
                            .is_some_and(|p| p.contains("text/srt"))
                })
                .find_map(|n| n.text().map(str::trim).filter(|t| !t.is_empty()))
                .map(str::to_string)
        })
        .unwrap_or_default();
    (title, srt)
}

fn title_by_search(metadata: &str) -> String {
    let Some(start) = metadata.find("<dc:title>") else {
        return String::new();
    };
    let rest = &metadata[start + "<dc:title>".len()..];
    rest.find("</dc:title>")
        .map_or("", |end| &rest[..end])
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn friendly_names() {
        assert_eq!(friendly_name(None, false), "Tiny Render");
        assert_eq!(friendly_name(None, true), "Tiny Recorder");
        assert_eq!(friendly_name(Some("TV"), true), "TV (Recorder)");
    }

    #[test]
    fn track_time_format() {
        assert_eq!(track_time(0), "0:00:00");
        assert_eq!(track_time(3725), "1:02:05");
    }

    #[test]
    fn action_from_header_or_body() {
        let hdr = Some("\"urn:schemas-upnp-org:service:AVTransport:1#Play\"");
        assert_eq!(soap_action_name(hdr, "").as_deref(), Some("Play"));
        assert_eq!(soap_action_name(None, xml::STOP).as_deref(), Some("Stop"));
        let body = xml::seek("00:01:00")
            .replace("u:", "x:")
            .replace("xmlns:u", "xmlns:x");
        assert_eq!(soap_action_name(None, &body).as_deref(), Some("Seek"));
        assert_eq!(soap_action_name(None, "garbage"), None);
    }

    #[test]
    fn set_av_roundtrip_with_subtitle() {
        let video = "http://10.0.0.2:50001/videos/a%20b.mp4?x=1&y=2";
        let srt = "http://10.0.0.2:50001/videos/a%20b.srt";
        let meta = xml::didl_metadata("A & B", video, Some(srt));
        let media = parse_set_av_transport_uri(&xml::set_av_transport_uri(video, &meta)).unwrap();
        assert_eq!(
            media,
            Media {
                uri: video.into(),
                srt: srt.into(),
                title: "A & B".into()
            }
        );
    }

    #[test]
    fn markup_in_title_keeps_subtitle() {
        let meta = xml::didl_metadata("Custom <T>", "http://h/v.mp4", Some("http://h/v.srt"));
        assert_eq!(
            parse_didl(&meta),
            ("Custom <T>".into(), "http://h/v.srt".into())
        );
    }

    #[test]
    fn double_escaped_metadata() {
        let meta = xml::escape(&xml::didl_metadata(
            "T",
            "http://h/v?a=1&b=2",
            Some("http://h/v.srt"),
        ));
        assert_eq!(parse_didl(&meta), ("T".into(), "http://h/v.srt".into()));
    }

    #[test]
    fn set_av_without_metadata() {
        let body = xml::set_av_transport_uri("http://h/v.m3u8", "");
        let media = parse_set_av_transport_uri(&body).unwrap();
        assert_eq!(media.uri, "http://h/v.m3u8");
        assert!(media.title.is_empty() && media.srt.is_empty());
    }

    #[test]
    fn broken_metadata_falls_back_to_title_search() {
        // undeclared `upnp:` prefix makes the DIDL invalid
        let meta = "<DIDL-Lite><item><dc:title>Live 1</dc:title><upnp:class>x</upnp:class></item></DIDL-Lite>";
        assert_eq!(parse_didl(meta), ("Live 1".into(), String::new()));
    }

    #[test]
    fn subtitle_from_res_type() {
        let meta = format!(
            r#"<DIDL-Lite xmlns="{NS_DIDL}" xmlns:dc="{NS_DC}"><item><dc:title>T</dc:title>
            <res protocolInfo="http-get:*:video/mp4:*">http://h/v.mp4</res>
            <res type="text/subtitle">http://h/v.srt</res></item></DIDL-Lite>"#
        );
        assert_eq!(parse_didl(&meta), ("T".into(), "http://h/v.srt".into()));
    }
}
