#!/usr/bin/env python3
"""Samsung Tizen TV helper: probe, pair, send remote keys, launch apps, guided privacy pass.

Standard library only. Talks to the TV's local APIs:
  - http://<tv>:8001/api/v2/                 device metadata (read-only)
  - http://<tv>:8001/api/v2/applications/<id> app status / launch
  - wss://<tv>:8002/api/v2/channels/samsung.remote.control   remote keys

This does NOT modify firmware, remove apps, or get a shell. Samsung retail
firmware exposes none of that (no ADB, no sdb without Developer Mode, no root).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CLIENT_NAME = "cleantizen"
STATE_DIR = Path(os.environ.get("CLEANTIZEN_HOME", Path.home() / ".cleantizen"))
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
KEY_RE = re.compile(r"^KEY_[A-Z0-9_]+$")

# Fields in /api/v2/ that identify the set, its owner or the home network.
REDACT_DEVICE = {"duid", "id", "ip", "developerIP", "name", "ssid", "udn", "wifiMac"}
REDACT_TOP = {"id", "name", "uri"}

PORTS = {
    8001: "HTTP API + remote websocket",
    8002: "remote websocket over TLS",
    5555: "ADB (expected closed on Tizen)",
    26101: "sdb (open only in Developer Mode)",
}

# Commonly reported app ids. Verify on your set with `app <id>`: 404 means not present.
KNOWN_APPS = {
    "netflix": "3201907018807",
    "youtube": "111299001912",
    "prime": "3201910019365",
    "disney": "3201901017640",
}

# Settings pass for a 2023 Samsung (S95C ships Tizen 7.0). Paths are the expected
# locations on 2023 firmware; Samsung moves these between years and regions, so
# every step says what to look for, not a key sequence to fire blind.
CHECKLIST = [
    {
        "title": "Record your current values first",
        "path": "Take a photo of each screen below before changing it",
        "action": "These photos are your undo. Nothing here has a factory 'restore' for privacy toggles.",
    },
    {
        "title": "Viewing Information Services (ACR) -> Off",
        "path": "Settings > All Settings > General & Privacy > Terms & Privacy",
        "action": "Turn off Viewing Information Services. This is the content-recognition that "
                  "fingerprints what is on screen, including HDMI inputs.",
    },
    {
        "title": "Interest-Based Advertisement -> Off",
        "path": "Settings > All Settings > General & Privacy > Terms & Privacy",
        "action": "Turn off Interest-Based Advertisement.",
    },
    {
        "title": "Reset the advertising ID (PSID)",
        "path": "Settings > All Settings > General & Privacy > Terms & Privacy",
        "action": "Use Reset PSID if offered, after turning ads off, so the old profile is orphaned.",
    },
    {
        "title": "Voice Recognition Services -> Off (if present)",
        "path": "Settings > All Settings > General & Privacy > Terms & Privacy",
        "action": "Turn off. Some regions/firmwares do not show this entry.",
    },
    {
        "title": "Voice Wake-up -> Off (if present)",
        "path": "Settings > All Settings > General & Privacy > Voice",
        "action": "Turn off always-listening wake word. Push-to-talk on the remote still works.",
    },
    {
        "title": "Start screen behaviour",
        "path": "Settings > All Settings > General & Privacy > Start Screen Option",
        "action": "Optional: 'Start with Smart Hub Home' off and 'Autorun Last App' on boots into your "
                  "last input/app instead of the ad-carrying home row. Also turn off any 'Autorun "
                  "Samsung TV Plus' toggle. The Home button will still open Samsung Home.",
    },
    {
        "title": "Leave Software Update on",
        "path": "Settings > Support > Software Update > Auto Update",
        "action": "Keep ON. Firmware updates carry security fixes and can reset the toggles above, "
                  "so re-run this pass after an update instead of freezing firmware.",
    },
    {
        "title": "Remove this tool's pairing when done",
        "path": "Settings > All Settings > Connection > External Device Manager > Device Connection Manager > Device List",
        "action": f"Delete '{CLIENT_NAME}' if you do not plan to use the remote again.",
    },
]

GUIDE_KEYS = {
    "u": "KEY_UP", "d": "KEY_DOWN", "l": "KEY_LEFT", "r": "KEY_RIGHT",
    "ok": "KEY_ENTER", "back": "KEY_RETURN", "home": "KEY_HOME",
    "menu": "KEY_MENU", "exit": "KEY_EXIT",
}


# ---------------------------------------------------------------- helpers

def require_lan_ip(host: str) -> str:
    """Only talk to private addresses: TLS verification is off for the TV's self-signed cert."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        raise SystemExit(f"error: give the TV's IP address, not a hostname ({host!r})")
    lan = (ip.is_private or ip.is_link_local) and not ip.is_loopback
    if not lan:
        raise SystemExit(f"error: {host} is not a private LAN address; refusing")
    return host


