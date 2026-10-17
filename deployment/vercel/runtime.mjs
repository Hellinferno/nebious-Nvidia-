import { Sandbox } from '@vercel/sandbox';
import { readFile } from 'node:fs/promises';

export const APP_ROOT = '/vercel/sandbox/benchproof';

export function runtimeUpgrade(current, desired, approvedPrevious) {
  if (!current || current === desired) return false;
  if (!/^[a-f0-9]{64}$/.test(approvedPrevious ?? '') || current !== approvedPrevious) {
    throw new Error('Existing runtime differs; pass --upgrade-from with the reviewed current hash');
  }
  return true;
}

export function runtimeSettings(env = process.env) {
  const name = env.BENCHPROOF_SANDBOX_NAME;
  const hash = env.BENCHPROOF_RUNTIME_HASH;
  const token = env.BENCHPROOF_ORIGIN_TOKEN;
  const user = env.BENCHPROOF_SANDBOX_USER;
  if (!name || !/^[a-z0-9-]{3,80}$/.test(name)) throw new Error('SANDBOX_NOT_CONFIGURED');
  if (!hash || !/^[a-f0-9]{64}$/.test(hash)) throw new Error('RUNTIME_NOT_CONFIGURED');
  if (!token || token.length < 32) throw new Error('ORIGIN_NOT_CONFIGURED');
  if (!user || !/^[a-z_][a-z0-9_-]*$/.test(user)) throw new Error('SANDBOX_USER_NOT_CONFIGURED');
  return { name, hash, token, user };
}

export async function startOrigin(sandbox, settings) {
  const marker = await sandbox.readFileToBuffer({ path: `${APP_ROOT}/runtime-hash` });
  if (marker?.toString().trim() !== settings.hash) throw new Error('RUNTIME_VERSION_MISMATCH');
  const result = await sandbox.runCommand({
    cmd: 'bash',
    args: [`${APP_ROOT}/deployment/vercel/bootstrap.sh`, 'start', APP_ROOT, settings.user],
    sudo: true,
    timeoutMs: 90_000,
  });
  if (result.exitCode !== 0) throw new Error('ORIGIN_START_FAILED');
}

export async function getRuntime(settings = runtimeSettings(), sdk = Sandbox) {
  const lookup = {
    name: settings.name,
    resume: true,
    onResume: instance => startOrigin(instance, settings),
    signal: AbortSignal.timeout(100_000),
  };
  let sandbox = await sdk.get(lookup);
  await startOrigin(sandbox, settings);
  if (sandbox.expiresAt && sandbox.expiresAt.getTime() - Date.now() < 330_000) {
    try {
      await sandbox.extendTimeout(600_000);
    } catch (error) {
      const refreshed = await sdk.get({ ...lookup, signal: AbortSignal.timeout(30_000) });
      if (!refreshed.expiresAt || refreshed.expiresAt.getTime() - Date.now() < 330_000) throw error;
      sandbox = refreshed;
    }
  }
  return { sandbox, origin: sandbox.domain(8765), token: settings.token };
}

export async function readPackage() {
  return JSON.parse(await readFile(new URL('./runtime-package.json', import.meta.url), 'utf8'));
}
