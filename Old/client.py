import os, socket, json, base64, argparse

def send_json(host, port, payload, timeout=5):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(timeout)
    s.sendto(json.dumps(payload).encode("utf-8"), (host, port))
    try:
        data,_ = s.recvfrom(65507)
        return json.loads(data.decode("utf-8"))
    except Exception:
        return {"ok": False, "error": "timeout"}

ap = argparse.ArgumentParser()
ap.add_argument("--server-host", required=True)
ap.add_argument("--server-port", type=int, default=5001)
ap.add_argument("--dir", default="./tmp")
args = ap.parse_args()

os.makedirs(args.dir, exist_ok=True)
files = []
for root, _, fs in os.walk(args.dir):
    for f in fs:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, args.dir)
        files.append((p, rel))

print(f"[client] sending {len(files)} file(s) from {args.dir} -> {args.server_host}:{args.server_port}")
for p, rel in files:
    with open(p, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("utf-8")
    resp = send_json(args.server_host, args.server_port, {"action":"ADD","filename":rel,"b64":b64})
    print(f"[client] {rel}: {resp}")