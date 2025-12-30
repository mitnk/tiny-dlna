import argparse
import html
import logging
import re
import os.path
import signal
import subprocess
import threading
import time
import xml.etree.ElementTree as ET

from flask import Flask, request, Response
from .tiny_ssdp import get_uuid, ssdp_listener
from .tiny_ssdp import register_render, unregister_render
from .tiny_xmls import *  # NOQA

app = Flask(__name__)
logger = logging.getLogger('tiny_render')
PORT_DEFAULT = 59876


class MPVRenderer:
    def __init__(self):
        self.process = None

    def play_media(self, url, title=None, srt=None, dump_to=None):
        self.stop_media()  # Stop any existing media
        cmd = ['mpv', '--quiet', '--screen=1', '--no-terminal', url]

        if dump_to:
            path_abs = os.path.abspath(dump_to)
            cmd.append(f'--stream-record={path_abs}')
        if title:
            cmd.append('--title={}'.format(title))
        if srt:
            cmd.append('--sub-file={}'.format(srt))

        logger.debug('running: {}'.format(' '.join(cmd)))
        self.process = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)

    def stop_media(self):
        if self.process:
            self.process.terminate()
            self.process = None


renderer = MPVRenderer()

_DATA = {
    'CURRENT_URI': '',
    'CURRENT_SRT': '',
    'VIDEO_TITLE': '',
    'DUMP_TO': None,
    'STARTED_AT': 0,
}


@app.route('/description.xml')
def description():
    friendly_name = app.config['FRIENDLY_NAME']
    uuid_str = get_uuid(app.config['PORT'])
    xml = XML_DESC_PTN.format(friendly_name, uuid_str)
    resp = Response(xml, mimetype="text/xml")
    resp.headers['Server'] = 'UPnP/1.0 Werkzeug/3.0 TinyRender/0.7'
    return resp

# these 3 dlna_ routings below are only here so that some dummy app
# could treat our "tiny render" as a proper dlna device. (Mouyu ..)
@app.route('/dlna/AVTransport.xml')
def dlna_avtransport():
    resp = Response(XML_DLNA_AVT, mimetype="text/xml")
    return resp

@app.route('/dlna/RenderingControl.xml')
def dlna_render_control():
    resp = Response(XML_DLNA_RENDER_CTRL, mimetype="text/xml")
    return resp

@app.route('/dlna/ConnectionManager.xml')
def dlna_conn_manager():
    resp = Response(XML_DLNA_CONN_MANAGER, mimetype="text/xml")
    return resp


def to_track_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours}:{minutes:02}:{remaining_seconds:02}"

def is_play(request):
    return b'<u:Play' in request.data

def is_stop(request):
    return b'<u:Stop' in request.data

def is_setav(request):
    return b'SetAVTransportURI' in request.data

def is_gettrans(request):
    return b'u:GetTransportInfo' in request.data

def is_getpos(request):
    return b'u:GetPositionInfo' in request.data

def is_seek(request):
    return b'u:Seek' in request.data

def get_title_re(xml_data):
    pattern = re.compile(r'<dc:title>(.*?)</dc:title>', re.DOTALL)
    match = pattern.search(xml_data)
    if match:
        return match.group(1)

def get_metadata(request):
    root = ET.fromstring(request.data.strip())
    current_uri = root.find('.//CurrentURI').text
    metadata = root.find('.//CurrentURIMetaData').text
    if not metadata:
        logger.debug('no metadata')
        return {'video': current_uri, 'title': ''}

    title = ''
    metadata = html.unescape(metadata)
    try:
        # HACK: replace all `&` to `&amp;`
        metadata = metadata.replace('&', '&amp;')
        metadata = ET.fromstring(metadata.strip())
    except ET.ParseError:
        # HACK: fall back to `re` to get title only (e.g. Huya)
        logger.debug('** got xml.ParseError, fall back to re')
        title = get_title_re(metadata)
        return {'video': current_uri, 'title': title}

    ns = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        '': 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/'
    }
    item = metadata.find('.//item', namespaces=ns)
    obj = item.find('.//dc:title', namespaces=ns)
    if obj is not None:
        title = obj.text

    current_srt = ''
    # Try sec:CaptionInfoEx first (Samsung standard, widely supported)
    elem = item.find('.//{http://www.sec.co.kr/}CaptionInfoEx')
    if elem is not None and elem.text:
        current_srt = elem.text.strip()
    # Try sec:CaptionInfo
    if not current_srt:
        elem = item.find('.//{http://www.sec.co.kr/}CaptionInfo')
        if elem is not None and elem.text:
            current_srt = elem.text.strip()
    # Try pv:subtitleFileUri (Panasonic)
    if not current_srt:
        elem = item.find('.//{http://www.pv.com/pvns/}subtitleFileUri')
        if elem is not None and elem.text:
            current_srt = elem.text.strip()
    # Try res with subtitle type or srt protocolInfo
    if not current_srt:
        for res in metadata.findall('.//{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}res'):
            proto = res.get('protocolInfo', '')
            if res.get('type') == 'text/subtitle' or 'text/srt' in proto:
                if res.text:
                    current_srt = res.text.strip()
                    break

    return {
        'video': current_uri,
        'srt': current_srt,
        'title': title,
    }


