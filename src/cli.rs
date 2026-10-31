//! `tiny-cli`: find DLNA renderers and control them, or stream local files.

use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom};
use std::net::IpAddr;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::Arc;
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use clap::{Args as ClapArgs, Parser, Subcommand};
use log::{LevelFilter, debug, error, info};
use percent_encoding::{AsciiSet, NON_ALPHANUMERIC, percent_decode_str, utf8_percent_encode};
use serde::Serialize;
use tiny_http::{Header, Method, Request, Response, ResponseBox, Server, StatusCode};
use ureq::http::Uri;

use crate::{HTTP_LOG, net, ssdp, xml};

const AVTRANSPORT: &str = "urn:schemas-upnp-org:service:AVTransport:1";
const SEARCH_WAIT: Duration = Duration::from_millis(1500);
const DESCRIPTION_TIMEOUT: Duration = Duration::from_secs(1);
const COMMAND_TIMEOUT: Duration = Duration::from_secs(10);
/// Characters kept as-is in served file names (RFC 3986 unreserved).
const PATH_SAFE: &AsciiSet = &NON_ALPHANUMERIC
    .remove(b'-')
    .remove(b'.')
    .remove(b'_')
    .remove(b'~');

#[derive(Parser)]
#[command(name = "tiny-cli", version, about = "A tiny DLNA sender")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// List available DLNA devices
    List {
        /// Show all device attributes, and enable verbose logs
        #[arg(short)]
        verbose: bool,
    },
    /// Stop DLNA streaming
    Stop(Target),
    /// Seek DLNA streaming
    Seek {
        #[command(flatten)]
        target: Target,
        /// The new time point, format: HH:MM:SS
        to: String,
    },
    /// Play a local video file or an http(s) URL via a DLNA device
    Play {
        video_file: String,
        #[command(flatten)]
        target: Target,
        /// Override the title
        #[arg(long)]
        title: Option<String>,
    },
}

#[derive(ClapArgs)]
struct Target {
    /// Enable verbose logs
    #[arg(short)]
    verbose: bool,
    /// Specify device by (part of) its friendly name
    #[arg(short = 'q', value_name = "QUERY")]
    query: String,
}

pub fn main() {
    let cli = Cli::parse();
    let verbose = match &cli.command {
        Command::List { verbose } => *verbose,
        Command::Stop(t) | Command::Seek { target: t, .. } | Command::Play { target: t, .. } => {
            t.verbose
        }
    };
    let level = if verbose {
        LevelFilter::Debug
    } else {
        LevelFilter::Error
    };
    let http_level = if verbose {
        LevelFilter::Info
    } else {
        LevelFilter::Error
    };
    crate::init_logging(&[("tiny_dlna", level), (HTTP_LOG, http_level)]);

    match cli.command {
        Command::List { verbose } => list(verbose),
        Command::Stop(target) => {
            let device = find_device(&target.query);
            debug!("Stopping streaming on DLNA: {}", device.control_url);
            send_or_exit(&device.control_url, xml::STOP, "Stop");
        }
        Command::Seek { target, to } => {
            let device = find_device(&target.query);
            debug!("Seek streaming to {to}: {}", device.control_url);
            send_or_exit(&device.control_url, &xml::seek(&to), "Seek");
        }
        Command::Play {
            video_file,
            target,
            title,
        } => {
            let device = find_device(&target.query);
            play(&device, &video_file, title.as_deref());
        }
    }
}

#[derive(Serialize, Debug, Default)]
struct Device {
    #[serde(skip_serializing_if = "Option::is_none")]
    control_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    friendly_name: Option<String>,
    location: String,
    st: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    usn: Option<String>,
    #[serde(skip)]
    ip: Option<IpAddr>,
}

impl Device {
    fn name(&self) -> &str {
        self.friendly_name.as_deref().unwrap_or("no-name")
    }
}

/// A device picked by name, ready to be controlled.
struct Renderer {
    control_url: String,
    ip: Option<IpAddr>,
}

