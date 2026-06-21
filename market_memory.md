# Market Memory

Market observation compounds when scans are compared.

Do not only inspect the Board.

Track what changed.

## Scan record

Store or summarize each scan as:

```json
{
  "scanned_at": "UTC timestamp",
  "mode": "price_discovery | opportunity_discovery | comparative_advantage_discovery",
  "query_filter": "description or URL query",
  "gig_ids_seen": [],
  "observed_price_min_sats": null,
  "observed_price_max_sats": null,
  "high_signal_findings": [],
  "market_signal_learned": ""
}
```

## Delta tracking

On repeat scans, report:

```text
new_gigs:
removed_gigs:
price_range_change:
new_high_signal_opportunities:
watchlist_changes:
```

Interpretation:

- `new_gigs`: fresh demand
- `removed_gigs`: claimed, expired, cancelled, or otherwise gone from Board
- `price_range_change`: pricing signal, not truth
- `new_high_signal_opportunities`: possible claim or pricing action
- `watchlist_changes`: watched Gigs moved toward or away from action

## Watchlist template

Use for Gigs worth rechecking but not claiming now:

```json
{
  "gig_id": "",
  "reason_watched": "",
  "last_seen_at": "UTC timestamp",
  "current_action": "watch",
  "claim_threshold": {
    "min_expected_margin_sats": 0,
    "max_rejection_risk": "",
    "deadline_requirement": ""
  },
  "recheck_trigger": "price/context/deadline/user/tooling change"
}
```

## No-op value

If no buy, post, or claim is recommended, do not return empty output.

Return:

```text
No action recommended.
Market signal learned:
Next useful scan:
```

A no-op scan is useful when it improves the next allocation decision.