@app.route('/AVTransport/control', methods=['POST'])
def control():
    if is_setav(request):
        metadata = get_metadata(request)
        current_uri = metadata['video']
        current_srt = metadata.get('srt', '')
        video_title = metadata.get('title', '')

        logger.debug(f'Action: SetAV: {current_uri}')
        logger.debug(f'Title: {video_title} SRT: {current_srt}')
        _DATA['CURRENT_URI'] = current_uri
        _DATA['CURRENT_SRT'] = current_srt
        _DATA['VIDEO_TITLE'] = video_title
        return Response(XML_AVSET_DONE, mimetype="text/xml")

    elif is_play(request):
        if _DATA['STARTED_AT'] > 0 and _DATA['DUMP_TO']:
            app.config['STOP'] = True
            exit(0)

        _DATA['STARTED_AT'] = time.time()
        url = _DATA['CURRENT_URI']
        srt = _DATA['CURRENT_SRT']
        title = _DATA['VIDEO_TITLE']
        dump_to = _DATA['DUMP_TO']
        logger.debug(f'action: Play: {url}')
        renderer.play_media(url, title, srt, dump_to)
        return Response(XML_PLAY_DONE, mimetype="text/xml")

    elif is_getpos(request):
        # this is only a dummy impl; we need rpc to mpv process for real.
        logger.debug('action: GetPositionInfo')
        seconds = int(time.time() - _DATA['STARTED_AT'])
        reltime = to_track_time(seconds)
        return Response(XML_POSINFO.format(reltime), mimetype="text/xml")

    elif is_gettrans(request):
        logger.debug('action: GetTransportInfo')
        return Response(XML_TRANSINFO, mimetype="text/xml")

    elif is_stop(request):
        logger.debug('stopping')

        if _DATA['STARTED_AT'] > 0 and _DATA['DUMP_TO']:
            app.config['STOP'] = True
            logger.info('stopping the recorder as a whole')
            exit(0)

        _DATA['CURRENT_URI'] = ''
        _DATA['CURRENT_SRT'] = ''
        _DATA['VIDEO_TITLE'] = ''
        _DATA['STARTED_AT'] = 0
        renderer.stop_media()
        return Response(XML_STOP_DONE, mimetype="text/xml")

    elif is_seek(request):
        logger.debug('action:seek')
        return Response(XML_SEEK_DONE, mimetype="text/xml")

    logger.error(f'action not support: {request.data}')
    return Response('Action Not Supported', status=500)


class SSDPServer(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            try:
                ssdp_listener()
            except OSError:
                # another SSDP Server is running
                time.sleep(0.05)
                continue
            break


def _get_friendly_name(args):
    if not args.name:
        return 'Tiny Recorder' if args.dump_to else 'Tiny Render'

    if args.dump_to:
        return args.name + f' (Recorder)'

    return args.name


def flask_app_monitor(uuid, port):
    to_stop = app.config.get('STOP')
    while app.config.get('STOP') is None:
        time.sleep(0.05)

    unregister_render(uuid)
    logger.debug(f'unregistered render: {uuid}')
    logger.info('killing render process. mpv process is left open')
    pid = os.getpid()
    os.kill(pid, signal.SIGTERM)


def signal_handler(signal, frame):
    logger.debug('got killing signal')
    uuid = get_uuid(app.config['PORT'])
    unregister_render(uuid)
    logger.debug(f'unregistered render: {uuid}')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    parser = argparse.ArgumentParser(prog='tiny-render')
    parser.add_argument('--http-logs', action='store_true', help='Enable server logs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable debug logs')
    parser.add_argument('--name', type=str, help='Specify render name')
    parser.add_argument('--port', type=int, default=0, help='Server Port')
    parser.add_argument('--dump-to', type=str, help='dump streaming to a file')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.ERROR,
        format='[%(asctime)s][%(levelname)s] %(message)s',
    )

    if not args.http_logs:
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        logging.getLogger('tiny_ssdp').setLevel(logging.ERROR)

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    port = PORT_DEFAULT
    if args.dump_to:
        file_dump = os.path.abspath(args.dump_to)
        if os.path.exists(file_dump):
            logger.error(f'target file exists: {file_dump}')
            exit(1)

        _DATA['DUMP_TO'] = args.dump_to
        port += 1

    if args.port:
        port = args.port

    ssdp = SSDPServer()
    ssdp.start()

    friendly_name = _get_friendly_name(args)
    app.config['FRIENDLY_NAME'] = friendly_name
    app.config['PORT'] = port
    logger.info(f'Starting DLNA Receiver: {friendly_name}')
    if args.dump_to:
        logger.info(f'Recording stream to {args.dump_to}')

    uuid = get_uuid(port)
    register_render(uuid, friendly_name, port)
    logger.debug(f'registered render {uuid}')

    app_server = threading.Thread(
        target=app.run,
        kwargs={'host': '0.0.0.0', 'port': port},
    )
    app_server.start()

    thread = threading.Thread(
        target=flask_app_monitor,
        kwargs={'uuid': uuid, 'port': port},
    )
    thread.start()
    thread.join()


if __name__ == "__main__":
    main()