/// Parse an SSDP reply; `None` unless it is an AVTransport service.
fn parse_ssdp_reply(reply: &str) -> Option<Device> {
    let mut lines = reply.split("\r\n");
    if !lines.next()?.trim_end().ends_with("200 OK") {
        return None;
    }
    let mut device = Device::default();
    for line in lines {
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        let value = value.trim().to_string();
        match key.trim().to_ascii_lowercase().as_str() {
            "location" => device.location = value,
            "usn" => device.usn = Some(value),
            "st" => device.st = value,
            _ => {}
        }
    }
    (device.st.contains(":service:AVTransport:") && !device.location.is_empty()).then_some(device)
}

fn agent(timeout: Duration) -> ureq::Agent {
    ureq::Agent::config_builder()
        .timeout_global(Some(timeout))
        .build()
        .into()
}

/// Turn a `controlURL` into an absolute URL, relative to the device's host.
fn resolve_control_url(location: &str, control: &str) -> Option<String> {
    let control = control.trim();
    if control.starts_with("http://") || control.starts_with("https://") {
        return Some(control.to_string());
    }
    let uri: Uri = location.parse().ok()?;
    let scheme = uri.scheme_str().unwrap_or("http");
    let host = uri.host()?;
    let port = uri
        .port_u16()
        .unwrap_or(if scheme == "https" { 443 } else { 80 });
    Some(format!(
        "{scheme}://{host}:{port}/{}",
        control.trim_start_matches('/')
    ))
}

/// Fill in name and control URL from the device description XML.
fn parse_description(device: &mut Device, xml_text: &str) -> Result<(), String> {
    let doc = roxmltree::Document::parse(xml_text.trim()).map_err(|e| e.to_string())?;
    let child_text = |node: roxmltree::Node, name: &str| {
        node.children()
            .find(|n| n.tag_name().name() == name)
            .and_then(|n| n.text())
            .map(str::trim)
            .filter(|t| !t.is_empty())
            .map(str::to_string)
    };
    device.friendly_name = doc
        .descendants()
        .find(|n| n.tag_name().name() == "friendlyName")
        .and_then(|n| n.text())
        .map(str::trim)
        .filter(|t| !t.is_empty())
        .map(str::to_string);
    device.control_url = doc
        .descendants()
        .filter(|n| n.tag_name().name() == "service")
        .find(|n| {
            child_text(*n, "serviceId").as_deref() == Some("urn:upnp-org:serviceId:AVTransport")
        })
        .and_then(|n| child_text(n, "controlURL"))
        .and_then(|url| resolve_control_url(&device.location, &url));
    Ok(())
}

fn fetch_description(device: &mut Device) -> Result<(), String> {
    let text = agent(DESCRIPTION_TIMEOUT)
        .get(&device.location)
        .call()
        .and_then(|mut r| r.body_mut().read_to_string())
        .map_err(|e| e.to_string())?;
    parse_description(device, &text)
}

fn discover() -> Vec<Device> {
    let replies = match ssdp::search(SEARCH_WAIT) {
        Ok(r) => r,
        Err(e) => {
            error!("SSDP search failed: {e}");
            return Vec::new();
        }
    };
    let mut seen = HashSet::new();
    let devices: Vec<Device> = replies
        .into_iter()
        .filter_map(|(addr, reply)| {
            let mut device = parse_ssdp_reply(&reply)?;
            device.ip = Some(addr.ip());
            seen.insert(device.location.clone()).then_some(device)
        })
        .collect();

    // Fetch descriptions in parallel; drop devices that don't answer.
    let handles: Vec<_> = devices
        .into_iter()
        .map(|mut d| {
            thread::spawn(move || match fetch_description(&mut d) {
                Ok(()) => Some(d),
                Err(e) => {
                    debug!("skip {}: {e}", d.location);
                    None
                }
            })
        })
        .collect();
    handles
        .into_iter()
        .filter_map(|h| h.join().ok().flatten())
        .collect()
}

fn list(verbose: bool) {
    let devices = discover();
    if verbose {
        let out = serde_json::json!({ "devices": devices });
        println!(
            "{}",
            serde_json::to_string_pretty(&out).expect("serializable")
        );
        return;
    }
    if devices.is_empty() {
        eprintln!("No DLNA devices found.");
    }
    for d in &devices {
        println!("{}", d.name());
    }
}

