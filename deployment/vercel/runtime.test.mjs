import assert from 'node:assert/strict';
import { test } from 'node:test';
import { allowedFile, makePackage } from './build.mjs';
import { getRuntime, runtimeSettings, runtimeUpgrade, startOrigin } from './runtime.mjs';
import { assertHobby } from './account.mjs';

const settings = { name: 'benchproof-runtime-v1', hash: 'a'.repeat(64), user: 'ubuntu', token: 't'.repeat(48) };

test('runtime upgrades require the exact reviewed previous identity', () => {
  const previous = 'b'.repeat(64);
  assert.equal(runtimeUpgrade(undefined, settings.hash), false);
  assert.equal(runtimeUpgrade(settings.hash, settings.hash), false);
  assert.throws(() => runtimeUpgrade(previous, settings.hash), /reviewed current hash/);
  assert.throws(() => runtimeUpgrade(previous, settings.hash, 'c'.repeat(64)), /reviewed current hash/);
  assert.equal(runtimeUpgrade(previous, settings.hash, previous), true);
});

test('provisioning refuses paid, unknown and mismatched account plans', () => {
  for (const team of [{ id: 'team_demo', billing: { plan: 'pro' } }, { id: 'team_demo' }, { id: 'team_other', billing: { plan: 'hobby' } }]) {
    assert.throws(() => assertHobby(team, 'team_demo'), /Hobby/);
  }
  assert.deepEqual(assertHobby({ id: 'team_demo', billing: { plan: 'hobby' } }, 'team_demo'), { orgId: 'team_demo', plan: 'hobby' });
});

test('runtime settings require an explicit name, identity and strong origin token', () => {
  assert.throws(() => runtimeSettings({}), /SANDBOX_NOT_CONFIGURED/);
  assert.deepEqual(runtimeSettings({
    BENCHPROOF_SANDBOX_NAME: settings.name,
    BENCHPROOF_RUNTIME_HASH: settings.hash,
    BENCHPROOF_ORIGIN_TOKEN: settings.token,
    BENCHPROOF_SANDBOX_USER: settings.user,
  }), settings);
});

test('runtime package paths exclude secrets, caches, local state and held-out truth', () => {
  for (const path of ['.env', 'backend/.env', 'backend/fixtures/heldout/truth.lock.json', 'artifacts/audit.db', 'backend/benchproof/../../.env', 'backend/benchproof/__pycache__/main.pyc']) {
    assert.equal(allowedFile(path), false, path);
  }
  assert.equal(allowedFile('backend/fixtures/development/MC-01/expected.json'), true);
  assert.equal(allowedFile('backend/benchproof/api/main.py'), true);
});

test('actual runtime package contains neither held-out assets nor local secrets/state', async () => {
  const runtime = await makePackage();
  assert.match(runtime.hash, /^[a-f0-9]{64}$/);
  assert.ok(runtime.entries.some(entry => entry.path === 'backend/runner/launcher/observe_invoice.py'));
  assert.ok(runtime.entries.every(entry => allowedFile(entry.path)));
  assert.ok(runtime.entries.every(entry => !entry.path.includes('heldout') && !entry.path.endsWith('.db')));
});

test('known runtime is retrieved by name, never created on a public request', async () => {
  const calls = [];
  const instance = {
    readFileToBuffer: async () => Buffer.from(settings.hash),
    runCommand: async params => { calls.push(params); return { exitCode: 0 }; },
    domain: port => { assert.equal(port, 8765); return 'https://origin.vercel.run'; },
  };
  const result = await getRuntime(settings, { get: async params => { assert.equal(params.name, settings.name); return instance; } });
  assert.equal(result.token, settings.token);
  assert.equal(calls.length, 1);
});

test('missing sandbox and changed runtime identity fail before starting code', async () => {
  await assert.rejects(getRuntime(settings, { get: async () => { throw new Error('snapshot missing'); } }), /snapshot missing/);
  await assert.rejects(startOrigin({ readFileToBuffer: async () => Buffer.from('old') }, settings), /RUNTIME_VERSION_MISMATCH/);
});

test('concurrent timeout extensions accept a fresh lifetime confirmed by the control plane', async () => {
  const original = {
    expiresAt: new Date(Date.now() + 240_000),
    readFileToBuffer: async () => Buffer.from(settings.hash),
    runCommand: async () => ({ exitCode: 0 }),
    extendTimeout: async () => { throw new Error('session maximum reached by concurrent extensions'); },
  };
  const refreshed = { expiresAt: new Date(Date.now() + 600_000), domain: () => 'https://origin.vercel.run' };
  let lookups = 0;
  const result = await getRuntime(settings, { get: async () => ++lookups === 1 ? original : refreshed });
  assert.equal(result.sandbox, refreshed);
  assert.equal(lookups, 2);
});

test('a failed timeout extension still refuses work if the current lifetime is insufficient', async () => {
  const instance = {
    expiresAt: new Date(Date.now() + 240_000),
    readFileToBuffer: async () => Buffer.from(settings.hash),
    runCommand: async () => ({ exitCode: 0 }),
    extendTimeout: async () => { throw new Error('session maximum'); },
  };
  await assert.rejects(getRuntime(settings, { get: async () => instance }), /session maximum/);
});
