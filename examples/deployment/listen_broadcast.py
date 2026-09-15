# -*- coding: utf-8 -*-
"""Passively listen for broadcasts from the directly-cabled Seewo
(LLMNR 5355, NetBIOS 137/138, DHCP 68) and print sender source IPs.
Safe: listens only, never responds.
"""
import socket
import threading
import time

PORTS = [5355, 137, 138, 68, 67]
stop = threading.Event()
lock = threading.Lock()
seen = {}

def listen(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("0.0.0.0", port))
        s.settimeout(1)
        while not stop.is_set():
            try:
                data, addr = s.recvfrom(2048)
            except socket.timeout:
                continue
            src = addr[0]
            with lock:
                seen[src] = seen.get(src, 0) + 1
                print("[%s] src=%s port=%s len=%d (total=%d)" %
                      (time.strftime("%H:%M:%S"), src, port, len(data), seen[src]), flush=True)
    except Exception as e:
        print("[listen %d] err: %s" % (port, e), flush=True)

def main():
    threads = [threading.Thread(target=listen, args=(p,), daemon=True) for p in PORTS]
    for t in threads:
        t.start()
    print("Listening 60s on USB link for Seewo broadcasts...", flush=True)
    time.sleep(60)
    stop.set()
    print("--- Summary ---", flush=True)
    for src, cnt in sorted(seen.items(), key=lambda x: -x[1]):
        print("SRC_IP=%s packets=%d" % (src, cnt), flush=True)

if __name__ == "__main__":
    main()
