import importlib.util
from pathlib import Path
import unittest
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts/validate_request_shape.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

class ProposalWindows(unittest.TestCase):
    def body(self):
        return dict(title='Alpha report', requirements_text='Deliverable: a short report', pay_sats=1000,
                    claim_window_s=3600, delivery_window_s=3600, decision_window_s=3600)
    def test_net_payout_is_explicitly_not_validated(self):
        for action in ('proposal', 'proposal_retry'):
            for amount in (1, 50, 100, 101, 1000, 100000):
                with self.subTest(action=action, amount=amount):
                    body=self.body(); body['pay_sats']=amount
                    errors,warnings=validator.validate(action, body)
                    self.assertEqual(errors, [])
                    self.assertTrue(any('does not verify net payout eligibility' in w for w in warnings))

    def test_valid_lower_bound(self):
        self.assertEqual(validator.validate('proposal', self.body())[0], [])
    def test_boundaries_each_window(self):
        for action in ('proposal', 'proposal_retry'):
            for field, (low, high) in validator.WINDOWS.items():
                for value, valid in ((0, False), (-1, False), (low-1, False), (low, True), (high, True), (high+1, False)):
                    with self.subTest(action=action, field=field, value=value):
                        body=self.body(); body[field]=value
                        self.assertEqual(not validator.validate(action, body)[0], valid)
    def test_type_and_presence(self):
        for field in validator.WINDOWS:
            for value in (None, True, '3600', 3600.5):
                with self.subTest(field=field, value=value):
                    body=self.body(); body[field]=value
                    self.assertTrue(validator.validate('proposal', body)[0])
            body=self.body(); del body[field]
            self.assertTrue(validator.validate('proposal', body)[0])

class ExactWireBody(unittest.TestCase):
    def test_claim_cancel_hash_exact_stdin(self):
        for action in ('claim', 'cancel'):
            for raw in (b'', b'{}', b'{ }\n'):
                with self.subTest(action=action, raw=raw):
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_request_shape.py'), action], input=raw, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    body = json.loads(result.stdout)
                    self.assertEqual(body['body_bytes'], len(raw))
                    self.assertEqual(body['body_sha256_hex'], hashlib.sha256(raw).hexdigest())

class ProposalAdmissionShape(unittest.TestCase):
    def body(self):
        return dict(title='Alpha report', requirements_text='Deliverable: x', pay_sats=2000,
                    claim_window_s=3600, delivery_window_s=3600, decision_window_s=3600)
    def test_empty_or_whitespace_title_refused(self):
        for action in ('proposal','proposal_retry'):
            for title in ('', '   ', '\t\r\n', '\u00a0', '\ufeff', ' \ufeff\t'):
                b=self.body(); b['title']=title
                self.assertTrue(validator.validate(action,b)[0])
    def test_caller_identity_refused_even_null(self):
        for action in ('proposal','proposal_retry'):
            for value in ('synthetic', None, ''):
                b=self.body(); b['buyer_pubky']=value
                self.assertTrue(validator.validate(action,b)[0])
    def test_valid_title_not_rewritten_before_signing(self):
        b=self.body(); b['title']='  Alpha report  '
        raw=json.dumps(b,indent=2).encode()+b'\n'
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_request_shape.py'),'proposal'],input=raw,capture_output=True)
        self.assertEqual(r.returncode,0)
        self.assertEqual(json.loads(r.stdout)['body_sha256_hex'],hashlib.sha256(raw).hexdigest())
    def test_empty_requirements_remains_shape_valid(self):
        b=self.body(); b['requirements_text']=''
        self.assertEqual(validator.validate('proposal',b)[0],[])

if __name__ == '__main__':
    unittest.main()
