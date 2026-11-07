//! Picking the local IP address other devices should use to reach us.

use std::net::{IpAddr, Ipv4Addr, SocketAddr, UdpSocket};

/// The local IPv4 address used to route packets to `target`.
/// No packet is sent: connecting a UDP socket only selects a route.
pub fn local_ip_towards(target: IpAddr) -> Option<Ipv4Addr> {
    let sock = UdpSocket::bind((Ipv4Addr::UNSPECIFIED, 0)).ok()?;
    sock.connect(SocketAddr::new(target, 9)).ok()?;
    match sock.local_addr().ok()?.ip() {
        IpAddr::V4(ip) if !ip.is_unspecified() && !ip.is_loopback() => Some(ip),
        _ => None,
    }
}

/// A best-guess LAN address of this host, used when no route-based answer
/// is available. Prefers 192.168.x.x, then other private ranges, then any
/// non-loopback address; within a class the smallest address wins, which
/// usually skips VM bridges like 192.168.65.1.
pub fn host_ip() -> Option<Ipv4Addr> {
    let mut ips = lan_ips();
    let rank = |ip: &Ipv4Addr| match ip.octets() {
        [192, 168, ..] => 0,
        _ if ip.is_private() => 1,
        _ => 2,
    };
    ips.sort_by_key(|ip| (rank(ip), *ip));
    ips.first().copied()
}

/// All non-loopback, non-link-local IPv4 addresses of this host, sorted.
pub fn lan_ips() -> Vec<Ipv4Addr> {
    let mut ips: Vec<Ipv4Addr> = if_addrs::get_if_addrs()
        .unwrap_or_default()
        .into_iter()
        .filter_map(|iface| match iface.ip() {
            IpAddr::V4(ip) if !ip.is_loopback() && !ip.is_link_local() => Some(ip),
            _ => None,
        })
        .collect();
    ips.sort();
    ips.dedup();
    ips
}

/// The address `peer` should use to reach this host.
pub fn local_ip_for(peer: IpAddr) -> Option<Ipv4Addr> {
    local_ip_towards(peer).or_else(host_ip)
}
