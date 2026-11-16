import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ev", ROOT / "scripts/calc_ev.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
class ExactFees(unittest.TestCase):
    def test_known_float_overrounding(self):
        self.assertEqual(ev.fees(100)["reject_penalty_sats"], 7)
        actual = ev.fees(14400)
        self.assertEqual(actual["reject_penalty_sats"], 1008)
        self.assertEqual(actual["entry_sats"], 504)
        self.assertEqual(actual["buyer_return_on_reject_gross_sats"], 13392)
    def test_domain_integer_ratio_agreement(self):
        # Dock src/domain/fees.ts uses ceilRatio, not float percentage products.
        for pay in list(range(1, 20001)) + [2100000000000]:
            with self.subTest(pay=pay):
                got = ev.fees(pay)
                rake = max(50, (pay * 5 + 99) // 100)
                penalty = max(1, (pay * 7 + 99) // 100)
                self.assertEqual(got["rake_sats"], rake)
                self.assertEqual(got["reject_penalty_sats"], penalty)
                self.assertEqual(got["entry_sats"], max(500, (penalty + 1) // 2))
if __name__ == "__main__": unittest.main()
