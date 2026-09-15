# -*- coding: utf-8 -*-
"""
Minimal DHCP server for direct-cable deployment to the Seewo.
Assigns 192.168.53.117 to the first client that DISCOVERs.
Binds to the USB ethernet IP 192.168.53.100.
Run as Administrator: python dhcp_server.py
"""
import socket
import struct
import sys
import time

SERVER_IP = "192.168.53.100"   # our USB NIC static IP
OFFER_IP  = "192.168.53.117"   # IP we hand the Seewo (matches original spec)
SUBNET    = "255.255.255.0"
LEASE     = 600

def build_option(code, data):
    return bytes([code, len(data)]) + data

def build_offer_packet(request, msg_type):
    # parse client MAC (chaddr) from request
    if len(request) >= 28:
        chaddr = request[28:44]
    else:
        chaddr = b"\x00" * 16
    xid = request[4:8]
    flags = request[10:12]
    yiaddr = socket.inet_aton(OFFER_IP)
    siaddr = socket.inet_aton("0.0.0.0")
    giaddr = b"\x00\x00\x00\x00"
    # BOOTP header
    header = b"\x02"          # op BOOTREPLY
    header += b"\x01\x06\x00" # htype eth, hlen 6, hops 0
    header += xid
    header += b"\x00\x00"     # secs
    header += flags
    header += b"\x00\x00\x00\x00"  # ciaddr
    header += yiaddr
    header += siaddr
    header += giaddr
    header += chaddr
    header += b"\x00" * 192   # sname(64)+file(128)
    # magic cookie
    cookie = b"\x63\x82\x53\x63"
    opts = bytes([msg_type, 1, 1])                     # 53: DHCP message type (1 byte: 2=OFFER,5=ACK)
    opts += build_option(54, socket.inet_aton(SERVER_IP))  # server id
    opts += build_option(51, struct.pack("!I", LEASE))     # lease time
    opts += build_option(1, socket.inet_aton(SUBNET))      # subnet mask
    opts += build_option(3, socket.inet_aton(SERVER_IP))   # router = our ip
    opts += b"\xff"                                      # end
    return header + cookie + opts

def parse_options(payload):
    """Return dict of option code -> value bytes from a DHCP payload."""
    cookie_idx = payload.find(b"\x63\x82\x53\x63")
    if cookie_idx < 0:
        return {}
    i = cookie_idx + 4
    opts = {}
    while i < len(payload):
        code = payload[i]
        if code == 0:
            i += 1
            continue
        if code == 255:
            break
        if i + 2 > len(payload):
            break
        ln = payload[i + 1]
        if i + 2 + ln > len(payload):
            break
        opts[code] = payload[i + 2:i + 2 + ln]
        i += 2 + ln
    return opts

def main():
    print("DHCP server starting on %s -> offers %s" % (SERVER_IP, OFFER_IP), flush=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind((SERVER_IP, 67))
    s.settimeout(2)
    start = time.time()
    while time.time() - start < 180:   # run up to 3 minutes
        try:
            data, addr = s.recvfrom(4096)
        except socket.timeout:
            continue
        if len(data) < 240:
            continue
        opts = parse_options(data)
        mtype = opts.get(53, b"\x00")[0] if 53 in opts else 0
        if mtype == 1:   # DISCOVER
            print("[DISCOVER] from %s xid=%s chaddr=%s -> send OFFER %s" %
                  (addr[0], data[4:8].hex(), data[28:34].hex().upper(), OFFER_IP), flush=True)
            pkt = build_offer_packet(data, 2)
            s.sendto(pkt, ("255.255.255.255", 68))
        elif mtype == 3:  # REQUEST
            print("[REQUEST] from %s chaddr=%s -> send ACK %s" %
                  (addr[0], data[28:34].hex().upper(), OFFER_IP), flush=True)
            pkt = build_offer_packet(data, 5)
            s.sendto(pkt, ("255.255.255.255", 68))
            print("CLIENT_ASSIGNED=%s" % OFFER_IP, flush=True)
    print("DHCP server stopped after 180s.", flush=True)

if __name__ == "__main__":
    main()
