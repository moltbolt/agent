#!/usr/bin/env python3
"""MoltBolt EV helper.

Stdlib only. No network. No wallet access.
"""
from __future__ import annotations

import argparse
import json
from math import ceil
from typing import Dict, Any


def nonnegative(name: str, value: int) -> int:
    if value < 0:
        raise argparse.ArgumentTypeError(f"{name} must be nonnegative")
    return value


def fees(pay_sats: int) -> Dict[str, int]:
    if pay_sats < 1:
        raise ValueError("pay_sats must be >= 1")
    rake_sats = max(50, ceil(0.05 * pay_sats))
    reject_penalty_sats = max(1, ceil(0.07 * pay_sats))
    entry_sats = max(500, ceil(0.5 * reject_penalty_sats))
    return {
        "pay_sats": pay_sats,
        "rake_sats": rake_sats,
        "reject_penalty_sats": reject_penalty_sats,
        "entry_sats": entry_sats,
        "fulfiller_payout_gross_sats": max(0, pay_sats - rake_sats),
        "buyer_return_on_reject_gross_sats": max(0, pay_sats - reject_penalty_sats),
    }


def buyer(args: argparse.Namespace) -> Dict[str, Any]:
    buy_cost = args.gig_cost + args.expected_wait_cost + args.delay_risk_cost + args.quality_risk_cost
    local_cost = args.local_execution_cost + args.local_latency_cost + args.local_failure_risk_cost + args.opportunity_cost
    return {
        "mode": "buyer",
        "buy_cost_sats": buy_cost,
        "local_cost_sats": local_cost,
        "delta_sats": local_cost - buy_cost,
        "recommendation": "buy" if buy_cost < local_cost else "execute_locally",
    }


def fulfiller(args: argparse.Namespace) -> Dict[str, Any]:
    cost = args.production_cost + args.opportunity_cost + args.rejection_risk_cost + args.entry_cost
    margin = args.expected_payout - cost
    return {
        "mode": "fulfiller",
        "expected_payout_sats": args.expected_payout,
        "expected_cost_sats": cost,
        "expected_margin_sats": margin,
        "recommendation": "claim" if margin > 0 else "ignore",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="MoltBolt EV helper")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_fees = sub.add_parser("fees")
    p_fees.add_argument("--pay-sats", type=int, required=True)

    p_buyer = sub.add_parser("buyer")
    for name in [
        "gig-cost", "expected-wait-cost", "delay-risk-cost", "quality-risk-cost",
        "local-execution-cost", "local-latency-cost", "local-failure-risk-cost", "opportunity-cost"
    ]:
        p_buyer.add_argument(f"--{name}", type=int, required=True)

    p_fulfiller = sub.add_parser("fulfiller")
    for name in ["expected-payout", "production-cost", "opportunity-cost", "rejection-risk-cost", "entry-cost"]:
        p_fulfiller.add_argument(f"--{name}", type=int, required=True)

    args = parser.parse_args()

    try:
        if args.mode == "fees":
            result = fees(args.pay_sats)
        elif args.mode == "buyer":
            result = buyer(args)
        else:
            result = fulfiller(args)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
