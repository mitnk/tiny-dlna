import socket

SSDP_MULTICAST = '239.255.255.250'
SSDP_PORT = 1900
LOCATION = "http://192.168.1.228:5000/description.xml"
USN = 'uuid:dlna-tiny-render-t001::upnp:rootdevice'

ssdp_response = (
    'HTTP/1.1 200 OK\r\n'
    'CACHE-CONTROL: max-age=1800\r\n'
    'EXT:\r\n'
    f'LOCATION: {LOCATION}\r\n'
    'HOSTNAME: 192.168.1.228\r\n'
    'SERVER: Custom/1.0 UPnP/1.0 DLNADOC/1.50\r\n'
    f'ST: urn:schemas-upnp-org:service:AVTransport:1\r\n'
    f'USN: {USN}\r\n'
    '\r\n'
)

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
            print(f'Received M-SEARCH from {addr}, sending response...')
            sock.sendto(ssdp_response.encode('utf-8'), addr)

if __name__ == '__main__':
    ssdp_listener()
