import html
import subprocess
from flask import Flask, request, Response
# from lxml import etree
import xml.etree.ElementTree as ET

app = Flask(__name__)

XML_AVSET_DONE = """
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetAVTransportURIResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"""

XML_PLAY_DONE = """
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"""

XML_POSINFO = """
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetPositionInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <Track>0</Track>
      <TrackDuration>00:00:00</TrackDuration>
      <RelTime>00:00:00</RelTime>
      <AbsTime>00:00:00</AbsTime>
      <RelCount>2147483647</RelCount>
      <AbsCount>2147483647</AbsCount>
    </u:GetPositionInfoResponse>
  </s:Body>
</s:Envelope>
"""

XML_TRANSINFO = """
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetTransportInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <CurrentTransportState>PLAYING</CurrentTransportState>
      <CurrentTransportStatus>OK</CurrentTransportStatus>
      <CurrentSpeed>1</CurrentSpeed>
    </u:GetTransportInfoResponse>
  </s:Body>
</s:Envelope>
"""

XML_STOP_DONE = """
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:StopResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"""

class MPVRenderer:
    def __init__(self):
        self.process = None

    def play_media(self, url, srt=None):
        self.stop_media()  # Stop any existing media
        cmd = ['mpv', url]
        if srt:
            cmd.append('--sub-file={}'.format(srt))
        self.process = subprocess.Popen(cmd)

    def stop_media(self):
        if self.process:
            self.process.terminate()
            self.process = None

renderer = MPVRenderer()

@app.route('/description.xml')
def description():
    xml = """<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:dlna="urn:schemas-dlna-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
        <friendlyName>Tiny Render</friendlyName>
        <manufacturer>mitnk</manufacturer>
        <modelName>T001</modelName>
        <UDN>uuid:dlna-tiny-render-t001</UDN>
        <dlna:X_DLNADOC xmlns:dlna="urn:schemas-dlna-org:device-1-0">DMR-1.50</dlna:X_DLNADOC>
            <serviceList>
                <service>
                <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
                <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
                <SCPDURL>AVTransport/82d8-eb72-b097/scpd.xml</SCPDURL>
                <controlURL>AVTransport/82d8-eb72-b097/control</controlURL>
                <eventSubURL>AVTransport/82d8-eb72-b097/event</eventSubURL>
                </service>
                <service>
                <serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType>
                <serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId>
                <SCPDURL>ConnectionManager/82d8-eb72-b097/scpd.xml</SCPDURL>
                <controlURL>ConnectionManager/82d8-eb72-b097/control</controlURL>
                <eventSubURL>ConnectionManager/82d8-eb72-b097/event</eventSubURL>
                </service>
                <service>
                <serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>
                <serviceId>urn:upnp-org:serviceId:RenderingControl</serviceId>
                <SCPDURL>RenderingControl/82d8-eb72-b097/scpd.xml</SCPDURL>
                <controlURL>RenderingControl/82d8-eb72-b097/control</controlURL>
                <eventSubURL>RenderingControl/82d8-eb72-b097/event</eventSubURL>
                </service>
            </serviceList>
    </device>
</root>"""
    return Response(xml, mimetype="text/xml")


_DATA = {
    'CURRENT_URI': '',
    'CURRENT_SRT': '',
}


def is_stop(request):
    return b'<u:Stop' in request.data

def is_play(data):
    return b'<u:Play' in request.data

def is_setav(data):
    return b'SetAVTransportURI' in request.data

def is_gettrans(data):
    return b'u:GetTransportInfo' in request.data

def is_getpos(data):
    return b'u:GetPositionInfo' in request.data


@app.route('/AVTransport/82d8-eb72-b097/control', methods=['POST'])
def control():
    if is_setav(request):
        root = ET.fromstring(request.data)
        current_uri = root.find('.//CurrentURI').text

        metadata = root.find('.//CurrentURIMetaData').text

        current_srt = None
        try:
            metadata = ET.fromstring(html.unescape(metadata))
            for res in metadata.findall('.//{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}res'):
                if res.get('type') == 'text/subtitle':
                    current_srt = res.text.strip()
                    break
        except:
            pass

        print('+++ SetAV:', current_uri)
        _DATA['CURRENT_URI'] = current_uri
        print('+++ SRT:', current_srt)
        if current_srt:
            _DATA['CURRENT_SRT'] = current_srt
        return Response(XML_AVSET_DONE, mimetype="text/xml")
    elif is_play(request):
        url = _DATA['CURRENT_URI']
        srt = _DATA['CURRENT_SRT']
        print('+++ Playing', url)
        renderer.play_media(url, srt)
        return Response(XML_PLAY_DONE, mimetype="text/xml")

    elif is_getpos(request):
        print('+++ GetPositionInfo +++')
        return Response(XML_POSINFO, mimetype="text/xml")

    elif is_gettrans(request):
        print('+++ GetTransportInfo +++')
        return Response(XML_TRANSINFO, mimetype="text/xml")

    elif is_stop(request):
        print('\n+++ Stopping +++')
        _DATA['CURRENT_URI'] = ''
        _DATA['CURRENT_SRT'] = ''
        renderer.stop_media()
        return Response(XML_STOP_DONE, mimetype="text/xml")

    print(request.data)
    return Response('Action Not Supported', status=500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
