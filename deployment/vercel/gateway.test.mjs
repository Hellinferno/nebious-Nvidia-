import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createServer } from 'node:http';
import { test } from 'node:test';
import { Readable } from 'node:stream';
import { createGateway, requestBody, upstreamRequest } from '../../api/gateway.mjs';

test('forwarding preserves API path, query and owner but replaces origin credentials', () => {
  const request = {
    url: '/api/v1/audits/demo/events?after=4',
    headers: { 'x-benchproof-owner': 'owner-demo', 'x-benchproof-origin': 'attacker', authorization: 'private', 'last-event-id': '4' },
  };
  const forwarded = upstreamRequest(request, 'https://private-origin.vercel.run', 'server-only-token');
  assert.equal(forwarded.url.href, 'https://private-origin.vercel.run/api/v1/audits/demo/events?after=4');
  assert.equal(forwarded.headers.get('X-BenchProof-Owner'), 'owner-demo');
  assert.equal(forwarded.headers.get('X-BenchProof-Origin'), 'server-only-token');
  assert.equal(forwarded.headers.has('authorization'), false);
  assert.equal(forwarded.headers.get('last-event-id'), '4');
});

test('paths outside the API and non-HTTPS origins are refused', () => {
  for (const url of ['/.env', '/api/gateway', '/api/v1/../../.env', '//evil.example/private']) {
    assert.throws(() => upstreamRequest({ url, headers: {} }, 'https://origin.vercel.run', 'secret'));
  }
  assert.throws(() => upstreamRequest({ url: '/api/v1/health', headers: {} }, 'http://origin', 'secret'));
});

test('both parsed and streamed oversized request bodies are rejected', async () => {
  await assert.rejects(requestBody({ method: 'POST', body: 'x'.repeat(65537) }), /REQUEST_TOO_LARGE/);
  const stream = Readable.from([Buffer.alloc(32768), Buffer.alloc(32769)]);
  stream.method = 'POST';
  await assert.rejects(requestBody(stream), /REQUEST_TOO_LARGE/);
  assert.equal(await requestBody({ method: 'GET' }), undefined);
});

async function withGateway(handler, action) {
  const server = createServer(handler);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try { await action(`http://127.0.0.1:${server.address().port}`); }
  finally { await new Promise(resolve => server.close(resolve)); }
}

test('SSE streams and private origin headers do not reach the response', async () => {
  const handler = createGateway(
    async () => ({ origin: 'https://origin.vercel.run', token: 'origin-secret' }),
    async (url, options) => {
      assert.equal(options.redirect, 'manual');
      assert.equal(options.headers.get('X-BenchProof-Origin'), 'origin-secret');
      return new Response('event: audit_created\ndata: {"sequence":1}\n\n', {
        headers: { 'content-type': 'text/event-stream', 'x-benchproof-origin': 'origin-secret' },
      });
    },
  );
  await withGateway(handler, async base => {
    const response = await fetch(`${base}/api/v1/audits/demo/events`);
    assert.equal(response.status, 200);
    assert.match(await response.text(), /event: audit_created/);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.equal(response.headers.has('x-benchproof-origin'), false);
  });
});

test('missing runtime fails closed without exposing exception details', async () => {
  await withGateway(createGateway(async () => { throw new Error('private-token-value'); }), async base => {
    const response = await fetch(`${base}/api/v1/health`);
    assert.equal(response.status, 503);
    assert.doesNotMatch(await response.text(), /private-token-value/);
  });
});

test('upstream redirects are not followed or exposed', async () => {
  const handler = createGateway(
    async () => ({ origin: 'https://origin.vercel.run', token: 'secret' }),
    async () => new Response(null, { status: 302, headers: { location: 'https://untrusted.example' } }),
  );
  await withGateway(handler, async base => {
    const response = await fetch(`${base}/api/v1/health`);
    assert.equal(response.status, 503);
    assert.equal(response.headers.has('location'), false);
  });
});
