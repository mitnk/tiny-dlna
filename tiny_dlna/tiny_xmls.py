XML_META = """
<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
  xmlns:sec="http://www.sec.co.kr/"
  xmlns:pv="http://www.pv.com/pvns/">
  <item id="0" parentID="-1" restricted="false">
    <dc:title>{title}</dc:title>
    <upnp:class>object.item.videoItem</upnp:class>
    <res protocolInfo="http-get:*:video/mp4:DLNA.ORG_OP=01;DLNA.ORG_FLAGS=01700000000000000000000000000000">{url_video}</res>{subtitle}
  </item>
</DIDL-Lite>"""

XML_SUBTITLE = """
    <res protocolInfo="http-get:*:text/srt:*">{url_srt}</res>
    <sec:CaptionInfo sec:type="srt">{url_srt}</sec:CaptionInfo>
    <sec:CaptionInfoEx sec:type="srt">{url_srt}</sec:CaptionInfoEx>
    <pv:subtitleFileUri>{url_srt}</pv:subtitleFileUri>"""

XML_SETAV = """<?xml version='1.0' encoding='utf-8'?>
<s:Envelope
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
    xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{url_video}</CurrentURI>
      <CurrentURIMetaData>{metadata}</CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>
"""

XML_PLAY = """<?xml version='1.0' encoding='utf-8'?>
<s:Envelope
    xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>
  </s:Body>
</s:Envelope>
"""

XML_STOP = """<?xml version='1.0' encoding='utf-8'?>
<s:Envelope
    xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Stop>
  </s:Body>
</s:Envelope>
"""

XML_SEEK_PTN = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope
    xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Seek xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Unit>REL_TIME</Unit>
      <Target>{}</Target>
    </u:Seek>
  </s:Body>
</s:Envelope>
"""

XML_DESC_PTN = """<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:dlna="urn:schemas-dlna-org:device-1-0" xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <device>
    <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
    <friendlyName>{}</friendlyName>
    <UDN>uuid:{}</UDN>
    <manufacturer>mitnk</manufacturer>
    <modelName>Tiny-Render</modelName>
    <modelDescription>AVTransport Media Renderer</modelDescription>
    <dlna:X_DLNADOC xmlns:dlna="urn:schemas-dlna-org:device-1-0">DMR-1.50</dlna:X_DLNADOC>
    <serviceList>
      <service>
        <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
        <controlURL>AVTransport/control</controlURL>
        <SCPDURL>dlna/AVTransport.xml</SCPDURL>
      </service>
      <service>
        <serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:RenderingControl</serviceId>
        <controlURL>RenderingControl/action</controlURL>
        <eventSubURL>RenderingControl/event</eventSubURL>
        <SCPDURL>dlna/RenderingControl.xml</SCPDURL>
      </service>
      <service>
        <serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId>
        <controlURL>ConnectionManager/action</controlURL>
        <eventSubURL>ConnectionManager/event</eventSubURL>
        <SCPDURL>dlna/ConnectionManager.xml</SCPDURL>
      </service>
    </serviceList>
  </device>
</root>"""

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
    <u:PlayResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"""

XML_SEEK_DONE = """
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:SeekResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"""

