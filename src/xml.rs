//! SOAP / UPnP XML documents sent and served by tiny-dlna.

pub const AVTRANSPORT_SCPD: &str = include_str!("../xml/AVTransport.xml");
pub const RENDERING_CONTROL_SCPD: &str = include_str!("../xml/RenderingControl.xml");
pub const CONNECTION_MANAGER_SCPD: &str = include_str!("../xml/ConnectionManager.xml");

/// Escape text for use inside an XML element or attribute.
pub fn escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(c),
        }
    }
    out
}

/// Resolve entity references (`&amp;`, `&#38;`, `&#x26;`, ...).
/// Unknown entities are kept as they are.
pub fn unescape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(pos) = rest.find('&') {
        out.push_str(&rest[..pos]);
        rest = &rest[pos..];
        let decoded = rest[1..].find(';').filter(|&n| n <= 10).and_then(|n| {
            let name = &rest[1..n + 1];
            let c = match name {
                "amp" => Some('&'),
                "lt" => Some('<'),
                "gt" => Some('>'),
                "quot" => Some('"'),
                "apos" => Some('\''),
                "nbsp" => Some('\u{a0}'),
                _ => {
                    let code =
                        if let Some(hex) = name.strip_prefix("#x").or(name.strip_prefix("#X")) {
                            u32::from_str_radix(hex, 16).ok()
                        } else if let Some(dec) = name.strip_prefix('#') {
                            dec.parse().ok()
                        } else {
                            None
                        };
                    code.and_then(char::from_u32)
                }
            };
            c.map(|c| (c, n + 2))
        });
        match decoded {
            Some((c, len)) => {
                out.push(c);
                rest = &rest[len..];
            }
            None => {
                out.push('&');
                rest = &rest[1..];
            }
        }
    }
    out.push_str(rest);
    out
}

/// DIDL-Lite metadata describing a video (and optional subtitle).
pub fn didl_metadata(title: &str, url_video: &str, url_srt: Option<&str>) -> String {
    let subtitle = match url_srt {
        Some(srt) => {
            let srt = escape(srt);
            format!(
                r#"
    <res protocolInfo="http-get:*:text/srt:*">{srt}</res>
    <sec:CaptionInfo sec:type="srt">{srt}</sec:CaptionInfo>
    <sec:CaptionInfoEx sec:type="srt">{srt}</sec:CaptionInfoEx>
    <pv:subtitleFileUri>{srt}</pv:subtitleFileUri>"#
            )
        }
        None => String::new(),
    };
    format!(
        r#"<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
  xmlns:sec="http://www.sec.co.kr/"
  xmlns:pv="http://www.pv.com/pvns/">
  <item id="0" parentID="-1" restricted="false">
    <dc:title>{title}</dc:title>
    <upnp:class>object.item.videoItem</upnp:class>
    <res protocolInfo="http-get:*:video/mp4:DLNA.ORG_OP=01;DLNA.ORG_FLAGS=01700000000000000000000000000000">{url_video}</res>{subtitle}
  </item>
</DIDL-Lite>"#,
        title = escape(title),
        url_video = escape(url_video),
    )
}

pub fn set_av_transport_uri(url_video: &str, metadata: &str) -> String {
    format!(
        r#"<?xml version='1.0' encoding='utf-8'?>
<s:Envelope
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
    xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{}</CurrentURI>
      <CurrentURIMetaData>{}</CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>
"#,
        escape(url_video),
        escape(metadata),
    )
}

pub const PLAY: &str = r#"<?xml version='1.0' encoding='utf-8'?>
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
"#;

pub const STOP: &str = r#"<?xml version='1.0' encoding='utf-8'?>
<s:Envelope
    xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Stop>
  </s:Body>
</s:Envelope>
"#;

pub fn seek(target: &str) -> String {
    format!(
        r#"<?xml version="1.0" encoding="utf-8"?>
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
"#,
        escape(target)
    )
}

/// Device description served at `/description.xml`.
pub fn description(friendly_name: &str, uuid: &str) -> String {
    format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
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
</root>"#,
        escape(friendly_name),
        escape(uuid),
    )
}

pub const SET_AV_TRANSPORT_URI_RESPONSE: &str = r#"
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetAVTransportURIResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"#;

pub const PLAY_RESPONSE: &str = r#"
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:PlayResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"#;

pub const SEEK_RESPONSE: &str = r#"
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:SeekResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"#;

pub const STOP_RESPONSE: &str = r#"
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:StopResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1"/>
  </s:Body>
</s:Envelope>
"#;

pub const TRANSPORT_INFO_RESPONSE: &str = r#"
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetTransportInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <CurrentTransportState>PLAYING</CurrentTransportState>
      <CurrentTransportStatus>OK</CurrentTransportStatus>
      <CurrentSpeed>1</CurrentSpeed>
    </u:GetTransportInfoResponse>
  </s:Body>
</s:Envelope>
"#;

pub fn position_info_response(rel_time: &str) -> String {
    format!(
        r#"
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetPositionInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <Track>0</Track>
      <TrackDuration>01:23:45</TrackDuration>
      <RelTime>{rel_time}</RelTime>
      <AbsTime>{rel_time}</AbsTime>
      <RelCount>2147483647</RelCount>
      <AbsCount>2147483647</AbsCount>
    </u:GetPositionInfoResponse>
  </s:Body>
</s:Envelope>
"#
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escape_roundtrip() {
        let s = r#"a&b<c>"d"#;
        assert_eq!(escape(s), "a&amp;b&lt;c&gt;&quot;d");
        assert_eq!(unescape(&escape(s)), s);
    }

    #[test]
    fn unescape_numeric_and_unknown() {
        assert_eq!(unescape("&#38;&#x3C;&foo; & x"), "&<&foo; & x");
    }

    #[test]
    fn static_documents_parse() {
        for doc in [
            AVTRANSPORT_SCPD,
            RENDERING_CONTROL_SCPD,
            CONNECTION_MANAGER_SCPD,
        ] {
            roxmltree::Document::parse(doc).unwrap();
        }
        roxmltree::Document::parse(&description("A & B <x>", "u-1")).unwrap();
        let meta = didl_metadata("t&t", "http://h/v?a=1&b=2", Some("http://h/s.srt"));
        roxmltree::Document::parse(&meta).unwrap();
        roxmltree::Document::parse(&set_av_transport_uri("http://h/v?a=1&b=2", &meta)).unwrap();
    }
}