fn find_device(query: &str) -> Renderer {
    let devices = discover();
    let q = query.to_lowercase();
    let (matched, others): (Vec<&Device>, Vec<&Device>) = devices.iter().partition(|d| {
        d.friendly_name
            .as_ref()
            .is_some_and(|n| n.to_lowercase().contains(&q))
    });
    if let Some((d, url)) = matched
        .iter()
        .find_map(|d| d.control_url.as_ref().map(|url| (d, url)))
    {
        return Renderer {
            control_url: url.clone(),
            ip: d.ip,
        };
    }
    eprintln!("No such DLNA device found: {query}");
    let names: Vec<&str> = others.iter().chain(&matched).map(|d| d.name()).collect();
    if !names.is_empty() {
        eprintln!("Available names: {}", names.join(", "));
    }
    process::exit(1);
}

/// Send a SOAP action; failures are reported to the user.
fn send_command(control_url: &str, body: &str, action: &str) -> bool {
    let result = agent(COMMAND_TIMEOUT)
        .post(control_url)
        .header("Content-Type", "text/xml; charset=\"utf-8\"")
        .header("SOAPACTION", format!("\"{AVTRANSPORT}#{action}\""))
        .send(body);
    match result {
        Ok(_) => {
            debug!("{action} request sent");
            true
        }
        Err(e) => {
            eprintln!("{action} failed: {e}");
            false
        }
    }
}

fn send_or_exit(control_url: &str, body: &str, action: &str) {
    if !send_command(control_url, body, action) {
        process::exit(1);
    }
}

fn file_name(path: &Path) -> String {
    path.file_name()
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned()
}

fn play(device: &Renderer, video: &str, title: Option<&str>) {
    let is_url = video.starts_with("http://") || video.starts_with("https://");
    let (url_video, url_srt, title) = if is_url {
        (
            video.to_string(),
            None,
            title.unwrap_or("online stream").to_string(),
        )
    } else {
        let path = Path::new(video);
        if !path.is_file() {
            eprintln!("no such file: {video}");
            process::exit(1);
        }
        let Some(ip) = device.ip.map_or_else(net::host_ip, net::local_ip_for) else {
            eprintln!("failed to find a local IP address reachable by the device");
            process::exit(1);
        };
        let (server, port) = match bind_file_server() {
            Ok(s) => s,
            Err(e) => {
                eprintln!("failed to start file server: {e}");
                process::exit(1);
            }
        };

        info!("play video: {video}");
        let mut files = HashMap::new();
        let mut url_for = |path: &Path| {
            let name = file_name(path);
            let url = format!(
                "http://{ip}:{port}/videos/{}",
                utf8_percent_encode(&name, PATH_SAFE)
            );
            info!("serving {} at {url}", path.display());
            files.insert(
                name,
                std::path::absolute(path).unwrap_or_else(|_| path.to_path_buf()),
            );
            url
        };
        let url_video = url_for(path);
        let srt = path.with_extension("srt");
        let url_srt = srt.is_file().then(|| url_for(&srt));

        let files = Arc::new(files);
        thread::spawn(move || serve_files(server, files));
        let title = title.map_or_else(|| file_name(path), str::to_string);
        (url_video, url_srt, title)
    };

    let metadata = xml::didl_metadata(&title, &url_video, url_srt.as_deref());
    let set_av = xml::set_av_transport_uri(&url_video, &metadata);
    send_or_exit(&device.control_url, &set_av, "SetAVTransportURI");
    send_or_exit(&device.control_url, xml::PLAY, "Play");

    // Keep serving until Ctrl-C, then stop playback on the device.
    let control_url = device.control_url.clone();
    ctrlc::set_handler(move || {
        send_command(&control_url, xml::STOP, "Stop");
        process::exit(0);
    })
    .expect("failed to install signal handler");
    loop {
        thread::park();
    }
}

