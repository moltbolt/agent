# Read-only broker status integration

This is the implementation of `get_lightning_status()` for a separately operated
wallet-status broker. It is not a payment adapter. Installing this helper does
not authorize an agent run or any financial action.

## Operator configuration

Requires Node 24 and access to `/run/mb-wallet-broker/status.sock`. The operator
must supply the expected compressed Lightning public key, not an NWC wallet key
or secret. The script uses only Node built-ins and installs no dependencies.

```sh
node /absolute/path/to/moltbolt/scripts/lightning_status.mjs \
  --expected-node-pubkey <compressed-Lightning-public-key>
```

Configure that exact command as `MOLTBOLT_LN_STATUS_HELPER` in the existing
operator-managed helper configuration. Do not use shell interpolation of agent
input. No URI, password, macaroon or other wallet credential belongs in this
command or the agent's environment. This document does not deploy/configure it.

For the current isolated status-probe setup, the broker is bound to app 3. Its
balance is separate from the funded application's 20k-sat ledger. A zero result
means the probe balance is zero, not that the funded application is empty.
The displayed connection balance is not a promise of spendable liquidity.

## Contract

The helper makes one `GET /v1/status` request over the fixed Unix socket. It
requires the pinned Lightning identity, Bitcoin mainnet, credential-bound
balance scope, valid msat/sat amounts, and disabled payment/invoice operations.
It returns a small JSON object containing only those verified status fields.
Unknown fields, raw errors, transactions, secrets and wallet metadata are never
forwarded. A missing/misconfigured broker returns sanitized JSON and exit 2.
Success returns exit 0. No retries, redirects, TCP fallback or destination options.
There is a 15-second absolute deadline and an 8192-byte response limit.

`get_lightning_status({expectedNodePublicKey})` is also exported for local code.
Its injectable transport is an offline-test hook, not a CLI capability.

## Strict boundary for this stage

- Leave `MOLTBOLT_LN_PAY_HELPER` and `MOLTBOLT_LN_INVOICE_HELPER` unset.
- Do not label this helper as a payment-capable `MOLTBOLT_LIGHTNING_ADAPTER`.
- Payment, invoice creation, funding and settlement flows must still stop at
  the missing/disabled capability boundary, even after a successful status read.
- Do not pass NWC URIs, admin credentials, invoices, arbitrary paths or methods.
- Do not scan the Board, start heartbeat/cron, or message the agent merely to
  test this helper. A standalone status test is sufficient for this component.

Unix permissions grant status access to any process with the socket group,
not to a particular agent identity. The host broker and wallet-side read-only
permission enforce the actual boundary. Agent-owned code alone is not a security
boundary against an agent with unrestricted shell access.

No deployment, live agent execution, payment/invoice functionality, or automatic
startup configuration is included in this repository change. Future gateway
Compose operations must keep the operator's socket override; broker boot state
is managed separately. If status is unavailable, report it without inventing a
balance or repeatedly probing.
