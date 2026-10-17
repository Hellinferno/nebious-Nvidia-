import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { APP_ROOT, getRuntime } from './runtime.mjs';
import { verifyHobby } from './account.mjs';

const root = new URL('../../', import.meta.url);
const envFile = new URL('.env.local', root);
if (existsSync(envFile)) process.loadEnvFile(envFile);
const stateFile = new URL('.vercel/sandbox-state.json', root);
const state = JSON.parse(await readFile(stateFile, 'utf8'));
verifyHobby(state.orgId);
const secrets = JSON.parse(await readFile(new URL('.vercel/runtime-secrets.json', root), 'utf8'));
const settings = { name: state.name, hash: state.runtimeHash, user: state.user, token: secrets.originToken };
let runtime = await getRuntime(settings);
const evidence = { schema: 'benchproof/vercel-verification-v1', timestamp: new Date().toISOString(), runtimeHash: state.runtimeHash };
const headers = { 'X-BenchProof-Origin': secrets.originToken, 'X-BenchProof-Owner': `cloud-check-${randomBytes(6).toString('hex')}` };

async function call(path, options = {}) {
  const response = await fetch(new URL(`/api/v1/${path}`, runtime.origin), {
    ...options,
    headers: { ...headers, ...options.headers },
    signal: AbortSignal.timeout(150_000),
    redirect: 'error',
  });
  assert.ok(response.ok, `Cloud check ${path} returned HTTP ${response.status}`);
  return response;
}

async function command(options) {
  const result = await runtime.sandbox.runCommand(options);
  assert.equal(result.exitCode, 0, `Cloud command failed: ${options.cmd}`);
  return (await result.stdout()).trim();
}

const denied = await fetch(new URL('/api/v1/ready', runtime.origin), { signal: AbortSignal.timeout(30_000) });
assert.equal(denied.status, 403);
evidence.originDenied = true;
const ready = await (await call('ready')).json();
assert.equal(ready.runner.isolated_execution_available, true);
assert.equal(ready.provider.configured, true);
assert.equal(ready.worker.alive, true);
evidence.ready = true;

await command({ cmd: `${APP_ROOT}/.venv/bin/python`, args: [`${APP_ROOT}/backend/scripts/runner_preflight.py`, '--skip-contree'], timeoutMs: 150_000 });
const preflight = JSON.parse(await command({
  cmd: `${APP_ROOT}/.venv/bin/python`,
  args: ['-c', `import json,pathlib; files=sorted(pathlib.Path('${APP_ROOT}/artifacts/runner').glob('runner_*.json')); print(files[-1].read_text())`],
}));
assert.equal(preflight.docker.status, 'OK');
for (const check of ['internet_denied_all', 'metadata_denied_all', 'no_secret_env_all', 'no_trusted_assets_all', 'candidate_read_only_all']) {
  assert.equal(preflight.docker.isolation_summary[check], true, check);
}
assert.equal(preflight.docker.timeout_negative.ok, true);
evidence.runner = preflight.docker;

const resourceScript = `
import json, subprocess, uuid
name = 'bp-memory-check-' + uuid.uuid4().hex[:12]
def docker(*arguments):
    return subprocess.run(['docker', *arguments], capture_output=True, text=True, timeout=40)
try:
    created = docker('create', '--name', name, '--network', 'none', '--read-only', '--memory', '256m', '--memory-swap', '256m', '--pids-limit', '64', '--cpus', '1', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '65534:65534', 'benchproof-candidate:dev', 'env', '-i', 'PATH=/usr/local/bin:/usr/bin:/bin', 'python', '-c', 'bytearray(768 * 1024 * 1024)')
    assert created.returncode == 0, 'resource-check container creation failed'
    docker('start', '--attach', name)
    inspected = docker('inspect', name)
    assert inspected.returncode == 0, 'resource-check inspection failed'
    container = json.loads(inspected.stdout)[0]
    settings = container['HostConfig']
    assert settings['Memory'] == 256 * 1024 * 1024
    assert settings['MemorySwap'] == settings['Memory']
    assert settings['NanoCpus'] == 1000000000
    assert settings['PidsLimit'] == 64
    assert container['State']['OOMKilled'] is True
    assert container['State']['ExitCode'] == 137
    print(json.dumps({'memoryBytes': settings['Memory'], 'swapBytes': settings['MemorySwap'], 'nanoCpus': settings['NanoCpus'], 'pids': settings['PidsLimit'], 'oomKilled': True, 'exitCode': 137}))
finally:
    docker('rm', '--force', name)
`;
evidence.resources = JSON.parse(await command({ cmd: `${APP_ROOT}/.venv/bin/python`, args: ['-c', resourceScript], timeoutMs: 60_000 }));