fn bind_file_server() -> io::Result<(Server, u16)> {
    let seed = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .subsec_nanos();
    let offset = (seed ^ process::id()) % 9000;
    let mut last_err = None;
    for i in 0..50 {
        let port = 50000 + ((offset + i) % 9000) as u16;
        match Server::http(("0.0.0.0", port)) {
            Ok(server) => return Ok((server, port)),
            Err(e) => last_err = Some(e),
        }
    }
    Err(io::Error::other(
        last_err.map_or("no free port".into(), |e| e.to_string()),
    ))
}

fn serve_files(server: Server, files: Arc<HashMap<String, PathBuf>>) {
    for request in server.incoming_requests() {
        let files = files.clone();
        thread::spawn(move || serve_one(request, &files));
    }
}

fn header(name: &str, value: &str) -> Header {
    Header::from_bytes(name.as_bytes(), value.as_bytes()).expect("valid header")
}

fn plain(status: u16, body: &str) -> ResponseBox {
    Response::from_string(body)
        .with_status_code(StatusCode(status))
        .boxed()
}

fn serve_one(request: Request, files: &HashMap<String, PathBuf>) {
    let url = request.url().to_string();
    let path = url.split('?').next().unwrap_or_default();
    let file = path
        .strip_prefix("/videos/")
        .map(|name| percent_decode_str(name).decode_utf8_lossy().into_owned())
        .and_then(|name| files.get(&name));

    let resp = match (request.method(), file) {
        (_, None) => plain(404, "Not Found"),
        (Method::Get | Method::Head, Some(path)) => {
            file_response(&request, path).unwrap_or_else(|e| {
                error!("failed to read {}: {e}", path.display());
                plain(500, "Internal Server Error")
            })
        }
        _ => plain(405, "Method Not Allowed"),
    };

    let remote = request
        .remote_addr()
        .map(|a| a.ip().to_string())
        .unwrap_or_default();
    let range = request
        .headers()
        .iter()
        .find(|h| h.field.equiv("Range"))
        .map(|h| h.value.to_string());
    log::info!(
        target: HTTP_LOG,
        "{remote} \"{} {url}\" {}{}",
        request.method(),
        resp.status_code().0,
        range.map(|r| format!(" ({r})")).unwrap_or_default()
    );
    if let Err(e) = request.respond(resp) {
        // Normal when a TV drops a connection to seek elsewhere.
        debug!("response for {url} interrupted: {e}");
    }
}

fn content_type(path: &Path) -> String {
    match path
        .extension()
        .and_then(|e| e.to_str())
        .map(str::to_ascii_lowercase)
        .as_deref()
    {
        Some("srt") => "text/srt".into(),
        Some("ts" | "m2ts" | "mts") => "video/mp2t".into(),
        _ => mime_guess::from_path(path)
            .first_or_octet_stream()
            .to_string(),
    }
}

/// Parse a single-range `Range` header against a body of `len` bytes.
/// `None`: ignore the header and send everything; `Some(Err)`: unsatisfiable.
fn parse_range(value: &str, len: u64) -> Option<Result<(u64, u64), ()>> {
    let spec = value.trim().strip_prefix("bytes=")?;
    if spec.contains(',') {
        return None;
    }
    let (start, end) = spec.split_once('-')?;
    let (start, end) = (start.trim(), end.trim());
    if start.is_empty() {
        let suffix: u64 = end.parse().ok()?;
        if suffix == 0 || len == 0 {
            return Some(Err(()));
        }
        return Some(Ok((len.saturating_sub(suffix), len - 1)));
    }
    let start: u64 = start.parse().ok()?;
    let end = if end.is_empty() {
        len.saturating_sub(1)
    } else {
        end.parse::<u64>().ok()?.min(len.saturating_sub(1))
    };
    if start >= len || start > end {
        return Some(Err(()));
    }
    Some(Ok((start, end)))
}

