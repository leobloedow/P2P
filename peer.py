#!/usr/bin/env python3
import os, sys, time, json, base64, argparse, socket, threading

def send_json(addr, payload, timeout=2.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(json.dumps(payload).encode("utf-8"), addr)
        data, _ = s.recvfrom(65507)
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None
    finally:
        s.close()

def b64_of(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def write_file(path, b64):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64.encode("utf-8")))

def file_fingerprint(path):
    st = os.stat(path)
    return (st.st_size, int(st.st_mtime))

# server
def server_loop(bind_host, bind_port, dir_path):
    os.makedirs(dir_path, exist_ok=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind_host, bind_port))
    print(f"[peer] em UDP {bind_host}:{bind_port} dir={dir_path}", flush=True)

    while True:
        data, addr = sock.recvfrom(65507)
        try:
            msg = json.loads(data.decode("utf-8"))
        except Exception:
            continue

        act = msg.get("action")
        if act == "LIST":
            files = []
            for root, _, fs in os.walk(dir_path):
                for f in fs:
                    p = os.path.join(root, f)
                    rel = os.path.relpath(p, dir_path)
                    try:
                        sz, mt = file_fingerprint(p)
                        files.append({"name": rel, "size": sz, "mtime": mt})
                    except FileNotFoundError:
                        pass
            resp = {"ok": True, "files": files}
            sock.sendto(json.dumps(resp).encode("utf-8"), addr)

        elif act == "ADD":
            name = msg.get("filename")
            b64 = msg.get("b64")
            mt = msg.get("mtime")
            if not name or not b64:
                sock.sendto(b'{"ok":false,"err":"missing"}', addr)
                continue
            dst = os.path.join(dir_path, name)
            try:
                write_file(dst, b64)
                if mt:
                    try:
                        os.utime(dst, times=(mt, mt))
                    except Exception:
                        pass
                print(f"[peer] ADD <- {name}", flush=True)
                sock.sendto(b'{"ok":true}', addr)
            except Exception as e:
                sock.sendto(json.dumps({"ok": False, "err": str(e)}).encode(), addr)

        elif act == "REMOVE":
            name = msg.get("filename")
            if not name:
                sock.sendto(b'{"ok":false,"err":"missing"}', addr)
                continue
            dst = os.path.join(dir_path, name)
            try:
                if os.path.exists(dst):
                    os.remove(dst)
                    print(f"[peer] REMOVE <- {name}", flush=True)
                sock.sendto(b'{"ok":true}', addr)
            except Exception as e:
                sock.sendto(json.dumps({"ok": False, "err": str(e)}).encode(), addr)

        elif act == "PING":
            sock.sendto(b'{"ok":true}', addr)

        else:
            sock.sendto(b'{"ok":false,"err":"unknown_action"}', addr)

# analisador
def snapshot(dir_path):
    snap = {}
    for root, _, fs in os.walk(dir_path):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, dir_path)
            try:
                sz, mt = file_fingerprint(p)
                snap[rel] = (sz, mt)
            except FileNotFoundError:
                pass
    return snap

def broadcast_add(peers, dir_path, rel, meta):
    p = os.path.join(dir_path, rel)
    if not os.path.isfile(p):
        return
    b64 = b64_of(p)
    payload = {"action": "ADD", "filename": rel, "b64": b64, "mtime": meta[1]}
    for (h, pr) in peers:
        send_json((h, pr), payload)

def broadcast_remove(peers, rel):
    payload = {"action": "REMOVE", "filename": rel}
    for (h, pr) in peers:
        send_json((h, pr), payload)

def initial_push(dir_path, peers):
    snap = snapshot(dir_path)
    for rel, meta in snap.items():
        broadcast_add(peers, dir_path, rel, meta)

def watcher_loop(dir_path, peers, interval=2):
    os.makedirs(dir_path, exist_ok=True)
    seen = snapshot(dir_path)
    if peers:
        initial_push(dir_path, peers)

    while True:
        time.sleep(interval)
        cur = snapshot(dir_path)
        for rel, meta in cur.items():
            if rel not in seen or seen[rel] != meta:
                print(f"[peer] change -> ADD {rel}", flush=True)
                broadcast_add(peers, dir_path, rel, meta)
        for rel in list(seen.keys()):
            if rel not in cur:
                print(f"[peer] change -> REMOVE {rel}", flush=True)
                broadcast_remove(peers, rel)
        seen = cur

# peers
def parse_peers(peers_str):
    peers = []
    if not peers_str:
        return peers
    for item in peers_str.split(","):
        item = item.strip()
        if not item:
            continue
        host, port = item.rsplit(":", 1)
        peers.append((host, int(port)))
    return peers

def load_peers_file(path):
    peers = []
    if not os.path.exists(path):
        return peers
    with open(path, "r") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            host, port = ln.rsplit(":", 1)
            peers.append((host.strip(), int(port.strip())))
    return peers

#main
def main():
    ap = argparse.ArgumentParser(description="UDP P2P Peer")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5001)
    ap.add_argument("--dir", default="./tmp")
    ap.add_argument("--peers", default="", help="comma-separated host:port")
    ap.add_argument("--peers-file", default="./ips.txt", help="path to peers file")
    ap.add_argument("--poll", type=int, default=2, help="watch interval seconds")
    args = ap.parse_args()

    peers = parse_peers(args.peers)
    if args.peers_file:
        peers += load_peers_file(args.peers_file)
        peers = list({f"{h}:{p}": (h, p) for (h, p) in peers}.values())

    t = threading.Thread(target=server_loop, args=(args.host, args.port, args.dir), daemon=True)
    t.start()

    watcher_loop(args.dir, peers, args.poll)

if __name__ == "__main__":
    main()