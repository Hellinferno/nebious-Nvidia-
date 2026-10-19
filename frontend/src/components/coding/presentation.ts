type JsonRecord = Record<string, unknown>

export type ExecutionPresentationRecord = {
  action_id: string
  stage: string
  status: string
  result?: unknown
  details?: unknown
}

export type PresentedCheck = {
  id: string
  outcome: 'passed' | 'failed' | 'skipped' | 'unknown'
  detail: string
}

function record(value: unknown): JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as JsonRecord
    : {}
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function presentCheck(value: unknown, index: number): PresentedCheck {
  const check = record(value)
  const status = text(check.outcome || check.status).toUpperCase()
  const outcome = ['SKIP', 'SKIPPED'].includes(status)
    ? 'skipped'
    : ['PASS', 'PASSED'].includes(status)
      ? 'passed'
      : ['FAIL', 'FAILED', 'ERROR'].includes(status)
        ? 'failed'
        : 'unknown'
  return {
    id: text(check.check_id) || `Check ${index + 1}`,
    outcome,
    detail: text(check.reason || check.detail),
  }
}

export function presentExecution(action: ExecutionPresentationRecord) {
  const result = record(action.result)
  const report = record(result.report)
  const execution = record(report.execution)
  const checks = Array.isArray(report.checks) ? report.checks.map(presentCheck) : []
  const verdict = text(report.verdict).toUpperCase()
  const failed = checks.filter((check) => check.outcome === 'failed').length
  const passed = checks.filter((check) => check.outcome === 'passed').length
  const skipped = checks.filter((check) => check.outcome === 'skipped').length
  const unknown = checks.filter((check) => check.outcome === 'unknown').length
  const completeChecks = checks.length > 0 && passed === checks.length
  const executionError = text(execution.error)
  const executionFailed = execution.timed_out === true || executionError.length > 0
    || (typeof execution.exit_code === 'number' && execution.exit_code !== 0)
  const inProgress = ['RESERVED', 'RUNNING'].includes(action.status)
  const tone = executionFailed || verdict === 'INCONCLUSIVE'
    ? 'unknown'
    : failed > 0 || verdict === 'REJECTED'
      ? 'failed'
      : verdict === 'VERIFIED' && completeChecks
        ? 'passed'
        : 'unknown'
  const label = inProgress
    ? 'In progress'
    : tone === 'passed'
      ? 'Declared checks passed'
      : tone === 'failed'
        ? 'Checks failed'
        : skipped > 0 && failed === 0
          ? 'Incomplete — checks skipped'
          : 'Result inconclusive'
  return {
    checks,
    verdict,
    tone,
    label,
    passed,
    failed,
    skipped,
    unknown,
    stdout: text(execution.stdout),
    stderr: text(execution.stderr),
    error: executionError,
    timedOut: execution.timed_out === true,
    exitCode: typeof execution.exit_code === 'number' ? execution.exit_code : null,
    durationMs: typeof execution.duration_ms === 'number' ? execution.duration_ms : null,
    isolationReported: record(execution.isolation).enforced === true,
    profile: text(report.profile),
    sourceHash: text(report.source_hash),
    hasReport: Object.keys(report).length > 0,
  }
}

export function formatTimestamp(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return 'Not recorded'
  const numeric = typeof value === 'number'
    ? value
    : /^\d+(\.\d+)?$/.test(value) ? Number(value) : null
  const date = numeric === null
    ? new Date(value)
    : new Date(Math.abs(numeric) < 1_000_000_000_000 ? numeric * 1000 : numeric)
  return Number.isNaN(date.getTime()) ? 'Not recorded' : date.toLocaleString()
}

export function taskResultMessage(result: { code?: string; message?: string; summary?: string; stop_reason?: string } | null): string | null {
  if (!result) return null
  const messages: Record<string, string> = {
    BASELINE_ALREADY_PASSES: 'The starting code already passes its checks. For changes that begin with passing tests, choose Add a feature or Refactor in a new task.',
    CHECKS_PASSED: 'The declared checks passed on the final candidate. Review the patch and any requirements those checks do not cover.',
    CHECKS_INCONCLUSIVE: 'The runner could not establish a complete check result. Review the recorded output; this is not a passing result.',
    FRESH_CHECK_FAILED: 'Fresh final checks failed. Review the recorded failure before accepting any changes.',
    PATCH_ATTEMPT_LIMIT: 'The task reached its edit-attempt limit. Your partial changes and check results remain available for review.',
    SOURCE_LIMIT: 'The selected source and instructions exceed the model context allowance. Narrow the file scope or instructions in a new task.',
    MODEL_OUTPUT_TRUNCATED: 'The model response reached its output limit and was not accepted as a valid edit. No automatic paid retry was made.',
    BUDGET_EXHAUSTED: 'The task reached a resource limit. Review its usage and partial results; starting over does not refund consumed usage.',
    SESSION_WINDOW_INSUFFICIENT: 'The cloud session does not have enough time left for this task. No further work can start in this session.',
  }
  return messages[result.code || ''] || result.message || result.summary || result.stop_reason
    || (result.code ? result.code.replaceAll('_', ' ').toLowerCase() : null)
}
