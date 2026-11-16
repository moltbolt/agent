#!/usr/bin/env node
// Status only. The host broker owns NWC credentials and the wallet-side policy.
import http from 'node:http';
import {pathToFileURL} from 'node:url';
export const SOCKET_PATH = '/run/mb-wallet-broker/status.sock';
const PIN_PATTERN = /^(02|03)[0-9a-f]{64}$/;
const TIMEOUT_MS = 15000;
const MAX_BYTES = 8192;
const failure = code => Object.assign(new Error(code), {code});

export function sanitizeStatus(body, expectedNodePublicKey) {
  if (!PIN_PATTERN.test(expectedNodePublicKey ?? '')) throw failure('INVALID_PUBLIC_IDENTITY_PIN');
  if (body?.status !== 'verified-read-only' || body.network !== 'bitcoin' ||
      body.nodePublicKey !== expectedNodePublicKey ||
      body.balanceScope !== 'credential-bound-not-other-apps' ||
      body.paymentsEnabled !== false || body.invoiceCreationEnabled !== false ||
      !Number.isSafeInteger(body.connectionBalanceMsat) || body.connectionBalanceMsat < 0 ||
      body.connectionBalanceSats !== body.connectionBalanceMsat / 1000) {
    throw failure('BROKER_RESPONSE_INVALID');
  }
  return {
    status: 'verified-read-only',
    network: 'bitcoin',
    nodePublicKey: expectedNodePublicKey,
    balanceScope: 'credential-bound-not-other-apps',
    connectionBalanceMsat: body.connectionBalanceMsat,
    connectionBalanceSats: body.connectionBalanceSats,
    paymentsEnabled: false,
    invoiceCreationEnabled: false,
  };
}

// requestImpl is for offline tests, not a CLI option or a network destination.
export function get_lightning_status({expectedNodePublicKey, requestImpl = http.request} = {}) {
  if (!PIN_PATTERN.test(expectedNodePublicKey ?? '')) return Promise.reject(failure('INVALID_PUBLIC_IDENTITY_PIN'));
  return new Promise((resolve, reject) => {
    let request, timer, settled = false;
    function finish(error, result) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error) { request?.destroy(); reject(error); }
      else resolve(result);
    }
    timer = setTimeout(() => finish(failure('BROKER_TIMEOUT')), TIMEOUT_MS);
    try {
      request = requestImpl({socketPath: SOCKET_PATH, path: '/v1/status', method: 'GET', agent: false}, response => {
        if (response.statusCode !== 200) {
          response.resume();
          finish(failure(response.statusCode === 429 ? 'BROKER_RATE_LIMITED' : 'BROKER_UNAVAILABLE'));
          return;
        }
        if (!/^application\/json(?:\s*;|$)/i.test(response.headers['content-type'] ?? '')) {
          response.resume(); finish(failure('BROKER_RESPONSE_INVALID')); return;
        }
        let length = 0;
        const chunks = [];
        response.on('data', chunk => {
          const bytes = Buffer.from(chunk); length += bytes.length;
          if (length > MAX_BYTES) { finish(failure('BROKER_RESPONSE_TOO_LARGE')); return; }
          chunks.push(bytes);
        });
        response.on('aborted', () => finish(failure('BROKER_UNAVAILABLE')));
        response.on('error', () => finish(failure('BROKER_UNAVAILABLE')));
        response.on('end', () => {
          if (settled) return;
          try { finish(null, sanitizeStatus(JSON.parse(Buffer.concat(chunks).toString('utf8')), expectedNodePublicKey)); }
          catch { finish(failure('BROKER_RESPONSE_INVALID')); }
        });
      });
      request.on('error', error => finish(failure(
        error.code === 'EACCES' ? 'BROKER_ACCESS_DENIED' : 'BROKER_UNAVAILABLE')));
      request.end();
    } catch { finish(failure('BROKER_UNAVAILABLE')); }
  });
}

export async function main(args = process.argv.slice(2)) {
  if (args.length === 1 && args[0] === '--help') {
    process.stdout.write('Usage: node lightning_status.mjs --expected-node-pubkey <compressed-public-key>\nRead-only local Unix socket status; no payment or invoice commands.\n');
    return 0;
  }
  if (args.length !== 2 || args[0] !== '--expected-node-pubkey' || !PIN_PATTERN.test(args[1])) {
    process.stdout.write(JSON.stringify({status: 'unavailable', code: 'INVALID_ARGUMENTS', automaticRetry: false}) + '\n');
    return 2;
  }
  try {
    const result = await get_lightning_status({expectedNodePublicKey: args[1]});
    process.stdout.write(JSON.stringify(result) + '\n');
    return 0;
  } catch (error) {
    const allowed = new Set(['INVALID_PUBLIC_IDENTITY_PIN', 'BROKER_TIMEOUT', 'BROKER_RATE_LIMITED',
      'BROKER_UNAVAILABLE', 'BROKER_ACCESS_DENIED', 'BROKER_RESPONSE_TOO_LARGE', 'BROKER_RESPONSE_INVALID']);
    process.stdout.write(JSON.stringify({status: 'unavailable', code: allowed.has(error.code) ? error.code : 'BROKER_UNAVAILABLE', automaticRetry: false}) + '\n');
    return 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
