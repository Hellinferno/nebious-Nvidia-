import assert from 'node:assert/strict';
import { test } from 'node:test';
import { assessJudgingConfiguration, JUDGING_END_EPOCH } from './judging-check.mjs';

const observedAtEpoch = Date.parse('2026-10-21T14:00:00Z') / 1000;
const ready = {
  coding: { enabled: true, admission_configured: true, worker_alive: true, session_seconds_remaining: JUDGING_END_EPOCH - observedAtEpoch + 86400, hard_model_calls_per_day: 8, hard_executions_per_day: 12 },
  provider: { configured: true },
  runner: { isolated_execution_available: true },
};

test('judging check catches the November deadline despite current successful readiness', () => {
  const report = assessJudgingConfiguration(ready, { observedAtEpoch, deadlineEpoch: 1796063340 });
  assert.equal(report.configuration_ready, false);
  assert.deepEqual(report.blockers, ['ADMISSION_ENDS_BEFORE_JUDGING']);
  assert.equal(report.admission_deadline_utc, '2026-11-30T18:29:00.000Z');
});

test('a covered judging window is configuration readiness, never a hosting or compliance guarantee', () => {
  const report = assessJudgingConfiguration(ready, { observedAtEpoch });
  assert.equal(report.configuration_ready, true);
  assert.equal(report.deadline_source, 'public-relative-estimate');
  assert.equal(report.availability_or_rule_compliance_guaranteed, false);
  assert.equal(report.inference_calls, 0);
  assert.equal(report.changes_made, false);
  assert.ok(report.remaining_owner_checks.includes('Judge access versus shared quotas'));
});

test('missing malformed or nonpositive deadline evidence fails closed', () => {
  for (const remaining of [undefined, -1, 0, Infinity, NaN, '300', 1e20]) {
    const report = assessJudgingConfiguration({ ...ready, coding: { ...ready.coding, session_seconds_remaining: remaining } }, { observedAtEpoch });
    assert.equal(report.configuration_ready, false);
    assert.ok(report.blockers.includes('ADMISSION_DEADLINE_UNKNOWN'));
  }
});

test('current provider runner worker and admission failures remain distinct', () => {
  const report = assessJudgingConfiguration({}, { observedAtEpoch, deadlineEpoch: JUDGING_END_EPOCH + 1 });
  assert.deepEqual(report.blockers, ['CODING_ADMISSION_UNAVAILABLE', 'PROVIDER_UNCONFIGURED', 'ISOLATED_RUNNER_UNAVAILABLE', 'CODING_WORKER_UNAVAILABLE']);
});

test('operator-supplied deadline cannot silently fall back to a later public estimate', () => {
  const report = assessJudgingConfiguration(ready, { observedAtEpoch, deadlineEpoch: 0 });
  assert.equal(report.configuration_ready, false);
  assert.equal(report.deadline_source, 'operator-supplied');
  assert.equal(report.admission_deadline_utc, null);
});

test('judging check refuses unknown clocks and uses the verified Pacific-standard-time end', () => {
  assert.throws(() => assessJudgingConfiguration(ready), /observation time/);
  assert.throws(() => assessJudgingConfiguration(ready, { observedAtEpoch: Infinity }), /observation time/);
  assert.throws(() => assessJudgingConfiguration(ready, { observedAtEpoch: 1e20 }), /observation time/);
  assert.equal(new Date(JUDGING_END_EPOCH * 1000).toISOString(), '2026-12-15T20:00:00.000Z');
});
