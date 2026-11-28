"""Exercise the local Markdown's concrete script interface, not editorial wording."""
import ast
import hashlib
import json
import operator
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FENCES = re.compile(r"^```(\w+)\n(.*?)^```", re.M | re.S)


def arithmetic(expression, values):
    """Only names, numbers and arithmetic from documentation; never eval Markdown."""
    operations = {ast.Add: operator.add, ast.Sub: operator.sub,
                  ast.Mult: operator.mul, ast.Div: operator.truediv}
    def visit(node):
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](visit(node.left), visit(node.right))
        raise AssertionError(f"Unsupported documented arithmetic: {ast.dump(node)}")
    normalized = re.sub(r"\s+", " ", expression.replace("×", "*")).strip()
    return visit(ast.parse(normalized, mode="eval").body)


class DocumentedScripts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        shutil.copytree(ROOT / "scripts", self.cwd / "scripts")
        self.readme = (ROOT / "scripts/README.md").read_text()
        self.models = (ROOT / "ev_models.md").read_text()
        fixtures = {
            "body.json": dict(title="Synthetic report", requirements_text="Deliverable: report",
                              pay_sats=1000, claim_window_s=3600,
                              delivery_window_s=3600, decision_window_s=3600),
            "claim.json": {},
            "deliver.json": {"deliverable_b64": "c3ludGhldGlj"},
            "withdraw.json": {"payable_id": "00000000-0000-0000-0000-000000000001",
                              "invoice_bolt11": "lnbc1syntheticonly"},
            "previous_board.json": {"items": [{"gig_id": "old", "pay_sats": 1000}]},
            "current_board.json": {"items": [{"gig_id": "new", "pay_sats": 2000}]},
        }
        for name, body in fixtures.items():
            (self.cwd / name).write_text(json.dumps(body))
        (self.cwd / "qa.log").write_text("Authorization: L402 synthetic-token:synthetic-preimage\nstatus: okay\n")

    def run_command(self, command):
        args = shlex.split(command)
        self.assertIn(args[0], ("python", "python3"))
        self.assertRegex(args[1], r"^scripts/[a-z_]+\.py$")
        output = None
        if ">" in args:
            index = args.index(">")
            self.assertEqual(index, len(args) - 2)
            output = self.cwd / args[-1]
            self.assertEqual(output.parent, self.cwd)
            args = args[:index]
        result = subprocess.run([sys.executable, "-B", *args[1:]], cwd=self.cwd,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, f"{command}\n{result.stderr}\n{result.stdout}")
        if output:
            output.write_text(result.stdout)
        return args, result.stdout

    def cli(self, mode, arguments):
        args = " ".join(f"--{key} {value}" for key, value in arguments.items())
        return json.loads(self.run_command(f"python scripts/calc_ev.py {mode} {args}")[1])

    def equation(self, name):
        blocks = [body for lang, body in FENCES.findall(self.models)
                  if lang == "text" and re.search(r"^" + name + r"\s*=", body, re.M)]
        self.assertEqual(len(blocks), 1, f"Document one equation for {name}")
        return re.search(r"^" + name + r"\s*=\s*(.*?)(?=^\w+\s*=|\Z)",
                         blocks[0], re.M | re.S)[1].strip()

    def equation_terms(self, expression):
        normalized = re.sub(r"\s+", " ", expression.replace("×", "*")).strip()
        return {node.id for node in ast.walk(ast.parse(normalized, mode="eval"))
                if isinstance(node, ast.Name)}

    def test_all_documented_shell_examples(self):
        covered = set()
        example_count = 0
        for path in sorted(ROOT.rglob("*.md")):
            fences = list(FENCES.finditer(path.read_text()))
            for index, block in enumerate(fences):
                if block[1] not in ("bash", "sh"):
                    continue
                commands = block[2].replace("\\\n", " ").splitlines()
                results = []
                for command in commands:
                    if not re.match(r"^python[3]? scripts/", command.strip()):
                        continue
                    with self.subTest(document=str(path.relative_to(ROOT)), command=command):
                        args, output = self.run_command(command)
                        covered.add(args[1])
                        example_count += 1
                        results.append(output)
                        if args[1].endswith("validate_request_shape.py"):
                            data = json.loads(output)
                            self.assertTrue(data["ok"])
                            raw = (self.cwd / args[-1]).read_bytes()
                            self.assertEqual(data["body_sha256_hex"], hashlib.sha256(raw).hexdigest())
                        elif args[1].endswith("board_delta.py"):
                            data = json.loads(output)
                            self.assertEqual(data["new_gigs"], ["new"])
                            self.assertEqual(data["removed_gigs"], ["old"])
                        elif args[1].endswith("redact_moltbolt_log.py"):
                            self.assertNotIn("synthetic-token", output)
                            self.assertNotIn("synthetic-preimage", output)
                            self.assertIn("status: okay", output)
                            self.assertEqual((self.cwd / "qa.redacted.log").read_text(), output)
                if results and index + 1 < len(fences) and fences[index + 1][1] == "json":
                    # Paired examples guard all documented output keys and values.
                    self.assertEqual(len(results), 1)
                    self.assertEqual(json.loads(results[0]), json.loads(fences[index + 1][2]))
        self.assertGreaterEqual(example_count, 9)
        self.assertEqual(covered, {"scripts/calc_ev.py", "scripts/validate_request_shape.py",
                                   "scripts/board_delta.py", "scripts/redact_moltbolt_log.py"})

    def test_documented_calculator_flags_exist(self):
        # Equation tests separately validate flags in their actual modes.
        known_flags = set()
        for mode in ("buyer", "fulfiller", "fees"):
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/calc_ev.py"), mode, "--help"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            known_flags.update(re.findall(r"--[a-z][a-z-]*", result.stdout))
        for document in (ROOT / "ev_models.md", ROOT / "scripts/README.md"):
            for flag in set(re.findall(r"`(--[a-z][a-z-]*)`", document.read_text())):
                with self.subTest(document=document.name, flag=flag):
                    self.assertIn(flag, known_flags, f"Unknown documented CLI flag: {flag}")

    def test_documented_output_field_names(self):
        for section, command in (
            ("validate_request_shape.py", "python scripts/validate_request_shape.py claim claim.json"),
            ("board_delta.py", "python scripts/board_delta.py current_board.json --previous previous_board.json"),
        ):
            text = self.readme.split(f"## [{section}]", 1)[1].split("\n## ", 1)[0]
            line = next(line for line in text.splitlines() if line.startswith("JSON output includes "))
            names = re.findall(r"`([a-z_]+)`", line)
            self.assertTrue(names)
            data = json.loads(self.run_command(command)[1])
            self.assertTrue(set(names) <= data.keys(), f"Unknown output fields: {set(names) - data.keys()}")

    def test_equation_terms_match_cli_arguments_exactly(self):
        for mode, names in (("buyer", ("buy_cost", "local_cost")),
                            ("fulfiller", ("expected_margin",))):
            terms = set().union(*(self.equation_terms(self.equation(name)) for name in names))
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/calc_ev.py"), mode, "--help"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            flags = set(re.findall(r"--[a-z][a-z-]*", result.stdout)) - {"--help"}
            self.assertEqual(flags, {"--" + term.replace("_", "-") for term in terms})

    def test_buyer_equation_and_decision_boundary(self):
        buy_expression = self.equation("buy_cost")
        local_expression = self.equation("local_cost")
        self.assertIn("decision = buy if buy_cost < local_cost else execute_locally", self.models)
        values = dict(gig_cost=100, specification_cost=11, verification_cost=13,
                      buy_opportunity_cost=17, expected_wait_cost=19,
                      delay_risk_cost=23, quality_risk_cost=29, local_latency_cost=7,
                      local_failure_risk_cost=11, local_opportunity_cost=13)
        for local_total in (211, 212, 213):
            with self.subTest(local_total=local_total):
                values["local_execution_cost"] = local_total - 31
                result = self.cli("buyer", {key.replace("_", "-"): value for key, value in values.items()})
                self.assertEqual(arithmetic(buy_expression, values), 212)
                self.assertEqual(arithmetic(local_expression, values), local_total)
                self.assertEqual(result["buy_cost"], 212)
                self.assertEqual(result["local_cost"], local_total)
                self.assertEqual(result["delta_sats"], local_total - 212)
                self.assertEqual(result["decision"], "buy" if local_total > 212 else "execute_locally")

    def test_fulfiller_equation_and_decision_boundary(self):
        margin_expression = self.equation("expected_margin")
        values = dict(probability_of_accepted_payout=0.5, accepted_invoice_sats=1000,
                      success_only_cost_sats=40, per_attempt_cost_sats=540)
        for rejection_receipts in (59, 60, 61):
            with self.subTest(rejection_receipts=rejection_receipts):
                values["expected_rejection_receipts_sats"] = rejection_receipts
                result = self.cli("fulfiller", {key.replace("_", "-"): value for key, value in values.items()})
                self.assertEqual(result["expected_payout"], 480 + rejection_receipts)
                self.assertEqual(result["expected_costs"], 540)
                self.assertEqual(result["expected_margin"], rejection_receipts - 60)
                self.assertEqual(result["expected_margin"], arithmetic(margin_expression, values))
                self.assertEqual(result["decision"], "claim" if rejection_receipts > 60 else "pass")

    def test_fractional_estimates_and_probability_endpoints(self):
        values = {name: 0 for name in self.equation_terms(self.equation("buy_cost"))
                  | self.equation_terms(self.equation("local_cost"))}
        values.update(specification_cost=0.25, local_execution_cost=0.5)
        result = self.cli("buyer", {key.replace("_", "-"): value for key, value in values.items()})
        self.assertEqual(result["buy_cost"], 0.25)
        self.assertEqual(result["delta_sats"], 0.25)
        for probability in (0, 0.25, 1):
            values = dict(probability_of_accepted_payout=probability, accepted_invoice_sats=10,
                          success_only_cost_sats=1, expected_rejection_receipts_sats=0.5,
                          per_attempt_cost_sats=2)
            result = self.cli("fulfiller", {key.replace("_", "-"): value for key, value in values.items()})
            self.assertEqual(result["expected_margin"], arithmetic(self.equation("expected_margin"), values))

    def test_invalid_estimates_and_probabilities(self):
        for mode, equations in (("buyer", ("buy_cost", "local_cost")),
                                ("fulfiller", ("expected_margin",))):
            terms = set().union(*(self.equation_terms(self.equation(name)) for name in equations))
            for term in sorted(terms):
                for invalid in ("-1", "nan", "inf", "not-a-number"):
                    with self.subTest(mode=mode, term=term, invalid=invalid):
                        args = [sys.executable, "-B", str(ROOT / "scripts/calc_ev.py"), mode]
                        for name in sorted(terms):
                            args.append(f"--{name.replace('_', '-')}={invalid if name == term else 0}")
                        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(result.stdout, "")
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/calc_ev.py"), "fulfiller",
             "--probability-of-accepted-payout=1.01", "--accepted-invoice-sats=0",
             "--success-only-cost-sats=0", "--expected-rejection-receipts-sats=0", "--per-attempt-cost-sats=0"],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be in [0, 1]", result.stderr)

    def test_decimal_ties_do_not_create_a_false_advantage(self):
        terms = self.equation_terms(self.equation("buy_cost")) | self.equation_terms(self.equation("local_cost"))
        values = {name.replace("_", "-"): 0 for name in terms}
        values.update({"gig-cost": "0.3", "local-execution-cost": "0.1", "local-latency-cost": "0.2"})
        result = self.cli("buyer", values)
        self.assertEqual(result["delta_sats"], 0)
        self.assertEqual(result["decision"], "execute_locally")
        result = self.cli("fulfiller", {
            "probability-of-accepted-payout": "0.1", "accepted-invoice-sats": 3,
            "success-only-cost-sats": 0, "expected-rejection-receipts-sats": 0,
            "per-attempt-cost-sats": "0.3",
        })
        self.assertEqual(result["expected_margin"], 0)
        self.assertEqual(result["decision"], "pass")

    def test_documented_fee_command_and_formula_output_names(self):
        self.assertIn("python scripts/calc_ev.py fees --pay-sats 2000", self.readme)
        data = self.cli("fees", {"pay-sats": 2000})
        fee_block = next(body for lang, body in FENCES.findall(self.models)
                         if lang == "text" and "rake_sats =" in body)
        names = re.findall(r"^([a-z_]+)\s*=", fee_block, re.M)
        self.assertTrue(names)
        self.assertTrue(set(names) <= data.keys())
        self.assertEqual(data["fulfiller_rejection_share_sats"], 35)


if __name__ == "__main__":
    unittest.main()
