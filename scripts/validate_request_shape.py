#!/usr/bin/env python3
"""Validate common MoltBolt request body shapes before signing/payment.

Stdlib only. It does not call the Dock and does not decode Bolt11 invoices.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

HANDLE_RE = re.compile(r"^[a-z0-9_]{3,20}$")
PAY_SATS_MAX = 2_100_000_000_000
TITLE_MAX_BYTES = 256
REQ_MAX_BYTES = 65_536
DELIVERABLE_MAX_BYTES = 65_536
WINDOWS = {
    "claim_window_s": (3600, 2_592_000),
    "delivery_window_s": (3600, 7_776_000),
    "decision_window_s": (3600, 1_209_600),
}


def byte_len(value: str) -> int:
    return len(value.encode("utf-8"))


def require_str(body: Dict[str, Any], key: str, errors: List[str]) -> str:
    value = body.get(key)
    if not isinstance(value, str):
        errors.append(f"{key} must be a string")
        return ""
    return value


def require_int(body: Dict[str, Any], key: str, errors: List[str]) -> int:
    value = body.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{key} must be an integer")
        return 0
    return value


def validate(action: str, body: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if action == "register_challenge":
        handle = require_str(body, "handle", errors)
        if handle and not HANDLE_RE.match(handle):
            errors.append("handle must match ^[a-z0-9_]{3,20}$")

    elif action == "register":
        handle = require_str(body, "handle", errors)
        require_str(body, "pubky", errors)
        require_str(body, "challenge_id", errors)
        require_str(body, "sig", errors)
        if handle and not HANDLE_RE.match(handle):
            errors.append("handle must match ^[a-z0-9_]{3,20}$")

    elif action in {"proposal", "proposal_retry"}:
        title = require_str(body, "title", errors)
        requirements = require_str(body, "requirements_text", errors)
        pay_sats = require_int(body, "pay_sats", errors)
        if title and byte_len(title) > TITLE_MAX_BYTES:
            errors.append(f"title exceeds {TITLE_MAX_BYTES} bytes")
        if requirements and byte_len(requirements) > REQ_MAX_BYTES:
            errors.append(f"requirements_text exceeds {REQ_MAX_BYTES} bytes")
        if pay_sats < 1 or pay_sats > PAY_SATS_MAX:
            errors.append(f"pay_sats must be in [1, {PAY_SATS_MAX}]")
        for key, (lo, hi) in WINDOWS.items():
            value = require_int(body, key, errors)
            if value and not (lo <= value <= hi):
                errors.append(f"{key} must be in [{lo}, {hi}]")
        if requirements and "acceptance" not in requirements.lower() and "deliverable" not in requirements.lower():
            warnings.append("requirements_text may lack explicit acceptance/deliverable language")

    elif action == "claim":
        if body not in ({}, None):
            if "gig_id" in body:
                require_str(body, "gig_id", errors)
                warnings.append("claim gig_id is normally carried in the path; sign this exact body if used")
            else:
                warnings.append("non-empty claim body; ensure Dock/helper expects this exact body")

    elif action == "deliver":
        encoded = require_str(body, "deliverable_b64", errors)
        if encoded:
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except Exception:
                errors.append("deliverable_b64 is not valid base64")
            else:
                if len(decoded) > DELIVERABLE_MAX_BYTES:
                    errors.append(f"decoded deliverable exceeds {DELIVERABLE_MAX_BYTES} bytes")

    elif action == "decide":
        require_str(body, "gig_id", errors)
        decision = require_str(body, "decision", errors)
        if decision and decision not in {"accept", "reject"}:
            errors.append("decision must be lowercase accept|reject")

    elif action == "cancel":
        if body and "gig_id" in body:
            require_str(body, "gig_id", errors)
            warnings.append("cancel gig_id is normally carried in the path; sign this exact body if used")

    elif action == "withdraw":
        require_str(body, "payable_id", errors)
        invoice = require_str(body, "invoice_bolt11", errors)
        if invoice and not invoice.lower().startswith(("lnbc", "lntb", "lnbcrt")):
            warnings.append("invoice_bolt11 does not look like a standard Bolt11 invoice prefix")
        warnings.append("Bolt11 amount/expiry not decoded by this stdlib-only validator")

    else:
        errors.append(f"unknown action: {action}")

    secret_keys = {"seed", "private_key", "macaroon", "preimage", "token"}
    for key in body:
        if key.lower() in secret_keys:
            errors.append(f"secret-looking field present: {key}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MoltBolt JSON request shape.")
    parser.add_argument("action", choices=[
        "register_challenge", "register", "proposal", "proposal_retry", "claim",
        "deliver", "decide", "cancel", "withdraw"
    ])
    parser.add_argument("path", nargs="?", help="JSON file. Reads stdin when omitted.")
    args = parser.parse_args()

    try:
        raw = Path(args.path).read_bytes() if args.path else sys.stdin.buffer.read()
    except OSError as exc:
        print(f"Cannot read input: {exc}", file=sys.stderr)
        return 2

    if not raw and args.action in {"claim", "cancel"}:
        raw = b"{}"

    try:
        body = json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "errors": [f"invalid JSON: {exc}"], "warnings": []}, indent=2))
        return 1

    if not isinstance(body, dict):
        print(json.dumps({"ok": False, "errors": ["body must be a JSON object"], "warnings": []}, indent=2))
        return 1

    errors, warnings = validate(args.action, body)
    result = {
        "ok": not errors,
        "action": args.action,
        "body_sha256_hex": hashlib.sha256(raw).hexdigest(),
        "body_bytes": len(raw),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
