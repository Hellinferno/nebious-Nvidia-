import { presentExecution } from './presentation'
import type { ExecutionPresentationRecord } from './presentation'
import './ExecutionResults.css'

type ExecutionResultsProps = {
  records: readonly ExecutionPresentationRecord[]
}

const STAGE_LABELS: Record<string, string> = {
  BASELINE: 'Before changes',
  CANDIDATE: 'Candidate checks',
  FINAL: 'Fresh final checks',
}

export function ExecutionResults({ records }: ExecutionResultsProps) {
  return (
    <section className="execution-results" aria-label="Recorded check results">
      <p className="execution-results-scope">
        Results cover only the declared checks on the recorded source version. User-supplied project tests are not an independent guarantee of correctness.
      </p>
      {records.length === 0 && (
        <p className="execution-results-empty">No checks have run yet. Review and approve the plan before starting execution.</p>
      )}
      {records.map((action) => {
        const result = presentExecution(action)
        return (
          <article className="execution-result" key={action.action_id}>
            <div className="execution-result-heading">
              <h3>{STAGE_LABELS[action.stage] || action.stage}</h3>
              <span className={`execution-outcome ${result.tone}`}>{result.label}</span>
            </div>
            <p className="execution-result-meta">
              <span>Action: {action.status.replaceAll('_', ' ').toLowerCase()}</span>
              <span>Exit: {result.exitCode === null ? 'not recorded' : result.exitCode}</span>
              <span>{result.durationMs === null ? 'Duration not recorded' : `${result.durationMs.toLocaleString()} ms`}</span>
              <span>{result.isolationReported ? 'Isolation reported by runner' : 'Isolation not reported'}</span>
            </p>
            {result.hasReport ? (
              <>
                <p className="execution-check-counts">
                  <span>{result.passed} passed</span>
                  <span>{result.failed} failed</span>
                  <span>{result.skipped} skipped</span>
                  {result.unknown > 0 && <span>{result.unknown} unknown</span>}
                </p>
                <details className="execution-details" open={result.tone !== 'passed' && result.checks.length > 0}>
                  <summary>Check details ({result.checks.length})</summary>
                  {result.checks.length > 0 ? (
                    <ul className="execution-check-list">
                      {result.checks.map((check, index) => (
                        <li key={`${check.id}-${index}`}>
                          <div className="execution-check-heading">
                            <code>{check.id}</code>
                            <span className={`execution-outcome ${check.outcome}`}>{check.outcome}</span>
                          </div>
                          {check.detail && <p>{check.detail}</p>}
                        </li>
                      ))}
                    </ul>
                  ) : <p>No individual check results were recorded.</p>}
                </details>
                <div className="execution-report-meta">
                  {result.profile && <span>Check profile: <code>{result.profile}</code></span>}
                  {result.sourceHash && <span>Source: <code title={result.sourceHash}>{result.sourceHash.slice(0, 12)}</code></span>}
                </div>
              </>
            ) : (
              <p className="execution-results-empty">A check report is not available for this action yet.</p>
            )}
            {result.timedOut && <p className="execution-warning">Execution reached its time limit. This is not a passing result.</p>}
            {result.error && <p className="execution-warning">Runner: {result.error}</p>}
            <details className="execution-details">
              <summary>Recorded console output</summary>
              <div className="execution-console-group">
                <h4>Standard output</h4>
                <pre tabIndex={0}>{result.stdout || 'No standard output recorded.'}</pre>
                <h4>Standard error</h4>
                <pre tabIndex={0}>{result.stderr || 'No standard error recorded.'}</pre>
              </div>
            </details>
          </article>
        )
      })}
    </section>
  )
}
