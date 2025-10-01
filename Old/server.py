import os, socket, json, base64, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--host", default="0.0.0.0")
ap.add_argument("--port", type=int, default=5001)
ap.add_argument("--dir",  default="./tmp")
args = ap.parse_args()

os.makedirs(args.dir, exist_ok=True)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((args.host, args.port))
print(f"[server] UDP {args.host}:{args.port} dir={args.dir}")

while True:
    data, addr = sock.recvfrom(65507)
    try:
        msg = json.loads(data.decode("utf-8"))
    except Exception as e:
        continue

    act = msg.get("action")
    if act == "ADD":
        fname = msg.get("filename"); b64 = msg.get("b64")
        if not fname or not b64:
            sock.sendto(b'{"ok":false}', addr); continue
        try:
            content = base64.b64decode(b64.encode("utf-8"))
            path = os.path.join(args.dir, fname)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f: f.write(content)
            print(f"[server] wrote {fname} ({len(content)} bytes)")
            sock.sendto(b'{"ok":true}', addr)
        except Exception as e:
            sock.sendto(json.dumps({"ok":False,"error":str(e)}).encode(), addr)
    elif act == "PING":
        sock.sendto(b'{"ok":true}', addr)
    else:
        sock.sendto(b'{"ok":false,"error":"unknown_action"}', addr)