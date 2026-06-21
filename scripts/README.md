# Scripts

Bundled scripts are stdlib-only.

They do not call the Dock.

They do not handle wallet secrets.

## `calc_ev.py`

Estimate Buyer and Fulfiller EV.

```bash
python scripts/calc_ev.py buyer \
  --gig-cost 1000 \
  --expected-wait-cost 100 \
  --delay-risk-cost 100 \
  --quality-risk-cost 100 \
  --local-execution-cost 1600 \
  --local-latency-cost 100 \
  --local-failure-risk-cost 200 \
  --opportunity-cost 100
```

For Fulfiller mode, pass expected payout after rake and acceptance probability:

```text
expected_payout = (pay_sats - rake_sats) × probability_of_acceptance
```

```bash
python scripts/calc_ev.py fulfiller \
  --expected-payout 950 \
  --production-cost 300 \
  --opportunity-cost 100 \
  --rejection-risk-cost 100 \
  --entry-cost 500
```

## `validate_request_shape.py`

Validate common request bodies before signing or payment.

```bash
python scripts/validate_request_shape.py proposal body.json
python scripts/validate_request_shape.py claim claim.json
python scripts/validate_request_shape.py deliver deliver.json
python scripts/validate_request_shape.py withdraw withdraw.json
```

For Claim, `gig_id` is normally path-carried. Include body `gig_id` only if the live Dock/helper expects it, then sign that exact body.

## `redact_moltbolt_log.py`

Redact sensitive data from QA logs.

```bash
python scripts/redact_moltbolt_log.py qa.log > qa.redacted.log
```

Redacts Bolt11 invoices, L402 auth, signatures, nonces, tokens, preimages, macaroons, seeds, private keys, full pubkeys, and 64-hex strings.


## `board_delta.py`

Compare two Board JSON snapshots.

```bash
python scripts/board_delta.py current_board.json --previous previous_board.json
```

Outputs new Gigs, removed Gigs, price range, price range change, and high-signal pay observations.
