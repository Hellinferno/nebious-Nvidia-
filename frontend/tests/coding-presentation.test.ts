import assert from 'node:assert/strict'
import test from 'node:test'
import { formatTimestamp, presentExecution, taskResultMessage } from '../src/components/coding/presentation.ts'
import { instructionStorageKey, readSavedInstructions, TASK_RECIPES } from '../src/components/coding/taskRecipes.ts'
import { sameReviewedPlan } from '../src/components/coding/planReview.ts'
import type { CodingPlan } from '../src/components/coding/types.ts'

function action(checks: unknown[], execution: Record<string, unknown> = {}) {
  return {
    action_id: 'execution-test',
    stage: 'CANDIDATE',
    status: 'COMPLETED',
    result: {
      report: {
        verdict: 'VERIFIED',
        checks,
        execution: { exit_code: 0, stdout: 'test output', stderr: 'test diagnostic', duration_ms: 25, ...execution },
      },
    },
  }
}

test('recorded check reports retain separate console streams and scoped passing label', () => {
  const result = presentExecution(action([{ check_id: 'check-one', status: 'PASSED', detail: 'Observed expected output' }]))
  assert.equal(result.tone, 'passed')
  assert.equal(result.label, 'Declared checks passed')
  assert.equal(result.stdout, 'test output')
  assert.equal(result.stderr, 'test diagnostic')
  assert.equal(result.durationMs, 25)
  assert.equal(result.isolationReported, false)
})

test('skipped, unknown, empty and failed checks cannot be presented as passing', () => {
  for (const checks of [
    [{ check_id: 'skipped', status: 'SKIPPED', passed: true }],
    [{ check_id: 'unknown', outcome: 'UNKNOWN', passed: true }],
    [{ check_id: 'failed', outcome: 'FAIL', reason: 'Assertion failed' }],
    [],
  ]) {
    assert.notEqual(presentExecution(action(checks)).tone, 'passed')
  }
})

test('timeout, runner error and nonzero exit override an optimistic report verdict', () => {
  for (const execution of [{ timed_out: true }, { error: 'Runner unavailable' }, { exit_code: 1 }]) {
    const result = presentExecution(action([{ check_id: 'check-one', outcome: 'PASS' }], execution))
    assert.notEqual(result.tone, 'passed')
  }
})

test('missing execution evidence is not presented as a successful run', () => {
  const result = presentExecution({ action_id: 'pending', stage: 'BASELINE', status: 'RUNNING' })
  assert.equal(result.label, 'In progress')
  assert.equal(result.hasReport, false)
  assert.notEqual(result.tone, 'passed')
})

test('API Unix-second timestamps are converted correctly', () => {
  const timestamp = 1_792_242_000
  assert.equal(formatTimestamp(timestamp), new Date(timestamp * 1000).toLocaleString())
  assert.equal(formatTimestamp(String(timestamp)), formatTimestamp(timestamp))
  assert.equal(formatTimestamp(timestamp * 1000), formatTimestamp(timestamp))
  assert.equal(formatTimestamp(undefined), 'Not recorded')
  assert.equal(formatTimestamp('invalid'), 'Not recorded')
})

test('recipes expose supported workflows without changing user task text', () => {
  assert.deepEqual(TASK_RECIPES.map((recipe) => recipe.id), ['bugfix', 'feature', 'refactor', 'custom'])
  assert.ok(TASK_RECIPES.every((recipe) => recipe.label && recipe.description))
})

test('saved instructions are owner-scoped, bounded and resilient to storage errors', () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  try {
    const saved = new Map([[instructionStorageKey('owner-one'), 'Preserve public signatures.']])
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { getItem: (key: string) => saved.get(key) ?? null } })
    assert.equal(readSavedInstructions('owner-one'), 'Preserve public signatures.')
    assert.equal(readSavedInstructions('owner-two'), null)
    saved.set(instructionStorageKey('owner-one'), 'a'.repeat(2001))
    assert.equal(readSavedInstructions('owner-one'), null)
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, get() { throw new Error('Storage unavailable') } })
    assert.equal(readSavedInstructions('owner-one'), null)
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous)
    else Reflect.deleteProperty(globalThis, 'localStorage')
  }
})

test('approval comparison rejects unseen plan changes regardless of object key order', () => {
  const plan: CodingPlan = {
    schema_version: 'coding-plan-v1', source_hash: 'a'.repeat(64), brief_hash: 'b'.repeat(64),
    steps: ['Preserve public behavior'], target_files: ['app/service.py'], check_profile: 'project-unittest-v1',
  }
  assert.equal(sameReviewedPlan(plan, { ...plan }), true)
  assert.equal(sameReviewedPlan(plan, null), false)
  assert.equal(sameReviewedPlan(plan, { ...plan, steps: ['An unseen replacement step'] }), false)
  assert.equal(sameReviewedPlan(plan, { ...plan, target_files: ['app/other.py'] }), false)
  assert.equal(sameReviewedPlan(plan, { ...plan, brief_hash: 'c'.repeat(64) }), false)
  assert.equal(sameReviewedPlan(plan, { ...plan, check_profile: 'invoice-observation-v1' }), false)
})

test('task stop reasons explain recovery without overstating check coverage', () => {
  assert.match(taskResultMessage({ code: 'BASELINE_ALREADY_PASSES' }) || '', /Add a feature or Refactor/)
  assert.match(taskResultMessage({ code: 'CHECKS_PASSED' }) || '', /requirements those checks do not cover/)
  assert.match(taskResultMessage({ code: 'MODEL_OUTPUT_TRUNCATED' }) || '', /No automatic paid retry/)
  assert.equal(taskResultMessage({ code: 'FUTURE_CODE', message: 'Recorded explanation' }), 'Recorded explanation')
  assert.equal(taskResultMessage(null), null)
})
