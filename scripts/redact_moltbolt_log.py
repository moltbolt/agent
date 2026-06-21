#!/usr/bin/env python3
"""Redact MoltBolt-sensitive data from logs.

Stdlib only. Reads files or stdin; writes redacted text to stdout.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERNS = [
    (re.compile(r"(?i)\b(lnbc|lntb|lnbcrt)[a-z0-9]{40,}\b"), "[REDACTED_BOLT11]"),
    (re.compile(r"(?im)^(\s*Authorization\s*:\s*L402\s+).+$"), r"\1[REDACTED_L402]"),
    (re.compile(r"(?im)^(\s*X-Molt-Sig\s*:\s*).+$"), r"\1[REDACTED_SIGNATURE]"),
    (re.compile(r"(?im)^(\s*X-Molt-Pubky\s*:\s*).+$"), r"\1[REDACTED_PUBKY]"),
    (re.compile(r"(?im)^(\s*X-Molt-Nonce\s*:\s*).+$"), r"\1[REDACTED_NONCE]"),
    (re.compile(r"(?im)^(\s*X-Molt-Ts\s*:\s*).+$"), r"\1[REDACTED_TS]"),
    (re.compile(r"(?i)(macaroon\s*[:=]\s*)[A-Za-z0-9+/=_-]+"), r"\1[REDACTED_MACAROON]"),
    (re.compile(r"(?i)(seed(?:_phrase)?\s*[:=]\s*)[^\n,}]+"), r"\1[REDACTED_SEED]"),
    (re.compile(r"(?i)(private[_ -]?key\s*[:=]\s*)[^\n,}]+"), r"\1[REDACTED_PRIVATE_KEY]"),
    (re.compile(r'(?i)("(?:token|preimage|payment_hash|r_hash|invoice_bolt11|sig|signature|macaroon)"\s*:\s*)"[^"]*"'), r'\1"[REDACTED]"'),
    (re.compile(r'(?i)("(?:pubky|buyer_pubky|fulfiller_pubky|auth_pubky)"\s*:\s*)"[0-9a-f]{32,128}"'), r'\1"[REDACTED_PUBKY]"'),
    (re.compile(r"(?i)\b(preimage|payment_hash|r_hash|token|sig|signature)=([A-Za-z0-9+/=_:-]{16,})"), r"\1=[REDACTED]"),
    (re.compile(r"\b[0-9a-fA-F]{64}\b"), "[REDACTED_64HEX]"),
]


def redact(text: str) -> str:
    out = text
    for pattern, repl in PATTERNS:
        out = pattern.sub(repl, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact MoltBolt-sensitive log text.")
    parser.add_argument("paths", nargs="*", help="Files to redact. Reads stdin when omitted.")
    args = parser.parse_args()

    if not args.paths:
        sys.stdout.write(redact(sys.stdin.read()))
        return 0

    chunks = []
    for raw_path in args.paths:
        path = Path(raw_path)
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            print(f"Cannot read {path}: {exc}", file=sys.stderr)
            return 2
    sys.stdout.write(redact("\n".join(chunks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
