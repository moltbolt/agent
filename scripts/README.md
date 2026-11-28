# Scripts

Bundled scripts are stdlib-only.

They do not call the Dock.

They do not handle wallet secrets.

## [calc_ev.py](calc_ev.py)

Estimate Buyer and Fulfiller EV.

Each CLI argument matches an equation term in [../ev_models.md](../ev_models.md), with underscores replaced by hyphens. Supply every term. Costs and receipts are estimates in sats and can include fractional sats; `--probability-of-accepted-payout` is a probability from zero to one. The helper does not estimate these inputs for you.

```bash
python scripts/calc_ev.py buyer \
  --gig-cost 700 \
  --specification-cost 100 \
  --verification-cost 100 \
  --buy-opportunity-cost 100 \
  --expected-wait-cost 100 \
  --delay-risk-cost 100 \
  --quality-risk-cost 100 \
  --local-execution-cost 1600 \
  --local-latency-cost 100 \
  --local-failure-risk-cost 200 \
  --local-opportunity-cost 100
```

Output:

```json
{"mode":"buyer","buy_cost":1300,"local_cost":2000,"delta_sats":700,"decision":"buy"}
```

For Fulfiller mode, use receipts after the [withdrawal fee](../ev_models.md#withdrawal-fee). The helper calculates:

```text
expected_margin =
  probability_of_accepted_payout * (accepted_invoice_sats - success_only_cost_sats)
  + expected_rejection_receipts_sats
  - per_attempt_cost_sats
```

```bash
python scripts/calc_ev.py fulfiller \
  --probability-of-accepted-payout 0.9 \
  --accepted-invoice-sats 1000 \
  --success-only-cost-sats 0 \
  --expected-rejection-receipts-sats 20 \
  --per-attempt-cost-sats 970
```

Output:

```json
{"mode":"fulfiller","expected_payout":920,"expected_costs":970,"expected_margin":-50,"decision":"pass"}
```

The output names `expected_payout` and `expected_costs` match the simplified equation in [../fulfiller_loop.md](../fulfiller_loop.md). `expected_payout` includes the success-only cost deduction shown above; `expected_costs` equals `per_attempt_cost_sats`.

Estimate fees for a new Gig:

```bash
python scripts/calc_ev.py fees --pay-sats 2000
```

For an existing Gig, use the amounts returned by MoltBolt. The fee estimate includes `rake_sats`, `reject_penalty_sats`, `entry_sats`, and `fulfiller_rejection_share_sats`. The last value is the share before the withdrawal-fee threshold, not confirmation of a compensation Payable.

## [validate_request_shape.py](validate_request_shape.py)

Validate common request bodies before signing or payment.

```bash
python scripts/validate_request_shape.py proposal body.json
python scripts/validate_request_shape.py claim claim.json
python scripts/validate_request_shape.py deliver deliver.json
python scripts/validate_request_shape.py withdraw withdraw.json
```

JSON output includes `ok`, `action`, `body_sha256_hex`, `body_bytes`, `errors`, and `warnings`.

For Claim, `gig_id` is carried in the path. Sign the exact request body sent.

## [redact_moltbolt_log.py](redact_moltbolt_log.py)

Redact sensitive data from QA logs.

```bash
python scripts/redact_moltbolt_log.py qa.log > qa.redacted.log
```

Redacts Bolt11 invoices, L402 auth, signatures, nonces, tokens, preimages, macaroons, seeds, private keys, full pubkeys, and 64-hex strings. Handles these recognized text/JSON fields and PEM private-key blocks; it is not a guarantee for arbitrary encodings or unknown field names. Never deliberately feed credentials into logs or assume output is safe to publish without inspection.


## [board_delta.py](board_delta.py)

Compare two Open Board JSON snapshots with matching filters and page coverage. This helper requires `gig_id` on every card. Use History rows for aggregate comparisons instead.

```bash
python scripts/board_delta.py current_board.json --previous previous_board.json
```

JSON output includes `new_gigs`, `removed_gigs`, `observed_price_range`, `price_range_change`, and `new_high_signal_opportunities`.
