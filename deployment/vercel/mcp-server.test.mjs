import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createServer } from 'node:http';
import { once } from 'node:events';
import mcp from '../../api/mcp.mjs';

function message(method, parameters = {}, version = '2026-07-28') {
  return { jsonrpc: '2.0', id: 'test-request', method, params: { ...parameters, _meta: { 'io.modelcontextprotocol/protocolVersion': version, 'io.modelcontextprotocol/clientInfo': { name: 'test', version: '1' }, 'io.modelcontextprotocol/clientCapabilities': {} } } };
}
async function withServer(action) {
  const server = createServer(mcp);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try { await action(`http://127.0.0.1:${server.address().port}`); }
  finally { await new Promise(resolve => server.close(resolve)); }
}
async function rpc(url, payload, overrides = {}) {
  const headers = { 'content-type': 'application/json', 'mcp-protocol-version': payload.params._meta['io.modelcontextprotocol/protocolVersion'], 'mcp-method': payload.method, ...(payload.params.name ? { 'mcp-name': payload.params.name } : {}), ...overrides };
  const response = await fetch(url, { method: 'POST', headers, body: JSON.stringify(payload) });
  return { status: response.status, body: await response.json() };
}

test('public docs server declares its version and one genuinely read-only tool', async () => withServer(async url => {
  const discovered = await rpc(url, message('server/discover'));
  assert.equal(discovered.status, 200);
  assert.deepEqual(discovered.body.result.supportedVersions, ['2026-07-28']);
  const listing = await rpc(url, message('tools/list'));
  assert.equal(listing.status, 200);
  assert.equal(listing.body.result.tools.length, 1);
  assert.equal(listing.body.result.tools[0].annotations.readOnlyHint, true);
  assert.equal(listing.body.result.tools[0].annotations.destructiveHint, false);
}));

test('public docs server returns bounded static guides without credentials or source', async () => withServer(async url => {
  process.env.NEBIUS_API_KEY = 'synthetic-private-value-must-not-appear';
  try {
    for (const argumentsValue of [{}, { topic: 'skills' }, { topic: 'harness' }, { topic: 'mcp' }, { topic: 'budgets' }]) {
      const result = await rpc(url, message('tools/call', { name: 'read_guide', arguments: argumentsValue }));
      assert.equal(result.status, 200);
      const content = result.body.result.content[0].text;
      assert.ok(content.length > 100 && content.length <= 2000);
      assert.equal(content.includes(process.env.NEBIUS_API_KEY), false);
    }
  } finally { delete process.env.NEBIUS_API_KEY; }
}));

test('public docs server rejects origin and metadata/header mismatches', async () => withServer(async url => {
  const payload = message('tools/call', { name: 'read_guide', arguments: {} });
  assert.equal((await rpc(url, payload, { origin: 'https://untrusted.example' })).status, 403);
  assert.equal((await rpc(url, payload, { 'mcp-name': 'execute_shell' })).body.error.code, -32020);
  assert.equal((await rpc(url, payload, { 'mcp-method': 'tools/list' })).status, 400);
  assert.equal((await rpc(url, payload, { 'mcp-protocol-version': '2025-11-25' })).status, 400);
  const legacy = await rpc(url, message('initialize', {}, '2025-11-25'));
  assert.equal(legacy.body.error.code, -32022);
  assert.deepEqual(legacy.body.error.data.supported, ['2026-07-28']);
}));

test('public docs server has no arbitrary fetch, execution or unknown topics', async () => withServer(async url => {
  for (const parameters of [{ name: 'execute_shell', arguments: {} }, { name: 'read_guide', arguments: { url: 'https://example.org' } }, { name: 'read_guide', arguments: { topic: '__proto__' } }, { name: 'read_guide', arguments: { topic: 4 } }]) {
    assert.equal((await rpc(url, message('tools/call', parameters))).body.error.code, -32602);
  }
  assert.equal((await rpc(url, message('private/read'))).status, 404);
  assert.equal((await rpc(url, message('tools/call', { name: 'read_guide', arguments: { topic: null } }))).status, 400);
}));

test('public docs server rejects invalid, oversized and non-POST requests', async () => withServer(async url => {
  assert.equal((await fetch(url)).status, 405);
  assert.equal((await fetch(url, { method: 'POST', body: '{}' })).status, 415);
  assert.equal((await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{broken' })).status, 400);
  assert.equal((await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: 'x'.repeat(8193) })).status, 413);
  const payload = message('tools/list');
  delete payload.params._meta;
  const response = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) });
  assert.equal(response.status, 400);
}));
