import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { getRuntime } from '../deployment/vercel/runtime.mjs';

const incomingHeaders = ['accept', 'content-type', 'x-benchproof-owner', 'idempotency-key', 'last-event-id'];
const outgoingHeaders = ['content-type', 'content-disposition', 'retry-after'];

export function upstreamRequest(request, origin, token) {
  const original = new URL(request.url, 'https://benchproof.invalid');
  if (!original.pathname.startsWith('/api/v1/')) throw new Error('INVALID_API_PATH');
  const upstream = new URL(origin);
  if (upstream.protocol !== 'https:') throw new Error('INVALID_ORIGIN');
  upstream.pathname = original.pathname;
  upstream.search = original.search;
  const headers = new Headers();
  for (const name of incomingHeaders) {
    const value = request.headers[name];
    if (typeof value === 'string') headers.set(name, value);
  }
  headers.set('X-BenchProof-Origin', token);
  return { url: upstream, headers };
}

export async function requestBody(request) {
  if (request.method === 'GET' || request.method === 'HEAD') return undefined;
  if (request.body !== undefined) {
    const encoded = Buffer.isBuffer(request.body) ? request.body : Buffer.from(typeof request.body === 'string' ? request.body : JSON.stringify(request.body));
    if (encoded.length > 64 * 1024) throw new Error('REQUEST_TOO_LARGE');
    return encoded;
  }
  const chunks = [];
  let length = 0;
  for await (const chunk of request) {
    const bytes = Buffer.from(chunk);
    length += bytes.length;
    if (length > 64 * 1024) throw new Error('REQUEST_TOO_LARGE');
    chunks.push(bytes);
  }
  return Buffer.concat(chunks);
}

export function createGateway(resolveRuntime = getRuntime, fetchUpstream = fetch) {
  return async function gateway(request, response) {
    const abort = new AbortController();
    response.once('close', () => { if (!response.writableEnded) abort.abort(); });
    try {
      const parsed = new URL(request.url, 'https://benchproof.invalid');
      if (!parsed.pathname.startsWith('/api/v1/')) throw new Error('INVALID_API_PATH');
      const body = await requestBody(request);
      const runtime = await resolveRuntime();
      const target = upstreamRequest(request, runtime.origin, runtime.token);
      const upstream = await fetchUpstream(target.url, {
        method: request.method,
        headers: target.headers,
        body,
        redirect: 'manual',
        signal: AbortSignal.any([abort.signal, AbortSignal.timeout(180_000)]),
      });
      if (upstream.status >= 300 && upstream.status < 400) throw new Error('UNEXPECTED_ORIGIN_REDIRECT');
      response.statusCode = upstream.status;
      response.setHeader('Cache-Control', 'no-store');
      for (const name of outgoingHeaders) {
        const value = upstream.headers.get(name);
        if (value) response.setHeader(name, value);
      }
      response.flushHeaders?.();
      if (upstream.body) await pipeline(Readable.fromWeb(upstream.body), response);
      else response.end();
    } catch (error) {
      if (response.headersSent) { response.destroy(); return; }
      const code = error.message === 'REQUEST_TOO_LARGE' ? 'REQUEST_TOO_LARGE' : error.message === 'INVALID_API_PATH' ? 'INVALID_API_PATH' : 'CLOUD_RUNTIME_UNAVAILABLE';
      response.statusCode = code === 'REQUEST_TOO_LARGE' ? 413 : code === 'INVALID_API_PATH' ? 404 : 503;
      response.setHeader('Content-Type', 'application/json');
      response.setHeader('Cache-Control', 'no-store');
      response.end(JSON.stringify({ detail: { code, message: 'The cloud runtime is unavailable or the request cannot be served. Retry later.' } }));
    }
  };
}

export default createGateway();
