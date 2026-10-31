//! Files under `~/.config/tiny-dlna/`: the render UUID and the list of
//! renders currently running on this machine (shared by all processes so a
//! single SSDP listener can answer for every render).

use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use log::{debug, warn};
use serde::{Deserialize, Serialize};

const RENDER_CONFIG: &str = "tiny-render.json";
const LIVE_RENDERS: &str = "live-renders.json";

pub fn config_dir() -> PathBuf {
    let home = std::env::home_dir().unwrap_or_else(|| PathBuf::from("."));
    let dir = home.join(".config").join("tiny-dlna");
    if let Err(e) = fs::create_dir_all(&dir) {
        warn!("failed to create {}: {e}", dir.display());
    }
    dir
}

fn read_json<T: for<'de> Deserialize<'de> + Default>(path: &Path) -> T {
    match fs::read_to_string(path) {
        Ok(text) => serde_json::from_str(&text).unwrap_or_else(|e| {
            warn!("ignoring malformed {}: {e}", path.display());
            T::default()
        }),
        Err(e) if e.kind() == io::ErrorKind::NotFound => T::default(),
        Err(e) => {
            warn!("failed to read {}: {e}", path.display());
            T::default()
        }
    }
}

/// Write via a temp file + rename so concurrent readers never see a partial file.
fn write_json<T: Serialize>(path: &Path, value: &T) -> io::Result<()> {
    let mut buf = Vec::new();
    let fmt = serde_json::ser::PrettyFormatter::with_indent(b"    ");
    let mut ser = serde_json::Serializer::with_formatter(&mut buf, fmt);
    value.serialize(&mut ser)?;
    let tmp = path.with_extension(format!("json.{}.tmp", std::process::id()));
    fs::write(&tmp, &buf)?;
    fs::rename(&tmp, path)
}

#[derive(Serialize, Deserialize, Default)]
struct RenderConfig {
    #[serde(rename = "UUID", default)]
    uuid: String,
}

/// The render's UUID: a per-machine random base plus the HTTP port, so that
/// several renders on one machine get distinct but stable IDs.
pub fn render_uuid(port: u16) -> String {
    let path = config_dir().join(RENDER_CONFIG);
    let mut config: RenderConfig = read_json(&path);
    if config.uuid.is_empty() {
        let full = uuid::Uuid::new_v4().to_string();
        config.uuid = full
            .rsplit_once('-')
            .map_or(full.as_str(), |(base, _)| base)
            .to_string();
        if let Err(e) = write_json(&path, &config) {
            warn!("failed to save {}: {e}", path.display());
        }
    }
    format!("{}-{port}", config.uuid)
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct LiveRender {
    pub name: String,
    pub port: u16,
    pub uuid: String,
}

#[derive(Serialize, Deserialize, Default)]
struct LiveRenders {
    #[serde(default)]
    renders: Vec<LiveRender>,
}

fn live_renders_path() -> PathBuf {
    config_dir().join(LIVE_RENDERS)
}

pub fn register_render(uuid: &str, name: &str, port: u16) {
    let path = live_renders_path();
    let mut data: LiveRenders = read_json(&path);
    if data.renders.iter().any(|r| r.uuid == uuid) {
        return;
    }
    data.renders.push(LiveRender {
        name: name.into(),
        port,
        uuid: uuid.into(),
    });
    match write_json(&path, &data) {
        Ok(()) => debug!("registered render {uuid}"),
        Err(e) => warn!("failed to save {}: {e}", path.display()),
    }
}

pub fn unregister_render(uuid: &str) {
    let path = live_renders_path();
    let mut data: LiveRenders = read_json(&path);
    let before = data.renders.len();
    data.renders.retain(|r| r.uuid != uuid);
    if data.renders.len() == before {
        return;
    }
    match write_json(&path, &data) {
        Ok(()) => debug!("unregistered render {uuid}"),
        Err(e) => warn!("failed to save {}: {e}", path.display()),
    }
}

pub fn live_render_ports() -> Vec<u16> {
    let data: LiveRenders = read_json(&live_renders_path());
    data.renders.into_iter().map(|r| r.port).collect()
}