XML_POSINFO = """
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetPositionInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <Track>0</Track>
      <TrackDuration>01:23:45</TrackDuration>
      <RelTime>{0}</RelTime>
      <AbsTime>{0}</AbsTime>
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

XML_DLNA_AVT = """<?xml version="1.0" encoding="UTF-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<actionList>
<action>
<name>GetCurrentTransportActions</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Actions</name>
<direction>out</direction>
<relatedStateVariable>CurrentTransportActions</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetDeviceCapabilities</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>PlayMedia</name>
<direction>out</direction>
<relatedStateVariable>PossiblePlaybackStorageMedia</relatedStateVariable>
</argument>
<argument>
<name>RecMedia</name>
<direction>out</direction>
<relatedStateVariable>PossibleRecordStorageMedia</relatedStateVariable>
</argument>
<argument>
<name>RecQualityModes</name>
<direction>out</direction>
<relatedStateVariable>PossibleRecordQualityModes</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetMediaInfo</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>NrTracks</name>
<direction>out</direction>
<relatedStateVariable>NumberOfTracks</relatedStateVariable>
</argument>
<argument>
<name>MediaDuration</name>
<direction>out</direction>
<relatedStateVariable>CurrentMediaDuration</relatedStateVariable>
</argument>
<argument>
<name>CurrentURI</name>
<direction>out</direction>
<relatedStateVariable>AVTransportURI</relatedStateVariable>
</argument>
<argument>
<name>CurrentURIMetaData</name>
<direction>out</direction>
<relatedStateVariable>AVTransportURIMetaData</relatedStateVariable>
</argument>
<argument>
<name>NextURI</name>
<direction>out</direction>
<relatedStateVariable>NextAVTransportURI</relatedStateVariable>
</argument>
<argument>
<name>NextURIMetaData</name>
<direction>out</direction>
<relatedStateVariable>NextAVTransportURIMetaData</relatedStateVariable>
</argument>
<argument>
<name>PlayMedium</name>
<direction>out</direction>
<relatedStateVariable>PlaybackStorageMedium</relatedStateVariable>
</argument>
<argument>
<name>RecordMedium</name>
<direction>out</direction>
<relatedStateVariable>RecordStorageMedium</relatedStateVariable>
</argument>
<argument>
<name>WriteStatus</name>
<direction>out</direction>
<relatedStateVariable>RecordMediumWriteStatus</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetPositionInfo</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Track</name>
<direction>out</direction>
<relatedStateVariable>CurrentTrack</relatedStateVariable>
</argument>
<argument>
<name>TrackDuration</name>
<direction>out</direction>
<relatedStateVariable>CurrentTrackDuration</relatedStateVariable>
</argument>
<argument>
<name>TrackMetaData</name>
<direction>out</direction>
<relatedStateVariable>CurrentTrackMetaData</relatedStateVariable>
</argument>
<argument>
<name>TrackURI</name>
<direction>out</direction>
<relatedStateVariable>CurrentTrackURI</relatedStateVariable>
</argument>
<argument>
<name>RelTime</name>
<direction>out</direction>
<relatedStateVariable>RelativeTimePosition</relatedStateVariable>
</argument>
<argument>
<name>AbsTime</name>
<direction>out</direction>
<relatedStateVariable>AbsoluteTimePosition</relatedStateVariable>
</argument>
<argument>
<name>RelCount</name>
<direction>out</direction>
<relatedStateVariable>RelativeCounterPosition</relatedStateVariable>
</argument>
<argument>
<name>AbsCount</name>
<direction>out</direction>
<relatedStateVariable>AbsoluteCounterPosition</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetTransportInfo</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>CurrentTransportState</name>
<direction>out</direction>
<relatedStateVariable>TransportState</relatedStateVariable>
</argument>
<argument>
<name>CurrentTransportStatus</name>
<direction>out</direction>
<relatedStateVariable>TransportStatus</relatedStateVariable>
</argument>
<argument>
<name>CurrentSpeed</name>
<direction>out</direction>
<relatedStateVariable>TransportPlaySpeed</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetTransportSettings</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>PlayMode</name>
<direction>out</direction>
<relatedStateVariable>CurrentPlayMode</relatedStateVariable>
</argument>
<argument>
<name>RecQualityMode</name>
<direction>out</direction>
<relatedStateVariable>CurrentRecordQualityMode</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>Next</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>Pause</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>Play</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Speed</name>
<direction>in</direction>
<relatedStateVariable>TransportPlaySpeed</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>Previous</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>Seek</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Unit</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_SeekMode</relatedStateVariable>
</argument>
<argument>
<name>Target</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_SeekTarget</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>SetAVTransportURI</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>CurrentURI</name>
<direction>in</direction>
<relatedStateVariable>AVTransportURI</relatedStateVariable>
</argument>
<argument>
<name>CurrentURIMetaData</name>
<direction>in</direction>
<relatedStateVariable>AVTransportURIMetaData</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>SetPlayMode</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>NewPlayMode</name>
<direction>in</direction>
<relatedStateVariable>CurrentPlayMode</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>Stop</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
</argumentList>
</action>
</actionList>
<serviceStateTable>
<stateVariable sendEvents="no">
<name>CurrentPlayMode</name>
<dataType>string</dataType>
<defaultValue>NORMAL</defaultValue>
<allowedValueList>
<allowedValue>NORMAL</allowedValue>
<allowedValue>REPEAT_ONE</allowedValue>
<allowedValue>REPEAT_ALL</allowedValue>
<allowedValue>SHUFFLE</allowedValue>
<allowedValue>SHUFFLE_NOREPEAT</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>RecordStorageMedium</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>NOT_IMPLEMENTED</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="yes">
<name>LastChange</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>RelativeTimePosition</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentTrackTitle</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>DisplayCurrentSubtitle</name>
<dataType>boolean</dataType>
<defaultValue>1</defaultValue>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentTrackURI</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentTrackDuration</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentRecordQualityMode</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>NOT_IMPLEMENTED</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentMediaDuration</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>AbsoluteCounterPosition</name>
<dataType>i4</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>RelativeCounterPosition</name>
<dataType>i4</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_InstanceID</name>
<dataType>ui4</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>AVTransportURI</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>TransportState</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>STOPPED</allowedValue>
<allowedValue>PAUSED_PLAYBACK</allowedValue>
<allowedValue>PLAYING</allowedValue>
<allowedValue>TRANSITIONING</allowedValue>
<allowedValue>NO_MEDIA_PRESENT</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentTrackMetaData</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>NextAVTransportURI</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>PossibleRecordQualityModes</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>NOT_IMPLEMENTED</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentTrack</name>
<dataType>ui4</dataType>
<allowedValueRange>
<minimum>0</minimum>
<maximum>65535</maximum>
<step>1</step>
</allowedValueRange>
</stateVariable>
<stateVariable sendEvents="no">
<name>AbsoluteTimePosition</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>NextAVTransportURIMetaData</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>PlaybackStorageMedium</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>NONE</allowedValue>
<allowedValue>UNKNOWN</allowedValue>
<allowedValue>CD-DA</allowedValue>
<allowedValue>HDD</allowedValue>
<allowedValue>NETWORK</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>CurrentTransportActions</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>RecordMediumWriteStatus</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>NOT_IMPLEMENTED</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>PossiblePlaybackStorageMedia</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>NONE</allowedValue>
<allowedValue>UNKNOWN</allowedValue>
<allowedValue>CD-DA</allowedValue>
<allowedValue>HDD</allowedValue>
<allowedValue>NETWORK</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>AVTransportURIMetaData</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>NumberOfTracks</name>
<dataType>ui4</dataType>
<allowedValueRange>
<minimum>0</minimum>
<maximum>65535</maximum>
</allowedValueRange>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_SeekMode</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>REL_TIME</allowedValue>
<allowedValue>TRACK_NR</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_SeekTarget</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>PossibleRecordStorageMedia</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>NOT_IMPLEMENTED</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>TransportStatus</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>OK</allowedValue>
<allowedValue>ERROR_OCCURRED</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>TransportPlaySpeed</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>0.5</allowedValue>
<allowedValue>0.75</allowedValue>
<allowedValue>1</allowedValue>
<allowedValue>1.25</allowedValue>
<allowedValue>1.5</allowedValue>
<allowedValue>2</allowedValue>
</allowedValueList>
</stateVariable>
</serviceStateTable>
</scpd>
"""

XML_DLNA_RENDER_CTRL = """<?xml version="1.0" encoding="UTF-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<actionList>
<action>
<name>GetMute</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Channel</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_Channel</relatedStateVariable>
</argument>
<argument>
<name>CurrentMute</name>
<direction>out</direction>
<relatedStateVariable>Mute</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetVolume</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Channel</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_Channel</relatedStateVariable>
</argument>
<argument>
<name>CurrentVolume</name>
<direction>out</direction>
<relatedStateVariable>Volume</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetVolumeDB</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Channel</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_Channel</relatedStateVariable>
</argument>
<argument>
<name>CurrentVolume</name>
<direction>out</direction>
<relatedStateVariable>VolumeDB</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetVolumeDBRange</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Channel</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_Channel</relatedStateVariable>
</argument>
<argument>
<name>MinValue</name>
<direction>out</direction>
<relatedStateVariable>VolumeDB</relatedStateVariable>
</argument>
<argument>
<name>MaxValue</name>
<direction>out</direction>
<relatedStateVariable>VolumeDB</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>ListPresets</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>CurrentPresetNameList</name>
<direction>out</direction>
<relatedStateVariable>PresetNameList</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>SelectPreset</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>PresetName</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_PresetName</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>SetMute</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Channel</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_Channel</relatedStateVariable>
</argument>
<argument>
<name>DesiredMute</name>
<direction>in</direction>
<relatedStateVariable>Mute</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>SetVolume</name>
<argumentList>
<argument>
<name>InstanceID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_InstanceID</relatedStateVariable>
</argument>
<argument>
<name>Channel</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_Channel</relatedStateVariable>
</argument>
<argument>
<name>DesiredVolume</name>
<direction>in</direction>
<relatedStateVariable>Volume</relatedStateVariable>
</argument>
</argumentList>
</action>
</actionList>
<serviceStateTable>
<stateVariable sendEvents="yes">
<name>LastChange</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_Channel</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>Master</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_InstanceID</name>
<dataType>ui4</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>Volume</name>
<dataType>ui2</dataType>
<allowedValueRange>
<minimum>0</minimum>
<maximum>100</maximum>
<step>1</step>
</allowedValueRange>
</stateVariable>
<stateVariable sendEvents="no">
<name>Mute</name>
<dataType>boolean</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>PresetNameList</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>FactoryDefaults</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_PresetName</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>FactoryDefaults</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>VolumeDB</name>
<dataType>i2</dataType>
<allowedValueRange>
<minimum>-32767</minimum>
<maximum>32767</maximum>
</allowedValueRange>
</stateVariable>
</serviceStateTable>
</scpd>
"""

XML_DLNA_CONN_MANAGER = """ <?xml version="1.0" encoding="UTF-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<actionList>
<action>
<name>GetCurrentConnectionInfo</name>
<argumentList>
<argument>
<name>ConnectionID</name>
<direction>in</direction>
<relatedStateVariable>A_ARG_TYPE_ConnectionID</relatedStateVariable>
</argument>
<argument>
<name>RcsID</name>
<direction>out</direction>
<relatedStateVariable>A_ARG_TYPE_RcsID</relatedStateVariable>
</argument>
<argument>
<name>AVTransportID</name>
<direction>out</direction>
<relatedStateVariable>A_ARG_TYPE_AVTransportID</relatedStateVariable>
</argument>
<argument>
<name>ProtocolInfo</name>
<direction>out</direction>
<relatedStateVariable>A_ARG_TYPE_ProtocolInfo</relatedStateVariable>
</argument>
<argument>
<name>PeerConnectionManager</name>
<direction>out</direction>
<relatedStateVariable>A_ARG_TYPE_ConnectionManager</relatedStateVariable>
</argument>
<argument>
<name>PeerConnectionID</name>
<direction>out</direction>
<relatedStateVariable>A_ARG_TYPE_ConnectionID</relatedStateVariable>
</argument>
<argument>
<name>Direction</name>
<direction>out</direction>
<relatedStateVariable>A_ARG_TYPE_Direction</relatedStateVariable>
</argument>
<argument>
<name>Status</name>
<direction>out</direction>
<relatedStateVariable>A_ARG_TYPE_ConnectionStatus</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetProtocolInfo</name>
<argumentList>
<argument>
<name>Source</name>
<direction>out</direction>
<relatedStateVariable>SourceProtocolInfo</relatedStateVariable>
</argument>
<argument>
<name>Sink</name>
<direction>out</direction>
<relatedStateVariable>SinkProtocolInfo</relatedStateVariable>
</argument>
</argumentList>
</action>
<action>
<name>GetCurrentConnectionIDs</name>
<argumentList>
<argument>
<name>ConnectionIDs</name>
<direction>out</direction>
<relatedStateVariable>CurrentConnectionIDs</relatedStateVariable>
</argument>
</argumentList>
</action>
</actionList>
<serviceStateTable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_ProtocolInfo</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_ConnectionStatus</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>OK</allowedValue>
<allowedValue>ContentFormatMismatch</allowedValue>
<allowedValue>InsufficientBandwidth</allowedValue>
<allowedValue>UnreliableChannel</allowedValue>
<allowedValue>Unknown</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_AVTransportID</name>
<dataType>i4</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_RcsID</name>
<dataType>i4</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_ConnectionID</name>
<dataType>i4</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_ConnectionManager</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="yes">
<name>SourceProtocolInfo</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="yes">
<name>SinkProtocolInfo</name>
<dataType>string</dataType>
</stateVariable>
<stateVariable sendEvents="no">
<name>A_ARG_TYPE_Direction</name>
<dataType>string</dataType>
<allowedValueList>
<allowedValue>Input</allowedValue>
<allowedValue>Output</allowedValue>
</allowedValueList>
</stateVariable>
<stateVariable sendEvents="yes">
<name>CurrentConnectionIDs</name>
<dataType>string</dataType>
</stateVariable>
</serviceStateTable>
</scpd>
"""
