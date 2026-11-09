import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tizen  # noqa: E402


class WebSocketFrames(unittest.TestCase):
    def roundtrip(self, payload: bytes):
        frame = tizen.encode_frame(payload)
        buf = io.BytesIO(frame)
        op, data = tizen.decode_frame(buf.read)
        self.assertEqual(op, 0x1)
        self.assertEqual(data, payload)
        self.assertEqual(buf.read(), b"")

    def test_small_medium_large(self):
        for n in (0, 5, 125, 126, 300, 70000):
            self.roundtrip(bytes(range(256)) * (n // 256) + bytes(range(n % 256)))

    def test_client_frames_are_masked(self):
        self.assertTrue(tizen.encode_frame(b"x")[1] & 0x80)

    def test_unmasked_server_frame(self):
        op, data = tizen.decode_frame(io.BytesIO(b"\x81\x02hi").read)
        self.assertEqual((op, data), (1, b"hi"))

    def test_accept_key_rfc6455_example(self):
        self.assertEqual(tizen.accept_key("dGhlIHNhbXBsZSBub25jZQ=="), "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")


class Safety(unittest.TestCase):
    def test_lan_only(self):
        for ok in ("192.168.1.20", "10.0.0.5", "172.16.3.4", "169.254.1.1"):
            self.assertEqual(tizen.require_lan_ip(ok), ok)
        for bad in ("8.8.8.8", "127.0.0.1", "tv.local"):
            with self.assertRaises(SystemExit):
                tizen.require_lan_ip(bad)

    def test_key_message(self):
        msg = json.loads(tizen.key_message("KEY_HOME"))
        self.assertEqual(msg["params"]["DataOfCmd"], "KEY_HOME")
        for bad in ("HOME", "KEY_home", 'KEY_X"}', ""):
            with self.assertRaises(ValueError):
                tizen.key_message(bad)

    def test_guide_keys_are_valid(self):
        for k in tizen.GUIDE_KEYS.values():
            tizen.key_message(k)

    def test_redact(self):
        info = {"id": "uuid", "name": "Living room", "uri": "http://192.168.1.2:8001/api/v2/",
                "version": "2.0.25",
                "device": {"duid": "uuid:x", "wifiMac": "aa:bb", "ssid": "cc:dd", "ip": "192.168.1.2",
                           "name": "Living room", "udn": "uuid:y", "id": "uuid", "developerIP": "0.0.0.0",
                           "modelName": "QN55S95C", "developerMode": "0"}}
        out = tizen.redact(info)
        blob = json.dumps(out)
        for secret in ("uuid", "aa:bb", "cc:dd", "192.168.1.2", "Living room"):
            self.assertNotIn(secret, blob)
        self.assertEqual(out["device"]["modelName"], "QN55S95C")
        self.assertEqual(out["version"], "2.0.25")

    def test_token_file_private(self):
        with tempfile.TemporaryDirectory() as d:
            old = tizen.STATE_DIR
            tizen.STATE_DIR = Path(d) / "state"
            try:
                tizen.save_token("192.168.1.2", "abc")
                self.assertEqual(tizen.load_token("192.168.1.2"), "abc")
                self.assertEqual(tizen.token_path().stat().st_mode & 0o777, 0o600)
            finally:
                tizen.STATE_DIR = old


class Content(unittest.TestCase):
    def test_blocklist_format(self):
        rules = [l for l in (ROOT / "dns" / "samsung-ads.txt").read_text().splitlines()
                 if l.strip() and not l.startswith("!")]
        self.assertTrue(rules)
        for r in rules:
            self.assertRegex(r, r"^\|\|[a-z0-9.-]+\.[a-z]{2,}\^$")
        self.assertEqual(len(rules), len(set(rules)))

    def test_checklist_markdown(self):
        md = tizen.checklist_markdown()
        self.assertEqual(len(re.findall(r"^\d+\. \*\*", md, re.M)), len(tizen.CHECKLIST))
        self.assertIn("Viewing Information Services", md)

    def test_settings_doc_in_sync(self):
        doc = (ROOT / "docs" / "s95c-settings.md").read_text()
        self.assertIn(tizen.checklist_markdown(), doc)


if __name__ == "__main__":
    unittest.main()
