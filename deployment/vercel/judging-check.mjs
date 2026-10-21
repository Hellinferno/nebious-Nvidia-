import { fileURLToPath } from 'node:url';
import path from 'node:path';

export const JUDGING_END_EPOCH = Date.parse('2026-12-15T20:00:00Z') / 1000;
export const RULES_URL = 'https://nebiusglobalaihackathon.devpost.com/rules';

export function assessJudgingConfiguration(ready, { observedAtEpoch, deadlineEpoch } = {}) {
  if (!Number.isFinite(observedAtEpoch) || observedAtEpoch <= 0 || observedAtEpoch > 8640000000000) throw new Error('A valid observation time is required');
  const remaining = ready?.coding?.session_seconds_remaining;
  const explicitDeadline = deadlineEpoch !== undefined;
  const deadline = explicitDeadline ? deadlineEpoch : Number.isInteger(remaining) && remaining > 0 ? observedAtEpoch + remaining : null;
  const knownDeadline = Number.isInteger(deadline) && deadline > 0 && deadline <= 8640000000000;
  const blockers = [];
  if (!knownDeadline) blockers.push('ADMISSION_DEADLINE_UNKNOWN');
  else if (deadline < JUDGING_END_EPOCH) blockers.push('ADMISSION_ENDS_BEFORE_JUDGING');
  if (ready?.coding?.enabled !== true || ready?.coding?.admission_configured !== true) blockers.push('CODING_ADMISSION_UNAVAILABLE');
  if (ready?.provider?.configured !== true) blockers.push('PROVIDER_UNCONFIGURED');
  if (ready?.runner?.isolated_execution_available !== true) blockers.push('ISOLATED_RUNNER_UNAVAILABLE');
  if (ready?.coding?.worker_alive !== true) blockers.push('CODING_WORKER_UNAVAILABLE');
  return {
    schema: 'benchproof/judging-configuration-check-v1',
    rules_url: RULES_URL,
    judging_end_utc: new Date(JUDGING_END_EPOCH * 1000).toISOString(),
    observed_at_utc: new Date(observedAtEpoch * 1000).toISOString(),
    admission_deadline_utc: knownDeadline ? new Date(deadline * 1000).toISOString() : null,
    deadline_source: explicitDeadline ? 'operator-supplied' : 'public-relative-estimate',
    configuration_ready: blockers.length === 0,
    blockers,
    hard_model_calls_per_day: ready?.coding?.hard_model_calls_per_day ?? null,
    hard_executions_per_day: ready?.coding?.hard_executions_per_day ?? null,
    inference_calls: 0,
    changes_made: false,
    availability_or_rule_compliance_guaranteed: false,
    remaining_owner_checks: ['Provider balance and hosting capacity', 'Judge access versus shared quotas', 'Public YouTube video URL', 'Rights and eligibility review', 'Actual submitted entry confirmation'],
  };
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length && (args.length !== 2 || args[0] !== '--deadline-epoch')) throw new Error('Usage: node deployment/vercel/judging-check.mjs [--deadline-epoch INTEGER]');
  const deadlineEpoch = args.length ? Number(args[1]) : undefined;
  if (args.length && (!Number.isInteger(deadlineEpoch) || deadlineEpoch <= 0)) throw new Error('Deadline must be a positive Unix timestamp');
  const response = await fetch('https://benchproof.vercel.app/api/v1/ready', { signal: AbortSignal.timeout(100000), redirect: 'error' });
  if (!response.ok) throw new Error(`Public readiness returned HTTP ${response.status}`);
  const serverEpoch = Date.parse(response.headers.get('date')) / 1000;
  const observedAtEpoch = Number.isFinite(serverEpoch) ? serverEpoch : Math.floor(Date.now() / 1000);
  const report = assessJudgingConfiguration(await response.json(), { observedAtEpoch, deadlineEpoch });
  console.log(JSON.stringify(report, null, 2));
  if (!report.configuration_ready) process.exitCode = 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
