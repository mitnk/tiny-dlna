//! A tiny DLNA sender (`tiny-cli`) and receiver (`tiny-render`).

pub mod cli;
pub mod config;
pub mod net;
pub mod render;
pub mod ssdp;
pub mod xml;

use std::io::Write;

use log::LevelFilter;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Log target for per-request HTTP access lines.
pub const HTTP_LOG: &str = "tiny_dlna::http";

/// Set up logging: errors by default, with per-module overrides.
pub fn init_logging(filters: &[(&str, LevelFilter)]) {
    let mut builder = env_logger::Builder::new();
    builder.filter_level(LevelFilter::Error);
    for (module, level) in filters {
        builder.filter_module(module, *level);
    }
    builder.format(|buf, record| {
        writeln!(
            buf,
            "[{}][{}] {}",
            chrono::Local::now().format("%Y-%m-%d %H:%M:%S,%3f"),
            record.level(),
            record.args()
        )
    });
    builder.init();
}
