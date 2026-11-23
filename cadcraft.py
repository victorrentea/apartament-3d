"""Tiny client for the CADCraft desktop control channel (JSON lines on 127.0.0.1:PORT)."""
import json, socket, sys, os
PORT = 7979
TOKEN = open(os.path.expanduser(f'~/.cache/cadcraft-control-{PORT}.token')).read().strip()
_id = 0
def call(method, **params):
    global _id; _id += 1
    with socket.create_connection(('127.0.0.1', PORT), timeout=70) as s:
        s.sendall((json.dumps({'id': _id, 'method': method, 'params': params, 'token': TOKEN}) + '\n').encode())
        buf = b''
        while not buf.endswith(b'\n'):
            chunk = s.recv(1 << 20)
            if not chunk: break
            buf += chunk
    return json.loads(buf)
if __name__ == '__main__':
    print(json.dumps(call(sys.argv[1], **json.loads(sys.argv[2] if len(sys.argv) > 2 else '{}')))[:1500])
