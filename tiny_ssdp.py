import datetime
import json
import logging
import os
import psutil
import socket
import uuid

SSDP_MULTICAST_IP = '239.255.255.250'
SSDP_PORT = 1900
RENDER_PORT = 55000
logger = logging.getLogger('tiny_ssdp')
ST_VALUE_MEDIARENDERER = 'mediarenderer'
ST_VALUE_AVTRANSPORT = 'avtransport'


def get_uuid():
    home_dir = os.path.expanduser('~')
    app_data_dir = os.path.join(home_dir, '.config', 'tiny-dlna')
    os.makedirs(app_data_dir, exist_ok=True)
    config_file = os.path.join(app_data_dir, 'tiny-render.json')

    if os.path.exists(config_file):
        with open(config_file) as f:
            configs = json.load(f)
            if 'UUID' in configs and configs['UUID']:
                return configs['UUID']

    uuid_str = f'{uuid.uuid4()}'
    with open(config_file, 'w') as f:
        configs = {'UUID': uuid_str}
        json.dump(configs, f)


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


def build_m_search_response(st):
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    host_ip = get_host_ip()
    location = f'http://{host_ip}:{RENDER_PORT}/description.xml'
    uuid_str = get_uuid()

    text = 'HTTP/1.1 200 OK\r\n'
    if st == ST_VALUE_MEDIARENDERER:
        text += 'ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n'
        text += f'USN: uuid:{uuid_str}::urn:schemas-upnp-org:device:MediaRenderer:1\r\n'
    else:
        text += 'ST: urn:schemas-upnp-org:service:AVTransport:1\r\n'
        text += f'USN: uuid:{uuid_str}::urn:schemas-upnp-org:service:AVTransport:1\r\n'
    text += f'Location: {location}\r\n'
    text += 'EXT: \r\n'
    text += 'Server: Werkzeug/3.0 TinyRender/0.6\r\n'
    text += 'Cache-Control: max-age=70\r\n'
    text += f'Date: {date_str}\r\n\r\n'
    return text.encode('utf-8')

def get_search_target(data):
    if b':device:MediaRenderer:1' in data:
        return ST_VALUE_MEDIARENDERER
    else:
        return ST_VALUE_AVTRANSPORT

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
            st = get_search_target(data)
            logger.info(f'Received M-SEARCH from {addr}, sending response...')
            sock.sendto(build_m_search_response(st), addr)

if __name__ == '__main__':
    ssdp_listener()
