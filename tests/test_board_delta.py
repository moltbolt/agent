import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("board", ROOT / "scripts/board_delta.py")
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)
class BoardInput(unittest.TestCase):
    def load(self, body):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "board.json"
            p.write_text(json.dumps(body))
            return board.load_items(str(p))
    def test_error_is_not_empty_board(self):
        for body in ({}, {"code":"BOARD_NOT_CONFIGURED"}, {"code":"RATE_LIMITED"}, {"items":None}, {"items":{}}):
            with self.subTest(body=body), self.assertRaises(SystemExit): self.load(body)
    def test_cli_error_stops_without_delta(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "error.json"
            p.write_text('{"code":"BOARD_NOT_CONFIGURED"}')
            r = subprocess.run([sys.executable, str(ROOT / "scripts/board_delta.py"), str(p)], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(r.stdout, b"")
            self.assertIn(b"Expected items array", r.stderr)
    def test_valid_empty_and_cards(self):
        self.assertEqual(self.load({"items":[], "next_cursor":None}), [])
        cards = [{"gig_id":"example", "pay_sats":1000}]
        self.assertEqual(self.load({"items":cards, "next_cursor":"page2"}), cards)
        self.assertEqual(self.load(cards), cards)
    def test_malformed_cards_not_silently_dropped(self):
        for cards in ([None], [{}], [{"gig_id":""}], [{"gig_id":"a"},{"gig_id":"a"}]):
            with self.subTest(cards=cards), self.assertRaises(SystemExit): self.load({"items":cards})
if __name__ == "__main__": unittest.main()
