import argparse
import json
import logging
import socket

from tiny_ssdp import SSDP_MULTICAST_IP, SSDP_PORT

MSEARCH_MSG = (
    'M-SEARCH * HTTP/1.1\r\n'
    f'HOST: {SSDP_MULTICAST_IP}:{SSDP_PORT}\r\n'
    'MAN: "ssdp:discover"\r\n'
    'MX: 1\r\n'
    'ST: urn:schemas-upnp-org:service:AVTransport:1\r\n'
    '\r\n'
)

logger = logging.getLogger('tiny_cli')


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

    return device


def get_dlna_devices():
    # Create the UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(1.2)

    # Send the M-SEARCH message to the SSDP multicast address
    logger.debug("Sending M-SEARCH...")
    sock.sendto(MSEARCH_MSG.encode('utf-8'), (SSDP_MULTICAST_IP, SSDP_PORT))

    result = {'devices': []}
    known_locations = set()
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            device = _parse_ssdp_response(data.decode('utf-8'))
            location = device.get('location')
            logger.debug(f'got reply from {addr}, Location: {location}')
            if device and location not in known_locations:
                result['devices'].append(device)
                known_locations.add(location)
        except socket.timeout:
            break

    print(json.dumps(result, sort_keys=True, indent=2))


def main():
    logging.basicConfig(
        level=logging.ERROR,
        format='[%(asctime)s][%(levelname)s] %(message)s',
    )

    parser = argparse.ArgumentParser(prog='tiny-cli')
    subparsers = parser.add_subparsers(dest='command', help='Choose a command', required=True)

    greet_parser = subparsers.add_parser('list', help='List available DLNA devices')
    greet_parser.add_argument('-v', dest='verbose', action='store_true', help='Enable verbose logs')

    args = parser.parse_args()
    if args.command == 'list':
        if args.verbose:
            logger.setLevel(logging.DEBUG)

        get_dlna_devices()


if __name__ == '__main__':
    main()
