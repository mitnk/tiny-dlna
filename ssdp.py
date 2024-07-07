import datetime
import logging
import socket

SSDP_MULTICAST = '239.255.255.250'
SSDP_PORT = 1900
RENDER_PORT = 55000
LOCATION = f'http://192.168.1.228:{RENDER_PORT}/description.xml'
UUID = 'd095ee0c-7bed-43d0-bf98-f815496e8383'
logger = logging.getLogger('ssdp')

def build_m_search_response():
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    text = 'HTTP/1.1 200 OK\r\n'
    text += f'USN: uuid:{UUID}::urn:schemas-upnp-org:service:AVTransport:1\r\n'
    text += f'Location: {LOCATION}\r\n'
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
    mreq = socket.inet_aton(SSDP_MULTICAST) + socket.inet_aton('0.0.0.0')
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        data, addr = sock.recvfrom(1024)
        if b'M-SEARCH' in data and b'ssdp:discover' in data:
            logger.info(f'Received M-SEARCH from {addr}, sending response...')
            sock.sendto(build_m_search_response(), addr)

if __name__ == '__main__':
    ssdp_listener()
