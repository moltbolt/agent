import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/calc_ev.py"
CURRENT = "rake-4-floor50-reject25-v1"
spec = importlib.util.spec_from_file_location("ev", HELPER)
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
                rake = max(50, (pay * 4 + 99) // 100)
                penalty = max(1, (pay * 7 + 99) // 100)
                self.assertEqual(got["rake_sats"], rake)
                self.assertEqual(got["fulfiller_payout_gross_sats"], max(0, pay - rake))
                self.assertEqual(got["reject_penalty_sats"], penalty)
                self.assertEqual(got["fulfiller_rejection_share_sats"], penalty // 4)
                self.assertEqual(got["entry_sats"], max(500, (penalty + 1) // 2))

    def test_floor_and_first_rounded_sat(self):
        for pay, rake in ((1249, 50), (1250, 50), (1251, 51), (2000, 80)):
            with self.subTest(pay=pay):
                self.assertEqual(ev.fees(pay)["rake_sats"], rake)

    def run_fees(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(HELPER), "fees", *args],
            capture_output=True, text=True, check=False,
        )

    def test_cli_rejects_bad_amount_and_policy_option(self):
        for args in ((), ("--pay-sats", "0"),
                     ("--pay-sats", "2000", "--fee-policy", "any")):
            with self.subTest(args=args):
                result = self.run_fees(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_cli_reports_new_gig_scope(self):
        result = self.run_fees("--pay-sats", "2000")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["fee_policy"], CURRENT)
        self.assertEqual(value["scope"], "new-gig-estimate")
        self.assertEqual(value["rake_sats"], 80)
        self.assertEqual(value["fulfiller_rejection_share_sats"], 35)
        self.assertEqual(value["fulfiller_payout_gross_sats"], 1920)
        help_result = self.run_fees("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("For existing Gigs,", help_result.stdout)
        self.assertIn("use Dock amounts.", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
