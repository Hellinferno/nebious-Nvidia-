import { readFile } from 'node:fs/promises';
import { readPackage } from './runtime.mjs';
import { vercel, verifyHobby } from './account.mjs';

const root = new URL('../../', import.meta.url);
const state = JSON.parse(await readFile(new URL('.vercel/sandbox-state.json', root), 'utf8'));
const metadata = JSON.parse(await readFile(new URL('.vercel/project.json', root), 'utf8'));
if (metadata.projectId !== state.projectId || metadata.orgId !== state.orgId) throw new Error('Linked project changed');
verifyHobby(state.orgId);
if (!state.verified || !state.verificationRecord) throw new Error('Cloud stop/resume verification must pass before deployment');
if ((await readPackage()).hash !== state.runtimeHash) throw new Error('Rebuilt runtime differs from verified cloud runtime');
const secrets = JSON.parse(await readFile(new URL('.vercel/runtime-secrets.json', root), 'utf8'));
const values = {
  BENCHPROOF_SANDBOX_NAME: state.name,
  BENCHPROOF_RUNTIME_HASH: state.runtimeHash,
  BENCHPROOF_SANDBOX_USER: state.user,
  BENCHPROOF_ORIGIN_TOKEN: secrets.originToken,
};
for (const [name, value] of Object.entries(values)) {
  vercel(['env', 'add', name, 'production', '--force', '--sensitive'], { input: value, stdio: ['pipe', 'pipe', 'inherit'] });
  console.log(`Configured ${name}`);
}
vercel(['deploy', '--prod', '--yes'], { stdio: 'inherit' });