fn file_response(request: &Request, path: &Path) -> io::Result<ResponseBox> {
    let mut file = File::open(path)?;
    let meta = file.metadata()?;
    let len = meta.len();
    let mut headers = vec![
        header("Content-Type", &content_type(path)),
        header("Accept-Ranges", "bytes"),
    ];
    if let Ok(modified) = meta.modified() {
        headers.push(header("Last-Modified", &httpdate::fmt_http_date(modified)));
    }

    let range = request
        .headers()
        .iter()
        .find(|h| h.field.equiv("Range"))
        .and_then(|h| parse_range(h.value.as_str(), len));
    let (status, body, body_len): (u16, Box<dyn Read + Send>, u64) = match range {
        None => (200, Box::new(file), len),
        Some(Ok((start, end))) => {
            file.seek(SeekFrom::Start(start))?;
            headers.push(header(
                "Content-Range",
                &format!("bytes {start}-{end}/{len}"),
            ));
            let n = end - start + 1;
            (206, Box::new(file.take(n)), n)
        }
        Some(Err(())) => {
            headers.push(header("Content-Range", &format!("bytes */{len}")));
            (416, Box::new(io::empty()), 0)
        }
    };
    // Always send Content-Length: many TVs can't stream chunked responses.
    Ok(Response::new(
        StatusCode(status),
        headers,
        body,
        usize::try_from(body_len).ok(),
        None,
    )
    .with_chunked_threshold(usize::MAX))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ssdp_reply_parsing() {
        let reply = "HTTP/1.1 200 OK\r\nST: urn:schemas-upnp-org:service:AVTransport:1\r\n\
                     USN: uuid:x::y\r\nLOCATION: http://10.0.0.5:1234/d.xml\r\n\r\n";
        let d = parse_ssdp_reply(reply).unwrap();
        assert_eq!(d.location, "http://10.0.0.5:1234/d.xml");
        assert_eq!(d.usn.as_deref(), Some("uuid:x::y"));
        assert!(parse_ssdp_reply(&reply.replace("AVTransport", "ContentDirectory")).is_none());
        assert!(parse_ssdp_reply(&reply.replace("200 OK", "404 Not Found")).is_none());
    }

    #[test]
    fn control_url_resolution() {
        let loc = "http://10.0.0.5:1234/desc/d.xml";
        assert_eq!(
            resolve_control_url(loc, "/AVT/ctl").unwrap(),
            "http://10.0.0.5:1234/AVT/ctl"
        );
        assert_eq!(
            resolve_control_url(loc, "AVT/ctl").unwrap(),
            "http://10.0.0.5:1234/AVT/ctl"
        );
        assert_eq!(
            resolve_control_url("http://10.0.0.5/d.xml", "c").unwrap(),
            "http://10.0.0.5:80/c"
        );
        assert_eq!(
            resolve_control_url(loc, "http://other/c").unwrap(),
            "http://other/c"
        );
    }

    #[test]
    fn description_parsing() {
        let mut d = Device {
            location: "http://10.0.0.5:59876/description.xml".into(),
            ..Default::default()
        };
        parse_description(&mut d, &xml::description("Living Room & TV", "u-1")).unwrap();
        assert_eq!(d.friendly_name.as_deref(), Some("Living Room & TV"));
        assert_eq!(
            d.control_url.as_deref(),
            Some("http://10.0.0.5:59876/AVTransport/control")
        );
    }

    #[test]
    fn ranges() {
        assert_eq!(parse_range("bytes=0-", 100), Some(Ok((0, 99))));
        assert_eq!(parse_range("bytes=10-19", 100), Some(Ok((10, 19))));
        assert_eq!(parse_range("bytes=90-200", 100), Some(Ok((90, 99))));
        assert_eq!(parse_range("bytes=-10", 100), Some(Ok((90, 99))));
        assert_eq!(parse_range("bytes=-500", 100), Some(Ok((0, 99))));
        assert_eq!(parse_range("bytes=100-", 100), Some(Err(())));
        assert_eq!(parse_range("bytes=20-10", 100), Some(Err(())));
        assert_eq!(parse_range("bytes=0-1,5-6", 100), None);
        assert_eq!(parse_range("items=0-1", 100), None);
    }

    #[test]
    fn content_types() {
        assert_eq!(content_type(Path::new("a.SRT")), "text/srt");
        assert_eq!(content_type(Path::new("a.mp4")), "video/mp4");
        assert_eq!(content_type(Path::new("a.mkv")), "video/x-matroska");
        assert_eq!(content_type(Path::new("a.ts")), "video/mp2t");
    }
}
