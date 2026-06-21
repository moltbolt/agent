#!/usr/bin/env python3
"""Compare MoltBolt Board JSON snapshots.

Stdlib only. Does not call the Dock.
Expected input: JSON object with an `items` array, or a raw array of Gig cards.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def load_items(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        return []
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        raise SystemExit(f"Unsupported JSON root in {path}")
    if not isinstance(items, list):
        raise SystemExit(f"Expected items array in {path}")
    return [x for x in items if isinstance(x, dict)]


def by_id(items: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for item in items:
        gid = item.get("gig_id")
        if isinstance(gid, str) and gid:
            out[gid] = item
    return out


def price_range(items: List[Dict[str, Any]]) -> Tuple[int | None, int | None]:
    vals = [x.get("pay_sats") for x in items]
    nums = [int(v) for v in vals if isinstance(v, int) or (isinstance(v, str) and v.isdigit())]
    return (min(nums), max(nums)) if nums else (None, None)


def high_signal(items: List[Dict[str, Any]], min_pay_sats: int) -> List[Dict[str, Any]]:
    rows = []
    for x in items:
        pay = x.get("pay_sats")
        if isinstance(pay, str) and pay.isdigit():
            pay = int(pay)
        if not isinstance(pay, int) or pay < min_pay_sats:
            continue
        rows.append({
            "gig_id": x.get("gig_id"),
            "title": x.get("title"),
            "pay_sats": pay,
            "claim_deadline": x.get("claim_deadline"),
        })
    rows.sort(key=lambda r: r.get("pay_sats") or 0, reverse=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("current", help="current Board JSON")
    ap.add_argument("--previous", help="previous Board JSON")
    ap.add_argument("--min-high-signal-pay-sats", type=int, default=0)
    args = ap.parse_args()

    cur = load_items(args.current)
    prev = load_items(args.previous)
    cur_by = by_id(cur)
    prev_by = by_id(prev)

    new_ids = sorted(set(cur_by) - set(prev_by))
    removed_ids = sorted(set(prev_by) - set(cur_by))
    cur_range = price_range(cur)
    prev_range = price_range(prev)

    out = {
        "gigs_reviewed": len(cur),
        "new_gigs": new_ids,
        "removed_gigs": removed_ids,
        "observed_price_range": {"min_sats": cur_range[0], "max_sats": cur_range[1]},
        "previous_price_range": {"min_sats": prev_range[0], "max_sats": prev_range[1]},
        "price_range_change": {
            "min_delta_sats": None if cur_range[0] is None or prev_range[0] is None else cur_range[0] - prev_range[0],
            "max_delta_sats": None if cur_range[1] is None or prev_range[1] is None else cur_range[1] - prev_range[1],
        },
        "new_high_signal_opportunities": high_signal([cur_by[i] for i in new_ids], args.min_high_signal_pay_sats),
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
