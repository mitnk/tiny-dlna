import argparse
import json
import logging
import os.path
import random
import signal
import socket
import threading
import time
import urllib.parse
import urllib.request as urlreq
import xml.etree.ElementTree as ET

from flask import Flask, send_from_directory
from xml.sax.saxutils import escape as xmlescape
from urllib.error import URLError
from .tiny_ssdp import SSDP_MULTICAST_IP, SSDP_PORT, get_host_ip
from .tiny_xmls import *  # NOQA

logger = logging.getLogger('tiny_cli')

MSEARCH_MSG = (
    'M-SEARCH * HTTP/1.1\r\n'
    f'HOST: {SSDP_MULTICAST_IP}:{SSDP_PORT}\r\n'
    'MAN: "ssdp:discover"\r\n'
    'MX: 1\r\n'
    'ST: urn:schemas-upnp-org:service:AVTransport:1\r\n'
    '\r\n'
)
DIR_LINKS = os.path.join('~', '.config', 'tiny-dlna', 'symlinks')


def _get_device_info(location):
    p = urllib.parse.urlparse(location)

    attrs = {}
    namespace = {'ns': 'urn:schemas-upnp-org:device-1-0'}
    namespaces = {
        '': 'urn:schemas-upnp-org:device-1-0',
        'dlna': 'urn:schemas-dlna-org:device-1-0'
    }

    with urlreq.urlopen(location, timeout=1.0) as r:
        xml = r.read()
        root = ET.fromstring(xml.strip())

        friendly_name = root.find('.//ns:friendlyName', namespace).text
        if friendly_name:
            attrs['friendly_name'] = friendly_name

        elem = root.find(
            ".//service[serviceId='urn:upnp-org:serviceId:AVTransport']",
            namespaces=namespaces,
        )
        if elem is not None:
            control_url = elem.find('controlURL', namespaces).text
            if control_url:
                control_url = control_url.lstrip('/')
                attrs['control_url'] = f'http://{p.hostname}:{p.port}/{control_url}'

    return attrs


def _parse_ssdp_response(resp):
    lines = resp.split('\r\n')
    device = {}

    if not lines[0].endswith('200 OK'):
        return None

    for line in lines:
        try:
            k, v = [x.strip() for x in line.split(':', 1)]
        except ValueError:
            continue

        k = k.lower()
        if k == 'location':
            device['location'] = v
        elif k == 'usn':
            device['usn'] = v
        elif k == 'st':
            device['st'] = v

    if ':service:AVTransport:' not in device.get('st', ''):
        return None

    attrs = _get_device_info(device['location'])
    device.update(attrs)
    return device


def get_dlna_devices():
    # Create the UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(1.2)

    # Send the M-SEARCH message to the SSDP multicast address
    # logger.debug("Sending M-SEARCH...")
    sock.sendto(MSEARCH_MSG.encode('utf-8'), (SSDP_MULTICAST_IP, SSDP_PORT))

    devices = []
    known_locations = set()
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            try:
                device = _parse_ssdp_response(data.decode('utf-8'))
            except URLError:
                # render url does not respond
                continue

            location = device.get('location')
            # logger.debug(f'got reply from {addr}, Location: {location}')
            if device and location not in known_locations:
                devices.append(device)
                known_locations.add(location)
        except socket.timeout:
            break

    return devices


def list_dlna_devices():
    devices = get_dlna_devices()
    print(json.dumps({'devices': devices}, ensure_ascii=False, sort_keys=True, indent=2))


def stop_dlna_render(args):
    url_control, names = get_control_url(args)
    if not url_control:
        logger.error(f'No such device found: {args.query}')
        logger.error('Available names: {}'.format(', '.join(names)))
        exit(1)

    logger.debug(f'Stopping streaming on DLNA: {url_control}')
    send_dlna_command(url_control, XML_STOP, 'Stop')


def seek_dlna_render(args):
    url_control, names = get_control_url(args)
    if not url_control:
        logger.error(f'No such device found: {args.query}')
        logger.error('Available names: {}'.format(', '.join(names)))
        exit(1)

    logger.debug(f'Seek streaming to {args.to}: {url_control}')
    xml = XML_SEEK_PTN.format(args.to)
    send_dlna_command(url_control, xml, 'Seek')


def post(url, action_data, headers):
    action_data = action_data.encode("utf-8")
    r = urlreq.Request(url, action_data, headers)
    try:
        urlreq.urlopen(r)
    except Exception as e:
        logger.error('{}: {}'.format(e.__class__.__name__, e))
    logging.debug("Request sent")


app = Flask(__name__)


@app.route('/videos/<name_video>')
def serve_video(name_video):
    dir_base = os.path.expanduser(DIR_LINKS)
    # Ensure proper MIME type for subtitle files
    if name_video.endswith('.srt'):
        return send_from_directory(dir_base, name_video, mimetype='text/srt')
    return send_from_directory(dir_base, name_video)


def run_flask_server(port):
    app.run(host='0.0.0.0', port=port)


def send_dlna_command(url_control, action_body, action_name):
    st = "urn:schemas-upnp-org:service:AVTransport:1"
    headers = {
        'Content-Type': 'text/xml; charset="utf-8"',
        'SOAPACTION': f'"{st}#{action_name}"',
        "Connection": "close",
    }
    post(url_control, action_body, headers)