def redact(info: dict) -> dict:
    out = {k: v for k, v in info.items() if k not in REDACT_TOP}
    dev = info.get("device")
    if isinstance(dev, dict):
        out["device"] = {k: ("<redacted>" if k in REDACT_DEVICE else v) for k, v in dev.items()}
    return out


def http(method: str, url: str, timeout: float = 5.0) -> tuple[int, str]:
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def token_path() -> Path:
    return STATE_DIR / "tokens.json"


def load_token(host: str) -> str | None:
    try:
        return json.loads(token_path().read_text()).get(host)
    except (OSError, ValueError):
        return None


def save_token(host: str, token: str) -> None:
    STATE_DIR.mkdir(mode=0o700, exist_ok=True)
    p = token_path()
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        data = {}
    data[host] = token
    p.write_text(json.dumps(data, indent=2))
    p.chmod(0o600)


def key_message(key: str) -> str:
    if not KEY_RE.match(key):
        raise ValueError(f"not a Samsung key code: {key!r} (expected e.g. KEY_HOME)")
    return json.dumps({
        "method": "ms.remote.control",
        "params": {"Cmd": "Click", "DataOfCmd": key, "Option": "false",
                   "TypeOfRemote": "SendRemoteKey"},
    })


# ---------------------------------------------------------------- websocket (RFC 6455 client)

def encode_frame(payload: bytes, opcode: int = 0x1, mask: bytes | None = None) -> bytes:
    mask = mask if mask is not None else os.urandom(4)
    head = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        head += bytes([0x80 | n])
    elif n < 1 << 16:
        head += bytes([0x80 | 126]) + struct.pack("!H", n)
    else:
        head += bytes([0x80 | 127]) + struct.pack("!Q", n)
    return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


def decode_frame(read) -> tuple[int, bytes]:
    """`read(n)` must return exactly n bytes. Returns (opcode, payload)."""
    b0, b1 = read(2)
    opcode, masked, n = b0 & 0x0F, b1 & 0x80, b1 & 0x7F
    if n == 126:
        n = struct.unpack("!H", read(2))[0]
    elif n == 127:
        n = struct.unpack("!Q", read(8))[0]
    mask = read(4) if masked else None
    data = read(n)
    if mask:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return opcode, data


def accept_key(key: str) -> str:
    return base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()


