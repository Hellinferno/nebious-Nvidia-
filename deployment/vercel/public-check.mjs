import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { Sandbox } from '@vercel/sandbox';

const root = new URL('../../', import.meta.url);
const base = new URL(process.argv[2]);
if (base.protocol !== 'https:' || !base.hostname.endsWith('.vercel.app') || base.username || base.password) throw new Error('An HTTPS Vercel production URL is required');
const headers = { 'X-BenchProof-Owner': `public-check-${randomBytes(8).toString('hex')}` };
const evidence = { schema: 'benchproof/vercel-public-check-v1', timestamp: new Date().toISOString(), url: base.origin, verified: false };
const skipProvider = process.argv.includes('--skip-provider');
evidence.scope = skipProvider ? 'public-infrastructure-without-model-call' : 'public-infrastructure-and-live-diagnosis';
let phase = 'frontend';

async function request(path, options = {}) {
  return fetch(new URL(path, base), { ...options, headers: { ...headers, ...options.headers }, redirect: 'error', signal: AbortSignal.timeout(240_000) });
}

async function json(path, options = {}) {
  const response = await request(`/api/v1/${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code;
    const error = new Error(`${path} returned HTTP ${response.status}`);
    error.status = response.status;
    if (typeof code === 'string' && /^[A-Z0-9_-]{1,80}$/.test(code)) error.code = code;
    throw error;
  }
  return response.json();
}

try {
  const frontend = await request('/');
  assert.equal(frontend.status, 200);
  assert.match(await frontend.text(), /<title>BenchProof<\/title>/);
  evidence.frontend = true;
  phase = 'cold-start';
  if (process.argv.includes('--cold')) {
    process.loadEnvFile(new URL('.env.local', root));
    const state = JSON.parse(await readFile(new URL('.vercel/sandbox-state.json', root), 'utf8'));
    assert.equal(state.verified, true);
    const sandbox = await Sandbox.get({ name: state.name, resume: false });
    if (sandbox.status === 'running') await sandbox.stop();
  }
  const started = Date.now();
  const ready = await json('ready');
  assert.equal(ready.provider.configured, true);
  assert.equal(ready.runner.isolated_execution_available, true);
  assert.equal(ready.worker.alive, true);
  evidence.readinessMs = Date.now() - started;
  evidence.gatewayColdResume = process.argv.includes('--cold');
  phase = 'clean-gate-and-replay';
  const audit = await json('audits', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fixture_id: 'clean-service', mode: 'live' }) });
  const path = `audits/${audit.audit_id}`;
  const gate = await json(`${path}/verify`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  assert.equal(gate.verdict, 'VERIFIED');
  const bundle = await json(`${path}/bundle`, { method: 'POST' });
  assert.equal((await json(`${path}/bundle/validate`, { method: 'POST' })).valid, true);
  const bytes = Buffer.from(await (await request(`/api/v1/${path}/bundle`)).arrayBuffer());
  assert.equal(createHash('sha256').update(bytes).digest('hex'), bundle.sha256);
  const replay = await json(`${path}/replay`, { method: 'POST' });
  assert.equal(replay.replayed_verdict, 'VERIFIED');
  assert.equal(replay.verdict_matches, true);
  assert.equal(replay.checks_matched, true);
  const events = await request(`/api/v1/${path}/events`, { headers: { Accept: 'text/event-stream' } });
  assert.match(events.headers.get('content-type'), /text\/event-stream/);
  assert.match(await events.text(), /data:/);
  evidence.auditId = audit.audit_id;
  evidence.bundleSha256 = bundle.sha256;
  evidence.cleanGate = true;
  evidence.bundleValidation = true;
  evidence.freshReplay = true;
  evidence.sse = true;
  phase = 'access-boundaries';
  for (const suffix of ['', '/bundle']) assert.equal((await request(`/api/v1/${path}${suffix}`, { headers: { 'X-BenchProof-Owner': 'different-public-owner' } })).status, 403);
  for (const filename of ['/.env', '/backend/fixtures/heldout/truth.lock.json', '/deployment/vercel/runtime-package.json']) assert.equal((await request(filename)).status, 404);
  assert.equal((await request('/api/v1/audits', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ padding: 'x'.repeat(65536) }) })).status, 413);
  evidence.accessBoundaries = true;
  phase = 'faulty-candidate-rejected';
  const live = await json('audits', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fixture_id: 'MC-01', mode: 'live' }) });
  const rejected = await json(`audits/${live.audit_id}/verify`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  assert.equal(rejected.verdict, 'REJECTED');
  assert.ok(rejected.failing_checks.includes('amount-boundary'));
  evidence.faultyCandidateRejected = true;
  if (skipProvider) {
    evidence.provider = { status: 'NOT_RUN', reason: '--skip-provider; no model charge in this infrastructure check' };
  } else {
    phase = 'real-nvidia-diagnosis';
    const diagnosis = await json(`audits/${live.audit_id}/diagnose`, { method: 'POST' });
    assert.equal(diagnosis.provider_metadata.mode, 'live');
    assert.equal(diagnosis.provider_metadata.provider, 'nebius-token-factory');
    assert.match(diagnosis.provider_metadata.model_id, /^nvidia\//i);
    assert.ok(diagnosis.provider_metadata.usage.total_tokens > 0);
    assert.ok(diagnosis.hypotheses_evaluation.some(item => item.constraint_id === 'C-AMOUNT' && item.outcome === 'SUPPORTED'));
    evidence.provider = { auditId: live.audit_id, ...diagnosis.provider_metadata, amountHypothesisSupported: true };
  }
  evidence.verified = true;
} catch (error) {
  evidence.failure = { phase, message: error.message, status: error.status, code: error.code };
  process.exitCode = 1;
} finally {
  await mkdir(new URL('artifacts/vercel/', root), { recursive: true });
  const record = `artifacts/vercel/public-check-${Date.now()}.json`;
  await writeFile(new URL(record, root), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify({ ...evidence, record }, null, 2));
}
