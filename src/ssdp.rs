//! SSDP: answering M-SEARCH for local renders, and searching for devices.

use std::io;
use std::net::{Ipv4Addr, SocketAddr, SocketAddrV4, TcpStream, UdpSocket};
use std::thread;
use std::time::{Duration, Instant, SystemTime};

use log::{debug, error, info};
use socket2::{Domain, Protocol, Socket, Type};

use crate::{config, net};

pub const MULTICAST_IP: Ipv4Addr = Ipv4Addr::new(239, 255, 255, 250);
pub const PORT: u16 = 1900;

const ST_MEDIA_RENDERER: &str = "urn:schemas-upnp-org:device:MediaRenderer:1";
const ST_AVTRANSPORT: &str = "urn:schemas-upnp-org:service:AVTransport:1";

fn contains(haystack: &[u8], needle: &[u8]) -> bool {
    haystack.windows(needle.len()).any(|w| w == needle)
}

fn search_target(data: &[u8]) -> &'static str {
    if contains(data, b":device:MediaRenderer:1") {
        ST_MEDIA_RENDERER
    } else {
        ST_AVTRANSPORT
    }
}

fn build_response(st: &str, ip: Ipv4Addr, port: u16, uuid: &str) -> String {
    format!(
        "HTTP/1.1 200 OK\r\n\
         ST: {st}\r\n\
         USN: uuid:{uuid}::{st}\r\n\
         Location: http://{ip}:{port}/description.xml\r\n\
         EXT: \r\n\
         Server: UPnP/1.0 TinyRender/{version}\r\n\
         Cache-Control: max-age=70\r\n\
         Date: {date}\r\n\r\n",
        version = crate::VERSION,
        date = httpdate::fmt_http_date(SystemTime::now()),
    )
}