class Remote:
    def __init__(self, host: str, token: str | None, timeout: float = 10.0):
        self.host = require_lan_ip(host)
        name = base64.b64encode(CLIENT_NAME.encode()).decode()
        path = f"/api/v2/channels/samsung.remote.control?name={name}"
        if token:
            path += f"&token={token}"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # TV uses a self-signed cert; LAN-only enforced above
        raw = socket.create_connection((host, 8002), timeout=timeout)
        self.sock = ctx.wrap_socket(raw, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            f"GET {path} HTTP/1.1\r\nHost: {host}:8002\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(1)
            if not chunk:
                raise ConnectionError("TV closed the connection during handshake")
            head += chunk
        lines = head.decode("latin-1").split("\r\n")
        if " 101 " not in lines[0] + " ":
            raise ConnectionError(f"websocket upgrade refused: {lines[0]}")
        hdrs = {l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip()
                for l in lines[1:] if ":" in l}
        if hdrs.get("sec-websocket-accept") != accept_key(key):
            raise ConnectionError("bad Sec-WebSocket-Accept from TV")

    def _read(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("TV closed the connection")
            buf += chunk
        return buf

    def recv_json(self) -> dict:
        while True:
            op, data = decode_frame(self._read)
            if op == 0x9:
                self.sock.sendall(encode_frame(data, 0xA))
            elif op == 0x8:
                raise ConnectionError("TV closed the websocket")
            elif op == 0x1:
                return json.loads(data)

    def wait_connected(self) -> dict:
        """Block until the TV accepts (prompt answered) or refuses."""
        while True:
            msg = self.recv_json()
            ev = msg.get("event")
            if ev == "ms.channel.connect":
                return msg
            if ev in ("ms.channel.unauthorized", "ms.channel.timeOut"):
                raise PermissionError(f"TV refused the connection ({ev})")

    def send_key(self, key: str) -> None:
        self.sock.sendall(encode_frame(key_message(key).encode()))

    def close(self) -> None:
        try:
            self.sock.sendall(encode_frame(b"", 0x8))
        finally:
            self.sock.close()


def open_remote(host: str) -> Remote:
    token = load_token(host)
    if not token:
        raise SystemExit("not paired yet: run `tizen.py pair <tv-ip>` first")
    r = Remote(host, token)
    r.wait_connected()
    return r


# ---------------------------------------------------------------- commands

def cmd_probe(a) -> None:
    host = require_lan_ip(a.host)
    for port, what in PORTS.items():
        print(f"{port:>6}  {'open  ' if port_open(host, port) else 'closed'}  {what}")
    status, body = http("GET", f"http://{host}:8001/api/v2/")
    if status != 200:
        raise SystemExit(f"/api/v2/ answered {status}")
    info = json.loads(body)
    print(json.dumps(info if a.raw else redact(info), indent=2))
    if not a.raw:
        print("# identifiers redacted; use --raw only for your own eyes", file=sys.stderr)


def cmd_pair(a) -> None:
    print("Connecting... accept the 'Allow' prompt on the TV within 30 s.")
    r = Remote(a.host, None, timeout=30)
    try:
        msg = r.wait_connected()
    finally:
        r.close()
    token = (msg.get("data") or {}).get("token")
    if not token:
        raise SystemExit("connected but the TV issued no token; this firmware may not support pairing")
    save_token(a.host, token)
    print(f"paired; token saved to {token_path()}")


def cmd_key(a) -> None:
    r = open_remote(a.host)
    try:
        for i, k in enumerate(a.keys):
            if i:
                time.sleep(0.4)  # back-to-back presses get dropped by some sets
            r.send_key(k if k.startswith("KEY_") else "KEY_" + k.upper())
    finally:
        r.close()


def cmd_app(a) -> None:
    host = require_lan_ip(a.host)
    app_id = KNOWN_APPS.get(a.app.lower(), a.app)
    url = f"http://{host}:8001/api/v2/applications/{app_id}"
    status, body = http("POST" if a.launch else "GET", url)
    print(status, body.strip() or "")
    if status == 404:
        sys.exit(1)


def checklist_markdown() -> str:
    out = ["# Samsung S95C privacy pass (2023, Tizen 7)", ""]
    for i, s in enumerate(CHECKLIST, 1):
        out += [f"{i}. **{s['title']}**", f"   - Where: {s['path']}", f"   - Do: {s['action']}"]
    return "\n".join(out)


def cmd_checklist(a) -> None:
    print(checklist_markdown())


def cmd_guide(a) -> None:
    """Walk the checklist with a person watching the screen. No key is ever sent blind."""
    r = open_remote(a.host)
    keys = " ".join(GUIDE_KEYS)
    i = 0
    try:
        while True:
            s = CHECKLIST[i]
            print(f"\n[{i + 1}/{len(CHECKLIST)}] {s['title']}\n  where: {s['path']}\n  do:    {s['action']}")
            while True:
                cmd = input(f"  keys ({keys}) | n next | p prev | q quit > ").strip().lower()
                if cmd in GUIDE_KEYS:
                    r.send_key(GUIDE_KEYS[cmd])
                elif cmd in ("n", "p", "q"):
                    break
                elif cmd:
                    print("  ?")
            if cmd == "q":
                return
            i = min(i + 1, len(CHECKLIST) - 1) if cmd == "n" else max(i - 1, 0)
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        r.close()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("probe", help="read-only: open ports and /api/v2/ metadata (redacted)")
    s.add_argument("host"); s.add_argument("--raw", action="store_true")
    s.set_defaults(fn=cmd_probe)

    s = sub.add_parser("pair", help="pair with the TV (accept the prompt on screen)")
    s.add_argument("host"); s.set_defaults(fn=cmd_pair)

    s = sub.add_parser("key", help="send remote keys, e.g. HOME or KEY_VOLUP")
    s.add_argument("host"); s.add_argument("keys", nargs="+"); s.set_defaults(fn=cmd_key)

    s = sub.add_parser("app", help=f"app status by id or alias ({', '.join(KNOWN_APPS)})")
    s.add_argument("host"); s.add_argument("app"); s.add_argument("--launch", action="store_true")
    s.set_defaults(fn=cmd_app)

    s = sub.add_parser("checklist", help="print the settings pass as markdown")
    s.set_defaults(fn=cmd_checklist)

    s = sub.add_parser("guide", help="interactive settings pass, you drive with keys while watching the TV")
    s.add_argument("host"); s.set_defaults(fn=cmd_guide)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
