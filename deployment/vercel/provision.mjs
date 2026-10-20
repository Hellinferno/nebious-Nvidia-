import { APIError, Drive, Sandbox } from '@vercel/sandbox';
import { randomBytes } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { APP_ROOT, readPackage, runtimeUpgrade, startOrigin } from './runtime.mjs';
import { verifyHobby } from './account.mjs';
import { mcpConfig } from './mcp-config.mjs';

const root = new URL('../../', import.meta.url);
for (const filename of ['.env', '.env.local']) {
  const filepath = new URL(filename, root);
  if (existsSync(filepath)) process.loadEnvFile(filepath);
}
const metadata = JSON.parse(await readFile(new URL('.vercel/project.json', root), 'utf8'));
const account = verifyHobby(metadata.orgId);
if (!process.env.VERCEL_OIDC_TOKEN) throw new Error('Run vercel env pull .env.local first');
if (!process.env.NEBIUS_API_KEY || !process.env.NEBIUS_MODEL_ID) throw new Error('Nebius settings missing');
const mcp = mcpConfig();
const runtime = await readPackage();
const stateFile = new URL('.vercel/sandbox-state.json', root);
const secretsFile = new URL('.vercel/runtime-secrets.json', root);
const name = 'benchproof-runtime-v1';
const upgradeIndex = process.argv.indexOf('--upgrade-from');
const approvedPrevious = upgradeIndex < 0 ? undefined : process.argv[upgradeIndex + 1];
let secrets;
if (existsSync(secretsFile)) secrets = JSON.parse(await readFile(secretsFile, 'utf8'));
else {
  secrets = { originToken: randomBytes(48).toString('hex') };
  await mkdir(new URL('.vercel/', root), { recursive: true });
  await writeFile(secretsFile, JSON.stringify(secrets), { flag: 'wx', mode: 0o600 });
}

let sandbox;
try {
  sandbox = await Sandbox.get({ name, resume: true });
} catch (error) {
  if (!(error instanceof APIError) || error.response.status !== 404) throw error;
  if (existsSync(stateFile)) throw new Error('Known sandbox missing; restore recorded state instead of recreating it');
  const drive = await Drive.getOrCreate({ name: 'benchproof-state-v1', region: 'iad1', maxSize: 1024 * 1024 * 1024 });
  sandbox = await Sandbox.create({
    name,
    image: 'vercel/sandbox/universal:latest',
    ports: [8765],
    timeout: 600_000,
    resources: { vcpus: 1 },
    persistent: true,
    snapshotExpiration: 0,
    keepLastSnapshots: { count: 2, expiration: 0 },
    mounts: { '/data': drive },
    tags: { application: 'benchproof', purpose: 'demo' },
  });
}

const marker = await sandbox.readFileToBuffer({ path: `${APP_ROOT}/runtime-hash` });
const upgrade = runtimeUpgrade(marker?.toString().trim(), runtime.hash, approvedPrevious);
if (upgrade) {
  await sandbox.stop();
  sandbox = await Sandbox.get({ name, resume: true });
  const resumedMarker = await sandbox.readFileToBuffer({ path: `${APP_ROOT}/runtime-hash` });
  if (resumedMarker?.toString().trim() !== approvedPrevious) throw new Error('Runtime changed during upgrade; stopped without replacing files');
}
if (sandbox.expiresAt && sandbox.expiresAt.getTime() - Date.now() < 420_000) await sandbox.extendTimeout(600_000);
const who = await sandbox.runCommand('id', ['-un']);
const user = (await who.stdout()).trim();
if (!/^[a-z_][a-z0-9_-]*$/.test(user)) throw new Error('Unexpected sandbox user');
const codingDeadline = Number(process.env.BENCHPROOF_CODING_DEADLINE_EPOCH ?? 0);
const coding = {
  enabled: codingDeadline > 0,
  model_calls_per_day: Number(process.env.BENCHPROOF_CODING_MODEL_CALLS_PER_DAY ?? 40),
  executions_per_day: Number(process.env.BENCHPROOF_CODING_EXECUTIONS_PER_DAY ?? 60),
  deadline_epoch: codingDeadline,
  output_tokens: Number(process.env.BENCHPROOF_CODING_OUTPUT_TOKENS ?? 2048),
};
if (coding.enabled) {
  if (!Number.isFinite(codingDeadline) || codingDeadline * 1000 - Date.now() < 3_600_000) {
    throw new Error('BENCHPROOF_CODING_DEADLINE_EPOCH must be at least one hour in the future');
  }
  for (const key of ['model_calls_per_day', 'executions_per_day', 'output_tokens']) {
    if (!Number.isInteger(coding[key]) || coding[key] <= 0) throw new Error(`Invalid coding ${key}`);
  }
}
await sandbox.writeFiles([
  ...runtime.entries.map(entry => ({ path: `${APP_ROOT}/${entry.path}`, content: Buffer.from(entry.content, 'base64') })),
  { path: `${APP_ROOT}/origin-config.json`, mode: 0o600, content: JSON.stringify({
    origin_token: secrets.originToken,
    nebius_api_key: process.env.NEBIUS_API_KEY,
    model_id: process.env.NEBIUS_MODEL_ID,
    daily_actions: 60,
    coding,
    mcp,
  }) },
]);
if (!marker || upgrade) {
  const setup = await sandbox.runCommand({
    cmd: 'bash', args: [`${APP_ROOT}/deployment/vercel/bootstrap.sh`, 'prepare', APP_ROOT, user],
    sudo: true, timeoutMs: 300_000,
  });
  if (setup.exitCode !== 0) {
    console.error((await setup.stderr()).slice(-3000));
    throw new Error('Sandbox setup failed; the sandbox is retained for inspection');
  }
  await sandbox.writeFiles([{ path: `${APP_ROOT}/runtime-hash`, content: runtime.hash }]);
}
const settings = { name, hash: runtime.hash, token: secrets.originToken, user };
await startOrigin(sandbox, settings);
const state = {
  schema: 'benchproof/vercel-deployment-v1',
  projectId: metadata.projectId,
  orgId: metadata.orgId,
  account,
  name,
  user,
  runtimeHash: runtime.hash,
  origin: sandbox.domain(8765),
  verified: false,
};
await writeFile(stateFile, JSON.stringify(state, null, 2), { mode: 0o600 });
console.log(JSON.stringify({ ...state, next: 'Run node deployment/vercel/verify.mjs before deploying the gateway' }, null, 2));