/// Skip registry entries left behind by renders that died without cleanup.
fn is_listening(port: u16) -> bool {
    let addr = SocketAddr::from((Ipv4Addr::LOCALHOST, port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(200)).is_ok()
}

/// How often the listener wakes up to check its multicast membership.
const CHECK_EVERY: Duration = Duration::from_secs(5);
/// Re-join this often even when nothing seems to have changed.
const REJOIN_EVERY: Duration = Duration::from_secs(60);

fn bind_listener() -> io::Result<UdpSocket> {
    let sock = Socket::new(Domain::IPV4, Type::DGRAM, Some(Protocol::UDP))?;
    sock.set_reuse_address(true)?;
    sock.bind(&SocketAddrV4::new(Ipv4Addr::UNSPECIFIED, PORT).into())?;
    let sock: UdpSocket = sock.into();
    sock.set_read_timeout(Some(CHECK_EVERY))?;
    Ok(sock)
}

/// Keeps the listener joined to the SSDP group on every LAN interface.
///
/// The OS can silently drop a socket's multicast membership when the
/// network goes away, e.g. Wi-Fi turning off while a Mac sleeps. The socket
/// then still gets unicast traffic but never sees M-SEARCH again, so we
/// re-join when the interfaces change, after a sleep, and periodically.
struct Membership {
    ifaces: Vec<Ipv4Addr>,
    joined_at: Instant,
    checked_at: Instant,
    checked_wall: SystemTime,
}

impl Membership {
    fn new(sock: &UdpSocket) -> Self {
        let ifaces = net::lan_ips();
        join_group(sock, &ifaces);
        let now = Instant::now();
        Membership {
            ifaces,
            joined_at: now,
            checked_at: now,
            checked_wall: SystemTime::now(),
        }
    }

    fn refresh(&mut self, sock: &UdpSocket) {
        let now = Instant::now();
        if now - self.checked_at < CHECK_EVERY {
            return;
        }
        let wall = SystemTime::now();
        // Instant stops while the machine sleeps; wall-clock time doesn't.
        let wall_gap = wall.duration_since(self.checked_wall).unwrap_or_default();
        let slept = wall_gap > (now - self.checked_at) + CHECK_EVERY;
        self.checked_at = now;
        self.checked_wall = wall;

        let ifaces = net::lan_ips();
        let changed = ifaces != self.ifaces;
        if !(changed || slept || now - self.joined_at >= REJOIN_EVERY) {
            return;
        }
        if changed || slept {
            info!("network changed, re-joining SSDP group on {ifaces:?}");
        }
        join_group(sock, &ifaces);
        self.ifaces = ifaces;
        self.joined_at = now;
    }
}

/// (Re-)join the SSDP group on each interface. Leaving first clears any
/// stale membership the kernel still holds for this socket.
fn join_group(sock: &UdpSocket, ifaces: &[Ipv4Addr]) {
    for ip in ifaces {
        let _ = sock.leave_multicast_v4(&MULTICAST_IP, ip);
        if let Err(e) = sock.join_multicast_v4(&MULTICAST_IP, ip) {
            debug!("failed to join SSDP group on {ip}: {e}");
        }
    }
}

fn listen(sock: &UdpSocket) -> io::Result<()> {
    debug!("SSDP server running at {PORT}");
    let mut membership = Membership::new(sock);
    let mut buf = [0u8; 2048];
    loop {
        membership.refresh(sock);
        let (n, addr) = match sock.recv_from(&mut buf) {
            Ok(r) => r,
            Err(e)
                if matches!(
                    e.kind(),
                    io::ErrorKind::WouldBlock | io::ErrorKind::TimedOut
                ) =>
            {
                continue;
            }
            Err(e) => return Err(e),
        };
        let data = &buf[..n];
        if !(contains(data, b"M-SEARCH") && contains(data, b"ssdp:discover")) {
            continue;
        }
        let st = search_target(data);
        info!("Received M-SEARCH from {addr}, sending response...");
        let Some(ip) = net::local_ip_for(addr.ip()) else {
            error!("failed to find host IP");
            continue;
        };
        for port in config::live_render_ports() {
            if !is_listening(port) {
                debug!("skip render on port {port}: not listening");
                continue;
            }
            let resp = build_response(st, ip, port, &config::render_uuid(port));
            if let Err(e) = sock.send_to(resp.as_bytes(), addr) {
                debug!("failed to answer {addr}: {e}");
            }
        }
    }
}

/// Answer M-SEARCH requests forever. If the SSDP port can't be bound
/// (e.g. another listener holds it exclusively), keep retrying so this
/// process takes over once the other one exits.
pub fn serve_forever() {
    loop {
        match bind_listener() {
            Ok(sock) => {
                if let Err(e) = listen(&sock) {
                    error!("SSDP listener failed: {e}");
                }
            }
            Err(e) => debug!("SSDP bind failed: {e}"),
        }
        thread::sleep(Duration::from_millis(500));
    }
}

/// Send an M-SEARCH for AVTransport services and collect raw replies.
pub fn search(wait: Duration) -> io::Result<Vec<(SocketAddr, String)>> {
    let msg = format!(
        "M-SEARCH * HTTP/1.1\r\n\
         HOST: {MULTICAST_IP}:{PORT}\r\n\
         MAN: \"ssdp:discover\"\r\n\
         MX: 1\r\n\
         ST: {ST_AVTRANSPORT}\r\n\r\n"
    );
    let sock = UdpSocket::bind((Ipv4Addr::UNSPECIFIED, 0))?;
    sock.set_multicast_ttl_v4(2)?;
    sock.send_to(msg.as_bytes(), (MULTICAST_IP, PORT))?;

    let deadline = Instant::now() + wait;
    let mut replies = Vec::new();
    let mut buf = [0u8; 2048];
    loop {
        let left = deadline.saturating_duration_since(Instant::now());
        if left.is_zero() {
            break;
        }
        sock.set_read_timeout(Some(left))?;
        match sock.recv_from(&mut buf) {
            Ok((n, addr)) => {
                replies.push((addr, String::from_utf8_lossy(&buf[..n]).into_owned()));
            }
            Err(e)
                if matches!(
                    e.kind(),
                    io::ErrorKind::WouldBlock | io::ErrorKind::TimedOut
                ) =>
            {
                break;
            }
            Err(e) => return Err(e),
        }
    }
    Ok(replies)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn response_format() {
        let r = build_response(
            ST_MEDIA_RENDERER,
            Ipv4Addr::new(10, 0, 0, 2),
            59876,
            "abc-59876",
        );
        assert!(r.starts_with("HTTP/1.1 200 OK\r\n"));
        assert!(r.contains("USN: uuid:abc-59876::urn:schemas-upnp-org:device:MediaRenderer:1\r\n"));
        assert!(r.contains("Location: http://10.0.0.2:59876/description.xml\r\n"));
        assert!(r.ends_with("\r\n\r\n"));
    }

    #[test]
    fn target_detection() {
        assert_eq!(
            search_target(b"ST: urn:schemas-upnp-org:device:MediaRenderer:1"),
            ST_MEDIA_RENDERER
        );
        assert_eq!(search_target(b"ST: ssdp:all"), ST_AVTRANSPORT);
    }
}
