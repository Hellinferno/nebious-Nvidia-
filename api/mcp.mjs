const protocolVersion = '2026-07-28';
const publicOrigin = 'https://benchproof.vercel.app';
const guides = Object.freeze({
  workflow: 'BenchProof workflow: choose a small Python project, describe the outcome, select up to three editable app/ files, and optionally customize the agent. Creating a draft makes no inference call. Generate a plan, review its exact source and preferences, then approve it. Implementation requires an explicit Start action. Tests remain read-only. Inspect the final diff and fresh checks before accepting changes. Passing supplied project tests is scoped evidence, not proof of untested requirements. This is public product guidance, not project source or test evidence.',
  skills: 'BenchProof skills are instruction-only snapshots. Create a skill or import a small SKILL.md with scalar name/description frontmatter and Markdown instructions. Save up to ten local skills and select up to three per new task. Scripts, archives and linked assets are not installed. A skill has at most 2,000 instruction characters; the combined model context also has a byte limit. Editing the library does not change a selected snapshot, saved profile or existing task. Deselect/reselect to use updated text. Portable profiles include selected skill text, so inspect exports and never put secrets in instructions.',
  harness: 'BenchProof offers two reviewed built-in orchestration strategies. bounded-v1 allows at most two candidate attempts within the task budget. single-pass-v1 permits one candidate and stops on failed checks without automatic revision. Neither strategy can grant permissions, change provider credentials, reset quotas or execute a third-party harness plugin. Plan-only mode is a separate backend restriction that refuses implementation and test execution. Harness, mode and skill snapshots are pinned to the task brief and plan approval.',
  mcp: 'BenchProof MCP context is explicit, read-only reference retrieval. Load the approved catalog, choose a tool, enter JSON arguments and consent to sending those exact arguments. Source is not attached automatically. Review returned text before creating a task. At most two snapshots are pinned by hash in the task; they are not portable-profile settings or verification evidence. Failed queries consume a shared daily allowance. The bridge supports a restricted modern stateless JSON transport, not stdio, older session initialization, SSE, OAuth setup, automatic model-selected calls or arbitrary server URLs. This documentation server returns public guides only; read_guide accepts an optional topic: workflow, skills, harness, mcp or budgets.',
  budgets: 'Default task upper bounds are four model calls, two edit attempts, four test executions and 300 active seconds. Users can lower, not raise, these allowances. Single-pass additionally caps edit attempts at one. Daily server limits and session admission still apply. A first implementation normally needs planning and editing calls plus baseline, candidate and fresh final checks. Lower budgets can intentionally stop a task early. Reservations survive restarts; canceling a request does not guarantee the provider can unbill an accepted call. These limits are not a fixed currency or total-token guarantee.',
});
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const serverInfo = { name: 'benchproof-public-guides', version: '1.0.0' };
const tool = {
  name: 'read_guide', title: 'Read a public BenchProof guide',
  description: 'Return static public workflow, skills, harness, MCP or budget guidance. No source, secrets, execution or model calls.',
  annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  inputSchema: { type: 'object', properties: { topic: { type: 'string', enum: Object.keys(guides) } }, additionalProperties: false },
};

function reply(response, status, body) {
  response.statusCode = status;
  response.setHeader('Content-Type', 'application/json; charset=utf-8');
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.end(JSON.stringify(body));
}

function headerName(value) {
  if (typeof value !== 'string' || value.length > 512) return null;
  if (!value.startsWith('=?base64?') || !value.endsWith('?=')) return value;
  const encoded = value.slice(9, -2);
  const bytes = Buffer.from(encoded, 'base64');
  if (bytes.toString('base64') !== encoded) return null;
  try { return new TextDecoder('utf-8', { fatal: true }).decode(bytes); } catch { return null; }
}

async function body(request) {
  let bytes;
  if (request.body !== undefined) bytes = Buffer.from(typeof request.body === 'string' ? request.body : Buffer.isBuffer(request.body) ? request.body : JSON.stringify(request.body));
  else {
    const chunks = [];
    let length = 0;
    for await (const chunk of request) {
      length += chunk.length;
      if (length > 8192) throw new Error('MCP_REQUEST_TOO_LARGE');
      chunks.push(Buffer.from(chunk));
    }
    bytes = Buffer.concat(chunks);
  }
  if (bytes.length > 8192) throw new Error('MCP_REQUEST_TOO_LARGE');
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}

export default async function mcp(request, response) {
  const fail = (status, id, code, message, data) => reply(response, status, { jsonrpc: '2.0', id, error: { code, message, ...(data ? { data } : {}) } });
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'POST');
    return fail(405, null, -32600, 'Use a stateless JSON-RPC POST');
  }
  if (request.headers.origin !== undefined && request.headers.origin !== publicOrigin) return fail(403, null, -32600, 'Origin is not allowed');
  if (request.headers['content-type']?.split(';')[0].trim().toLowerCase() !== 'application/json') return fail(415, null, -32600, 'JSON content type is required');
  let message;
  try { message = await body(request); }
  catch (error) { return fail(error.message === 'MCP_REQUEST_TOO_LARGE' ? 413 : 400, null, -32700, 'Invalid or oversized JSON request'); }
  if (!record(message) || message.jsonrpc !== '2.0' || !(Number.isSafeInteger(message.id) || (typeof message.id === 'string' && message.id.length > 0 && message.id.length <= 100)) || typeof message.method !== 'string' || !record(message.params)) return fail(400, null, -32600, 'Invalid JSON-RPC request');
  const { id, method, params } = message;
  const metadata = params._meta;
  if (!record(metadata) || !record(metadata['io.modelcontextprotocol/clientCapabilities']) || !record(metadata['io.modelcontextprotocol/clientInfo']) || typeof metadata['io.modelcontextprotocol/clientInfo'].name !== 'string' || typeof metadata['io.modelcontextprotocol/clientInfo'].version !== 'string') return fail(400, id, -32600, 'Required client metadata is missing');
  const version = metadata['io.modelcontextprotocol/protocolVersion'];
  if (request.headers['mcp-protocol-version'] !== version || request.headers['mcp-method'] !== method || (method === 'tools/call' && headerName(request.headers['mcp-name']) !== params.name)) return fail(400, id, -32020, 'MCP request headers do not match the body');
  if (version !== protocolVersion) return fail(400, id, -32022, 'Unsupported protocol version', { supported: [protocolVersion] });
  const complete = result => reply(response, 200, { jsonrpc: '2.0', id, result: { resultType: 'complete', _meta: { 'io.modelcontextprotocol/serverInfo': serverInfo }, ...result } });
  if (method === 'server/discover') return complete({ supportedVersions: [protocolVersion], capabilities: { tools: {} }, instructions: 'Public reference guides only. Not project context or verification evidence.' });
  if (method === 'ping') return complete({});
  if (method === 'tools/list') return complete({ tools: [tool] });
  if (method !== 'tools/call') return fail(404, id, -32601, 'Method not found; modern stateless protocol only');
  if (params.name !== tool.name || !record(params.arguments) || Object.keys(params.arguments).some(key => key !== 'topic')) return fail(400, id, -32602, 'Only read_guide with optional topic is supported');
  const topic = Object.hasOwn(params.arguments, 'topic') ? params.arguments.topic : 'workflow';
  if (typeof topic !== 'string' || !Object.hasOwn(guides, topic)) return fail(400, id, -32602, 'Unknown public guide topic');
  return complete({ content: [{ type: 'text', text: guides[topic] }], isError: false });
}
