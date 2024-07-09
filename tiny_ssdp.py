import datetime
import logging
import psutil
import socket
import uuid

SSDP_MULTICAST_IP = '239.255.255.250'
SSDP_PORT = 1900
RENDER_PORT = 55000
UUID = f'{uuid.uuid4()}'
logger = logging.getLogger('ssdp')


def get_host_ip():
    ips = []
    interfaces = psutil.net_if_addrs()

    for iface_name, iface_addresses in interfaces.items():
        for address in iface_addresses:
            if address.family == socket.AF_INET:
                ip = address.address
                if ip and not ip.startswith('127.'):
                    ips.append(ip)

    if len(ips) == 0:
        logger.error('failed to find host IP.')

    return ips[0]


def build_m_search_response():
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    host_ip = get_host_ip()
    location = f'http://{host_ip}:{RENDER_PORT}/description.xml'

    text = 'HTTP/1.1 200 OK\r\n'
    text += f'USN: uuid:{UUID}::urn:schemas-upnp-org:service:AVTransport:1\r\n'
    text += f'Location: {location}\r\n'
    text += 'ST: urn:schemas-upnp-org:service:AVTransport:1\r\n'
    text += 'EXT: \r\n'
    text += 'Server: Werkzeug/3.0.3 Python/3.11.0\r\n'
    text += 'Cache-Control: max-age=70\r\n'
    text += f'Date: {date_str}\r\n\r\n'
    return text.encode('utf-8')

def ssdp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', SSDP_PORT))

    # Join the SSDP multicast group
    mreq = socket.inet_aton(SSDP_MULTICAST_IP) + socket.inet_aton('0.0.0.0')
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        data, addr = sock.recvfrom(1024)
        if b'M-SEARCH' in data and b'ssdp:discover' in data:
            logger.info(f'Received M-SEARCH from {addr}, sending response...')
            sock.sendto(build_m_search_response(), addr)

if __name__ == '__main__':
    ssdp_listener()