def send_set_av_transport(url_control, url_video, url_srt=None, title=None):
    url_video = url_video.replace('&', '&amp;')
    if 'http://192.168' in url_video:
        title = title or url_video.split('/')[-1]
    else:
        title = title or 'online stream'

    subtitle = ''
    if url_srt:
        subtitle = XML_SUBTITLE.format(url_srt=url_srt)

    metadata = XML_META.format(
        title=title,
        url_video=url_video,
        subtitle=subtitle,
    )
    xml = XML_SETAV.format(
        url_video=url_video,
        metadata=xmlescape(metadata),
    )
    send_dlna_command(url_control, xml, 'SetAVTransportURI')


def send_play(url_control):
    send_dlna_command(url_control, XML_PLAY, 'Play')


def send_stop(url_control):
    dir_links = os.path.expanduser(DIR_LINKS)
    if not os.path.isdir(dir_links):
        return

    for item in os.listdir(dir_links):
        item_path = os.path.join(dir_links, item)
        if os.path.islink(item_path):
            os.unlink(item_path)

    send_dlna_command(url_control, XML_STOP, 'Stop')


def create_link(path_file):
    name_file = os.path.basename(path_file)
    dir_links = os.path.expanduser(DIR_LINKS)
    if not os.path.exists(dir_links):
        os.makedirs(dir_links, exist_ok=True)

    path_link = os.path.join(dir_links, name_file)
    if os.path.islink(path_link):
        os.unlink(path_link)

    path_abs = os.path.abspath(path_file)
    os.symlink(path_abs, path_link)
    logger.info(f'created softlink: {path_abs} --> {path_link}')


def get_control_url(args):
    devices = get_dlna_devices()
    url = None
    other_names = []
    for d in devices:
        if args.query.lower() in d['friendly_name'].lower():
            url = d.get('control_url')
        else:
            other_names.append(d.get('friendly_name', 'no-name'))

    return url, other_names


def play_online_stream(url_control, url_stream):
    send_set_av_transport(url_control, url_stream)
    send_play(url_control)

    def signal_handler(sig, frame):
        send_stop(url_control)
        exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        time.sleep(1)


def play_video(args):
    path_video = args.video_file
    url_control, names = get_control_url(args)
    if not url_control:
        logger.error(f'no such DLNA device found: {args.query}')
        logger.error('Available names: {}'.format(', '.join(names)))
        exit(0)

    if path_video.startswith('http://') or path_video.startswith('https://'):
        return play_online_stream(url_control, path_video)

    if not os.path.isfile(path_video):
        print(f'no such file: {path_video}')
        exit(0)

    ip = get_host_ip()
    port = random.randint(50000, 58999)

    logger.info(f'play video: {path_video}')
    create_link(path_video)
    name_video = os.path.basename(path_video)
    url_video = f"http://{ip}:{port}/videos/{name_video}"

    path_srt = '.'.join(path_video.split('.')[:-1]) + '.srt'
    if os.path.exists(path_srt):
        create_link(path_srt)
        name_srt = os.path.basename(path_srt)
        url_srt = f"http://{ip}:{port}/videos/{name_srt}"
    else:
        path_srt = None
        url_srt = None

    server_thread = threading.Thread(target=run_flask_server, args=(port,))
    server_thread.daemon = True
    server_thread.start()

    # Give some time for the server to start
    time.sleep(1.6)

    send_set_av_transport(url_control, url_video, url_srt)
    send_play(url_control)

    def signal_handler(sig, frame):
        send_stop(url_control)
        exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    # Keep main thread running so the server stays up and we can catch signal
    while True:
        time.sleep(1)


def main():
    logging.basicConfig(
        level=logging.ERROR,
        format='[%(asctime)s][%(levelname)s] %(message)s',
    )

    version_file = os.path.join(os.path.dirname(__file__), 'version')
    with open(version_file, 'r') as f:
        version = f.read().strip()

    parser = argparse.ArgumentParser(prog='tiny-cli')
    parser.add_argument('--version', action='version', version=f'v{version}')

    subparsers = parser.add_subparsers(dest='command', required=True,
                                       help='Choose a command')

    list_parser = subparsers.add_parser('list', help='List available DLNA devices')
    list_parser.add_argument('-v', dest='verbose', action='store_true',
                              help='Enable verbose logs')

    stop_parser = subparsers.add_parser('stop', help='Stop DLNA streaming')
    stop_parser.add_argument('-v', dest='verbose', action='store_true',
                              help='Enable verbose logs')
    stop_parser.add_argument('-q', dest='query', type=str, required=True,
                             help='Specify Device by Friendly Name')

    seek_parser = subparsers.add_parser('seek', help='Seek DLNA streaming')
    seek_parser.add_argument('-v', dest='verbose', action='store_true',
                              help='Enable verbose logs')
    seek_parser.add_argument('-q', dest='query', type=str, required=True,
                             help='Specify Device by Friendly Name')
    seek_parser.add_argument('to', type=str,
                             help='Specify the new time point, format: HH:MM:SS')

    play_parser = subparsers.add_parser('play', help='Play via DLNA device')
    play_parser.add_argument('video_file')
    play_parser.add_argument('-v', dest='verbose', action='store_true',
                             help='Enable verbose logs')
    play_parser.add_argument('-q', dest='query', type=str, required=True,
                             help='Specify Device by Friendly Name')

    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.command == 'list':
        list_dlna_devices()
    elif args.command == 'stop':
        stop_dlna_render(args)
    elif args.command == 'seek':
        seek_dlna_render(args)
    elif args.command == 'play':
        if not args.verbose:
            logging.getLogger('werkzeug').setLevel(logging.ERROR)
        play_video(args)


if __name__ == '__main__':
    main()
