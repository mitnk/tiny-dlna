import datetime
import json
import logging
import os
import psutil
import socket
import uuid

SSDP_MULTICAST_IP = '239.255.255.250'
SSDP_PORT = 1900
logger = logging.getLogger('tiny_ssdp')
logger.setLevel(logging.DEBUG)

ST_VALUE_MEDIARENDERER = 'mediarenderer'
ST_VALUE_AVTRANSPORT = 'avtransport'


def get_config_file(file_name):
    home_dir = os.path.expanduser('~')
    app_data_dir = os.path.join(home_dir, '.config', 'tiny-dlna')
    os.makedirs(app_data_dir, exist_ok=True)
    return os.path.join(app_data_dir, file_name)


def register_render(uuid, name, port):
    config_file = get_config_file('live-renders.json')
    data = {'renders': []}
    if os.path.exists(config_file):
        with open(config_file) as f:
            data = json.load(f)

    found = False
    for render in data.get('renders', []):
        if render['uuid'] == uuid:
            found = True
            break

    if found:
        return

    if 'renders' not in data:
        data['renders'] = []

    data['renders'].append({'uuid': uuid, 'name': name, 'port': port})
    with open(config_file, 'w') as f:
        json.dump(data, f, sort_keys=True, indent=4)


def unregister_render(uuid):
    config_file = get_config_file('live-renders.json')
    if os.path.exists(config_file):
        with open(config_file) as f:
            data = json.load(f)
    else:
        data = {'renders': []}

    if 'renders' not in data:
        return

    found = False
    others = []
    for render in data.get('renders', []):
        if render['uuid'] == uuid:
            found = True
        else:
            others.append(render)

    if not found:
        return

    data = {'renders': others}
    with open(config_file, 'w') as f:
        json.dump(data, f, sort_keys=True, indent=4)


def get_uuid(port):
    config_file = get_config_file('tiny-render.json')
    if os.path.exists(config_file):
        with open(config_file) as f:
            configs = json.load(f)
            if 'UUID' in configs and configs['UUID']:
                return configs['UUID'] + f'-{port}'

    uuid_str = str(uuid.uuid4()).rsplit('-', 1)[0]
    with open(config_file, 'w') as f:
        configs = {'UUID': uuid_str}
        json.dump(configs, f)

    return uuid_str + f'-{port}'


def get_host_ip():
    ips = []
    interfaces = psutil.net_if_addrs()

    for iface_name, iface_addresses in interfaces.items():
        for address in iface_addresses:
            if address.family == socket.AF_INET:
                ip = address.address
                if ip and ip.startswith('192.168.'):
                    ips.append(ip)

    if len(ips) == 0:
        logger.error('failed to find host IP.')

    # use the smallest one, in case get like 192.168.65.1 (vm interfaces)
    ips.sort()
    return ips[0]


def build_m_search_response(st, render_port):
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    render_ip = get_host_ip()
    location = f'http://{render_ip}:{render_port}/description.xml'
    uuid_str = get_uuid(render_port)

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


def _get_live_render_ports():
    config_file = get_config_file('live-renders.json')
    if not os.path.exists(config_file):
        return []

    with open(config_file) as f:
        configs = json.load(f)
        return [x['port'] for x in configs.get('renders', [])]


def ssdp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', SSDP_PORT))
    logger.debug(f'SSDP server running at {SSDP_PORT}')

    # Join the SSDP multicast group
    mreq = socket.inet_aton(SSDP_MULTICAST_IP) + socket.inet_aton('0.0.0.0')
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        data, addr = sock.recvfrom(1024)
        if b'M-SEARCH' in data and b'ssdp:discover' in data:
            st = get_search_target(data)
            logger.info(f'Received M-SEARCH from {addr}, sending response...')
            for render_port in _get_live_render_ports():
                sock.sendto(build_m_search_response(st, render_port), addr)
