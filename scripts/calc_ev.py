#!/usr/bin/env python3
"""MoltBolt EV helper.

Stdlib only. No network. No wallet access.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, DecimalException
import json
import math
from typing import Dict, Any


NEW_GIG_FEE_POLICY = "rake-4-floor50-reject25-v1"


BUYER_TERMS = (
    "gig_cost", "specification_cost", "verification_cost", "expected_wait_cost",
    "delay_risk_cost", "quality_risk_cost", "buy_opportunity_cost",
    "local_execution_cost", "local_latency_cost", "local_failure_risk_cost",
    "local_opportunity_cost",
)
FULFILLER_TERMS = (
    "probability_of_accepted_payout", "accepted_invoice_sats", "success_only_cost_sats",
    "expected_rejection_receipts_sats", "per_attempt_cost_sats",
)


def nonnegative(name: str, value: Decimal) -> Decimal:
    if not value.is_finite() or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def estimate(value: str) -> Decimal:
    try:
        return Decimal(value)
    except DecimalException:
        raise argparse.ArgumentTypeError("estimate must be a number")


def fees(pay_sats: int) -> Dict[str, Any]:
    """Estimate fees for a newly posted Gig, not an existing Gig."""
    if pay_sats < 1:
        raise ValueError("pay_sats must be >= 1")
    rake_sats = max(50, (4 * pay_sats + 99) // 100)
    reject_penalty_sats = max(1, (7 * pay_sats + 99) // 100)
    entry_sats = max(500, (reject_penalty_sats + 1) // 2)
    return {
        "pay_sats": pay_sats,
        "fee_policy": NEW_GIG_FEE_POLICY,
        "scope": "new-gig-estimate",
        "rake_sats": rake_sats,
        "reject_penalty_sats": reject_penalty_sats,
        "fulfiller_rejection_share_sats": reject_penalty_sats // 4,
        "entry_sats": entry_sats,
        "fulfiller_payout_gross_sats": max(0, pay_sats - rake_sats),
        "buyer_return_on_reject_gross_sats": max(0, pay_sats - reject_penalty_sats),
    }


def buyer(args: argparse.Namespace) -> Dict[str, Any]:
    for name in BUYER_TERMS:
        nonnegative(name, getattr(args, name))
    buy_cost = (args.gig_cost + args.specification_cost + args.verification_cost
                + args.expected_wait_cost + args.delay_risk_cost + args.quality_risk_cost
                + args.buy_opportunity_cost)
    local_cost = (args.local_execution_cost + args.local_latency_cost
                  + args.local_failure_risk_cost + args.local_opportunity_cost)
    return {
        "mode": "buyer",
        "buy_cost": buy_cost,
        "local_cost": local_cost,
        "delta_sats": local_cost - buy_cost,
        "decision": "buy" if buy_cost < local_cost else "execute_locally",
    }


def fulfiller(args: argparse.Namespace) -> Dict[str, Any]:
    for name in FULFILLER_TERMS:
        nonnegative(name, getattr(args, name))
    if args.probability_of_accepted_payout > 1:
        raise ValueError("probability_of_accepted_payout must be in [0, 1]")
    expected_payout = (args.probability_of_accepted_payout
                       * (args.accepted_invoice_sats - args.success_only_cost_sats)
                       + args.expected_rejection_receipts_sats)
    expected_costs = args.per_attempt_cost_sats
    expected_margin = expected_payout - expected_costs
    return {
        "mode": "fulfiller",
        "expected_payout": expected_payout,
        "expected_costs": expected_costs,
        "expected_margin": expected_margin,
        "decision": "claim" if expected_margin > 0 else "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="MoltBolt EV helper", allow_abbrev=False)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_fees = sub.add_parser(
        "fees", help="estimate fees for a newly posted Gig",
        description="Estimate fees for a newly posted Gig. For existing Gigs, use Dock amounts.",
    )
    p_fees.add_argument("--pay-sats", type=int, required=True)

    p_buyer = sub.add_parser("buyer", allow_abbrev=False)
    for name in BUYER_TERMS:
        p_buyer.add_argument(f"--{name.replace('_', '-')}", type=estimate, required=True,
                            help=f"{name}, estimated in sats")

    p_fulfiller = sub.add_parser("fulfiller", allow_abbrev=False)
    for name in FULFILLER_TERMS:
        help_text = (f"{name}, from 0 to 1" if name == "probability_of_accepted_payout"
                     else f"{name}, estimated in sats")
        p_fulfiller.add_argument(f"--{name.replace('_', '-')}", type=estimate, required=True, help=help_text)

    args = parser.parse_args()

    try:
        if args.mode == "fees":
            result = fees(args.pay_sats)
        elif args.mode == "buyer":
            result = buyer(args)
        else:
            result = fulfiller(args)
    except (ValueError, DecimalException) as exc:
        parser.error(str(exc))

    # Decide in decimal arithmetic before converting estimates to JSON numbers.
    for name, value in result.items():
        if isinstance(value, Decimal):
            converted = int(value) if value == value.to_integral_value() else float(value)
            if isinstance(converted, float) and not math.isfinite(converted):
                parser.error(f"{name} is too large for a JSON number")
            result[name] = converted
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
