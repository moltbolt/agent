import importlib.util
import json
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("redactor", ROOT / "scripts/redact_moltbolt_log.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
class SecretRedaction(unittest.TestCase):
    def test_json_sensitive_fields(self):
        for key in ("private_key", "privateKey", "seed", "seed_phrase", "Authorization", "X-Molt-Sig", "X-Molt-Nonce", "X-Molt-Pubky", "X-Molt-Ts", "token", "macaroon", "sig", "preimage", "invoice_bolt11"):
            with self.subTest(key=key):
                raw = json.dumps({key:'SYNTHETIC-ONLY \" quoted \n multi-line', 'status':'ok'})
                out = r.redact(raw)
                self.assertNotIn('SYNTHETIC', out)
                self.assertEqual(json.loads(out)['status'], 'ok')
    def test_all_plain_authorization_schemes(self):
        for header in ("Authorization", "Proxy-Authorization"):
            for scheme in ("Bearer", "Basic", "L402", "Custom"):
                out = r.redact(header + ": " + scheme + " synthetic-access-token\nstatus: okay")
                self.assertNotIn("synthetic-access-token", out)
                self.assertIn("status: okay", out)

    def test_wallet_connection_uri_entirely_removed(self):
        for scheme in ("nostr+walletconnect", "nostrwalletconnect"):
            uri = scheme + "://" + "a" * 64 + "?relay=wss%3A%2F%2Fexample.invalid%3Ftoken%3Dsynthetic-relay-token&secret=" + "b" * 64
            for text in (uri, json.dumps({"uri":uri, "status":"okay"})):
                out = r.redact(text)
                self.assertNotIn("synthetic-relay-token", out)
                self.assertNotIn("example.invalid", out)
                self.assertIn("REDACTED_NWC_URI", out)
            self.assertEqual(json.loads(r.redact(json.dumps({"uri":uri})))['uri'], "[REDACTED_NWC_URI]")

    def test_pem_private_blocks(self):
        for kind in ("PRIVATE KEY", "RSA PRIVATE KEY", "EC PRIVATE KEY", "OPENSSH PRIVATE KEY", "ENCRYPTED PRIVATE KEY"):
            with self.subTest(kind=kind):
                out = r.redact('prefix\n-----BEGIN '+kind+'-----\nSYNTHETIC_PRIVATE_CONTENT\n-----END '+kind+'-----\nsuffix')
                self.assertNotIn('SYNTHETIC', out)
                self.assertIn('prefix', out)
                self.assertIn('suffix', out)
    def test_existing_headers_and_diagnostics(self):
        self.assertNotIn('synthetic-token', r.redact('Authorization: L402 synthetic-token:synthetic-preimage'))
        self.assertEqual(r.redact('{"status":"failed","code":"CLAIM_PENDING","amount_sats":504}'), '{"status":"failed","code":"CLAIM_PENDING","amount_sats":504}')
if __name__ == "__main__": unittest.main()
