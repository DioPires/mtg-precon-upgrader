# Scratch (DEC-1103 delta 2): logs each TCP connection to 127.0.0.1:<port> and
# its first bytes, then closes it. A TLS hello starts with 16 03.
import socket, sys, threading, time
port, log = int(sys.argv[1]), sys.argv[2]

def note(line):
    with open(log, 'a') as f:
        f.write(f"{time.strftime('%H:%M:%S')} {line}\n")

def serve(conn, addr):
    try:
        conn.settimeout(2)
        try:
            head = conn.recv(16)
        except socket.timeout:
            head = b''
        kind = 'TLS hello' if head[:2] == b'\x16\x03' else ('HTTP ' + head.split(b' ')[0].decode('latin-1') if head else 'no bytes')
        note(f"CONNECTION from {addr[0]}:{addr[1]} first bytes {head[:6].hex()} ({kind})")
    finally:
        conn.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', port))
s.listen(16)
note(f"LISTENING 127.0.0.1:{port}")
while True:
    c, a = s.accept()
    threading.Thread(target=serve, args=(c, a), daemon=True).start()
