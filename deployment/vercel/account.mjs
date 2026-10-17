import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = new URL('../../', import.meta.url);

export function vercel(args, options = {}) {
  return execFileSync(process.execPath, [fileURLToPath(new URL('node_modules/vercel/dist/vc.js', root)), ...args], {
    cwd: fileURLToPath(root),
    encoding: 'utf8',
    env: { ...process.env, VERCEL_TELEMETRY_DISABLED: '1' },
    ...options,
  });
}

export function assertHobby(team, orgId) {
  if (team?.id !== orgId || team?.billing?.plan !== 'hobby') {
    throw new Error('A verified Hobby team is required; paid or unknown plans are refused');
  }
  return { orgId, plan: 'hobby' };
}

export function verifyHobby(orgId) {
  if (!/^team_[A-Za-z0-9]+$/.test(orgId)) throw new Error('A linked Hobby team is required');
  const result = JSON.parse(vercel(['api', `/v2/teams/${encodeURIComponent(orgId)}`]));
  return assertHobby(result.team ?? result, orgId);
}
