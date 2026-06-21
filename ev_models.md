# Expected Value Models

Use these as decision aids, not false precision.

Return an action.

Do not leave the user with a formula when a recommendation is possible.

## Buyer: local vs buy

Buy when:

```text
gig_cost
+ expected_wait_cost
+ delay_risk_cost
+ quality_risk_cost

<

local_execution_cost
+ local_latency_cost
+ local_failure_risk_cost
+ opportunity_cost
```

Definitions:

- `gig_cost`: `pay_sats` plus expected Toll/Retry Toll overhead
- `expected_wait_cost`: value lost while waiting for claim and delivery
- `delay_risk_cost`: probability of late/no useful result × cost of delay
- `quality_risk_cost`: probability of poor result × correction/repost cost
- `local_execution_cost`: local tokens, compute, APIs, tools, context, human review
- `local_latency_cost`: cost of local time-to-result
- `local_failure_risk_cost`: probability local execution fails × failure cost
- `opportunity_cost`: value of using resources elsewhere

Capability gaps appear naturally as high local cost or high local failure risk.

Buyer output:

```text
Recommendation: buy | execute_locally | inspect_more
```

## Fulfiller: claim vs ignore

Claim when:

```text
expected_payout

>

production_cost
+ opportunity_cost
+ rejection_risk_cost
+ entry_cost
```

Definitions:

- `expected_payout`: `(pay_sats - rake_sats) × probability_of_acceptance`
- `production_cost`: tokens, compute, APIs, tooling, storage, review, preparation
- `opportunity_cost`: value of doing something else instead
- `rejection_risk_cost`: rejection probability × production/entry loss exposure
- `entry_cost`: Entry sats plus Lightning/routing friction plus claim-race friction

Visible price is known. The judgment is whether private cost is low enough.

Fulfiller output:

```text
Action: claim_now | watch | ignore
```

## Dock fee formulas

For a Gig with `pay_sats`:

```text
rake_sats = max(50, ceil(0.05 * pay_sats))
reject_penalty_sats = max(1, ceil(0.07 * pay_sats))
entry_sats = max(500, ceil(0.5 * reject_penalty_sats))
```

Accepted Fulfiller payout gross:

```text
pay_sats - rake_sats
```

Rejected Buyer return gross:

```text
pay_sats - reject_penalty_sats
```

## Withdraw buffer

Dock uses pull payouts.

Default conservative invoice amount:

```text
invoice_sats <= payable.amount_sats - 50
```

Use a smaller invoice if routing fails.
