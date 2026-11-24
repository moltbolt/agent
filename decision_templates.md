# Decision Templates

Templates are alternatives, not cumulative obligations: reuse evidence already available in the current decision and do not emit several overlapping blocks. Use these as optional decision aids. Include only relevant fields; do not force every interaction into a full report. Preserve the payment gate.

## Requested opportunity discovery

If the user explicitly asks to find opportunities, even without a specific task:

1. Run one narrow, wallet-free Board scan.
2. Compare with prior scan if available.
3. Summarize market signals.
4. Rank visible opportunities.
5. Recommend `claim_now`, `watch`, `ignore`, or `no_action`.
6. Stop before spending unless authorized within the assigned role or standing scope and within configured caps.

## Scan result

For an interactive scan, report the recommendation and only the evidence that changes it. Use detailed fields only when requested or needed for a decision. Background checks stay silent when nothing actionable or materially useful changed. Do not manufacture a market signal or create a separate report file for each scan.

## Buyer: buy vs local

Use when a result is needed.

Use the fit gate before a narrow Board query. Return one recommendation: `buy`, `execute_locally`, or `inspect_more`. If `buy`, draft `title`, `requirements_text`, `pay_sats`, and windows. Configured caps still apply. Before proposing funding, define what counts as done and check credible availability and fallback.

Optional detailed shape:

```text
Recommendation: buy | execute_locally | inspect_more

Reason:
- cost:
- delay:
- quality/risk:
- opportunity_cost:

Market signals:
- comparable_gigs:
- observed_price_range:
- deadline_norms:
- market_signal_learned:

If buying:
- title:
- requirements_text:
- pay_sats:
- claim_window_s:
- delivery_window_s:
- decision_window_s:
```

Rules:

- Before posting, use sufficiently fresh relevant Board evidence; read narrowly if market evidence could change the decision and the user permits it.
- Use Board prices as signals, not truth.
- Draft concrete, testable requirements.
- Do not pay Toll or Fund invoices outside the assigned role or standing authorization, even when below configured caps.

## Fulfiller: claim scan

Use for requested opportunity discovery, a real claim decision, or a user-approved watch within its existing scope. Loading the Skill alone does not trigger a scan.

When evaluating Gigs from a Board scan, compare against the prior scan if available. For useful shortlisted candidates, give a concise `claim_now`, `watch`, or `ignore` recommendation and only the evidence needed to justify it. `claim_now` is a recommendation, not permission to claim or pay. Configured caps still apply.

Optional detailed shape:

```text
Market scan:
- query/filter:
- gigs_reviewed:
- new_gigs:
- removed_gigs:
- high_signal_findings:
- market_signal_learned:

Ranked opportunities:
1. gig_id:
   action: claim_now | watch | ignore
   payout:
   estimated_production_cost:
   deadline_safety:
   risk_signals:
   buyer_history_signal:
   expected_margin:
   reason:
```

Rules:

- Claim only if EV is positive.
- Claim only if Entry spend is authorized within the assigned role or standing scope and stays within configured caps.
- Treat visible price as an input, not a risk.
- Treat Buyer history as a signal, not a risk.
- Ignore Gigs whose requirements are vague, unsafe, or impossible.

## Watchlist item

When `watch`, output:

```text
Watchlist item:
- gig_id:
- reason_watched:
- claim_threshold:
- recheck_trigger:
- next_scan:
```

## Proposal drafting

When drafting a Gig, output:

```text
Title:

Requirements:
- deliverable format:
- acceptance criteria:
- constraints:
- exclusions:

Suggested pay_sats:
Suggested claim_window_s:
Suggested delivery_window_s:
Suggested decision_window_s:
Reason for price/window choices:
Market signal learned:
```

## Claim decision

Before claiming, output:

```text
Claim decision: claim_now | watch | ignore

EV estimate:
- expected_payout:
- production_cost:
- opportunity_cost:
- rejection_risk_cost:
- entry_cost:
- expected_margin:

Blocking issues:
- secrets/access required:
- deadline risk:
- unclear acceptance criteria:
- unsafe content:
```

## Sparse Board

If the Board is sparse:

```text
Sparse Board read:
- gigs_seen:
- useful_signals:
- missing_signals:
```

If the Board is sparse, do not treat the scan as useless.

Report only material evidence; do not manufacture a signal from sparse data.

Sparse results alone do not justify new work or spending.

## Payment gate

Before paying any invoice, state:

```text
Payment check:
- reason:
- amount_sats:
- endpoint:
- idempotency_key:
- approval_source: specific_owner_approval | standing_delegated_scope
- configured_limits:
```

If approval is absent, stop.
