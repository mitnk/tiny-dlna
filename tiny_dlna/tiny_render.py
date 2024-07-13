import argparse
import html
import logging
import re
import subprocess
import threading
import time
import xml.etree.ElementTree as ET

from flask import Flask, request, Response
from .tiny_ssdp import get_uuid, ssdp_listener
from .tiny_xmls import *  # NOQA

app = Flask(__name__)
logger = logging.getLogger('tiny_render')


class MPVRenderer:
    def __init__(self):
        self.process = None

    def play_media(self, url, title=None, srt=None):
        self.stop_media()  # Stop any existing media
        cmd = ['mpv', url]
        if title:
            cmd.append('--title={}'.format(title))
        if srt:
            cmd.append('--sub-file={}'.format(srt))

        logger.debug(f'running mpv: {cmd}')
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
    'STARTED_AT': 0,
}


@app.route('/description.xml')
def description():
    friendly_name = app.config['FRIENDLY_NAME']
    uuid_str = get_uuid()
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
    for res in metadata.findall('.//{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}res'):
        if res.get('type') == 'text/subtitle':
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
        _DATA['STARTED_AT'] = time.time()
        url = _DATA['CURRENT_URI']
        srt = _DATA['CURRENT_SRT']
        title = _DATA['VIDEO_TITLE']
        logger.debug(f'action: Play: {url}')
        renderer.play_media(url, title, srt)
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
    def __init__(self, render_port):
        super().__init__()
        self.render_port = render_port

    def run(self):
        ssdp_listener(self.render_port)


def main():
    parser = argparse.ArgumentParser(prog='tiny-render')
    parser.add_argument('--http-logs', action='store_true', help='Enable server logs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable debug logs')
    parser.add_argument('--name', type=str, default='Tiny Render', help='Change render name')

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

    port = 59876
    ssdp = SSDPServer(port)
    ssdp.start()

    friendly_name = args.name
    app.config['FRIENDLY_NAME'] = friendly_name
    logging.info(f'Starting DLNA Receiver: {friendly_name}')
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