const audit = await (await call('audits', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fixture_id: 'clean-service', mode: 'live' }) })).json();
const path = `audits/${audit.audit_id}`;
const gate = await (await call(`${path}/verify`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).json();
assert.equal(gate.gate_verdict ?? gate.verdict, 'VERIFIED');
const bundle = await (await call(`${path}/bundle`, { method: 'POST' })).json();
assert.equal((await (await call(`${path}/bundle/validate`, { method: 'POST' })).json()).valid, true);
const bundleBytes = Buffer.from(await (await call(`${path}/bundle`)).arrayBuffer());
assert.equal(createHash('sha256').update(bundleBytes).digest('hex'), bundle.sha256);
const replay = await (await call(`${path}/replay`, { method: 'POST' })).json();
assert.equal(replay.replayed_verdict, 'VERIFIED');
assert.equal(replay.verdict_matches, true);
assert.equal(replay.checks_matched, true);
const events = await call(`${path}/events`, { headers: { Accept: 'text/event-stream' } });
assert.match(events.headers.get('content-type'), /text\/event-stream/);
assert.match(await events.text(), /data:/);
const intruder = await fetch(new URL(`/api/v1/${path}`, runtime.origin), { headers: { ...headers, 'X-BenchProof-Owner': 'other-cloud-check' }, signal: AbortSignal.timeout(30_000) });
assert.equal(intruder.status, 403);

const limitQuery = { cmd: `${APP_ROOT}/.venv/bin/python`, args: ['-c', "import json,sqlite3; print(json.dumps(sqlite3.connect('/data/benchproof/limits.db').execute('select day,used from demo_actions order by day').fetchall()))"] };
const limitsBefore = await command(limitQuery);
await runtime.sandbox.stop();
runtime = await getRuntime(settings);
assert.equal((await (await call(path)).json()).audit_id, audit.audit_id);
assert.equal((await (await call(`${path}/bundle?metadata=true`)).json()).sha256, bundle.sha256);
assert.equal(await command(limitQuery), limitsBefore);
assert.equal((await (await call('ready')).json()).worker.alive, true);
const resumedReplay = await (await call(`${path}/replay`, { method: 'POST' })).json();
assert.equal(resumedReplay.replayed_verdict, 'VERIFIED');
assert.equal(resumedReplay.checks_matched, true);
assert.equal(resumedReplay.verdict_matches, true);
evidence.auditId = audit.audit_id;
evidence.bundleSha256 = bundle.sha256;
evidence.stopResume = { audit: true, bundle: true, actionLimits: true, worker: true, freshExecution: true };
evidence.gatewayVerified = false;
evidence.providerCallVerified = false;
evidence.verified = true;
await mkdir(new URL('artifacts/vercel/', root), { recursive: true });
const record = `artifacts/vercel/cloud-check-${Date.now()}.json`;
await writeFile(new URL(record, root), JSON.stringify(evidence, null, 2));
await writeFile(stateFile, JSON.stringify({ ...state, verified: true, verificationRecord: record }, null, 2), { mode: 0o600 });
console.log(JSON.stringify({ verified: true, record, auditId: audit.audit_id, next: 'Deploy gateway, then verify the public URL and one bounded model call' }, null, 2));
