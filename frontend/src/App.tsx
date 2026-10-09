import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

type Health = { status: string; version: string; runner: string }
type Ready = {
  status: string
  database: boolean
  contract_hash: string
  provider: { name: string; configured: boolean; model_id: string | null }
  runner: { mode: string; isolated_execution_available: boolean }
  worker: { alive: boolean; heartbeat: { worker_id: string; age_s: number } | null }
  fixtures: number
}
type Example = {
  id: string
  family: string
  constraint: string | null
  defect: string | null
  source_hash: string
  synthetic: boolean
}
type Constraint = {
  constraint_id: string
  version: number
  statement: string
  required: boolean
  protected_check_ids: string[]
  hash: string
}
type GraphData = {
  graph_id: string
  graph_hash: string
  source_hash?: string
  coverage: { status: string; total_files: number; total_symbols: number; total_edges: number }
  nodes: string[]
  edges: { from_node: string; to_node: string; edge_type: string; provenance: string }[]
}

type ImpactData = {
  changed_symbols: string[]
  impacted_symbols: string[]
  impacted_contracts: string[]
  selected_checks: string[]
  risk_severity: string
  risk_reasons: string[]
  coverage_status: string
}
type DiagnosisData = {
  action_id: string
  risk_severity: string
  risk_reasons: string[]
  proposal: {
    hypotheses: {
      hypothesis_id: string
      constraint_id: string
      source_location: string
      claim: string
      refutation_condition: string
      proposed_probe: string
    }[]
    selected_probe: string
  }
  probe_result: {
    probe_name: string
    elapsed_ms: number
    gate_verdict: string
    failed_checks: string[]
  }
  hypotheses_evaluation: {
    hypothesis_id: string
    constraint_id: string
    claim: string
    outcome: string
    detail: string
  }[]
  provider_metadata: {
    mode: string
    provider: string
    model_id?: string
    usage?: { total_tokens?: number }
    elapsed_ms?: number
  }
}

interface BundleInfo {
  name: string
  path: string
  sha256: string
  byteSize: number
  verdict: string
}

interface ValidationResult {
  valid: boolean
  total_files: number
  verified_files: number
  discrepancies: string[]
}

interface ReplayResult {
  replay_id: string
  replayed_verdict: string
  original_verdict: string
  verdict_matches: boolean
  checks_matched: boolean
  tampered: boolean
  check_comparisons: Array<{
    check_id: string
    original_outcome: string
    replayed_outcome: string
    match: boolean
  }>
}

function short(hash: string) {
  return hash.slice(0, 12)
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [ready, setReady] = useState<Ready | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [constraints, setConstraints] = useState<Constraint[]>([])
  const [error, setError] = useState<string | null>(null)

  // Interactive audit & inspection state
  const [selectedFixture, setSelectedFixture] = useState<string>('MC-01')
  const [activeAuditId, setActiveAuditId] = useState<string | null>(null)
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [impact, setImpact] = useState<ImpactData | null>(null)
  const [diagnosis, setDiagnosis] = useState<DiagnosisData | null>(null)
  const [activePatch, setActivePatch] = useState<any | null>(null)
  const [gateResult, setGateResult] = useState<any | null>(null)
  const [bundleInfo, setBundleInfo] = useState<BundleInfo | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [replayResult, setReplayResult] = useState<ReplayResult | null>(null)
  const [actionLoading, setActionLoading] = useState<boolean>(false)
  const [actionError, setActionError] = useState<string | null>(null)


  useEffect(() => {
    Promise.all([
      axios.get<Health>(`${API_BASE}/api/v1/health`),
      axios.get<Ready>(`${API_BASE}/api/v1/ready`),
      axios.get<Example[]>(`${API_BASE}/api/v1/examples`),
      axios.get<Constraint[]>(`${API_BASE}/api/v1/constraints`),
    ])
      .then(([h, r, e, c]) => {
        setHealth(h.data)
        setReady(r.data)
        setExamples(e.data)
        setConstraints(c.data)
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  const mode = ready
    ? ready.provider.configured
      ? 'live provider configured'
      : 'mock — no provider credentials'
    : 'unknown'

  const CANONICAL_DIFFS: Record<string, { diff: string; targetFiles: string[]; explanation: string }> = {
    'MC-01': {
      diff: `--- a/app/money.py\n+++ b/app/money.py\n@@ -4,12 +4,6 @@\ndef compute_total(lines: List[str]) -> str:\n-    """Faulty: premature rounding of each line."""\n+    """Sum unrounded line amounts, then ROUND_HALF_UP once on the invoice total."""\n     if not lines:\n         return "0.00"\n-    total = Decimal("0")\n-    for line in lines:\n-        val = Decimal(line).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)\n-        total += val\n+    total = sum((Decimal(line) for line in lines), Decimal("0"))\n     return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))`,
      targetFiles: ['app/money.py'],
      explanation: 'Sum unrounded items before single ROUND_HALF_UP on total',
    },

    'AC-01': {
      diff: `--- a/app/schemas.py\n+++ b/app/schemas.py\n@@ -13,3 +13,2 @@\n-    amount: str\n+    total_amount: str\n+    status: str\n--- a/app/services.py\n+++ b/app/services.py\n@@ -24,2 +24,2 @@\n-        "amount": total,\n+        "total_amount": total,\n+        "status": "processed"`,
      targetFiles: ['app/schemas.py', 'app/services.py'],
      explanation: 'Restore total_amount and status fields in ReceiptResponse',
    },
  }

  // Handle audit creation & inspection
  const handleInspectFixture = async (fixtureId: string) => {
    setSelectedFixture(fixtureId)
    setActionLoading(true)
    setActionError(null)
    setDiagnosis(null)
    setActivePatch(null)
    setGateResult(null)
    setBundleInfo(null)
    setValidationResult(null)
    setReplayResult(null)
    try {
      // 1. Create audit
      const auditRes = await axios.post(`${API_BASE}/api/v1/audits`, {
        fixture_id: fixtureId,
        mode: ready?.provider.configured ? 'live' : 'mock',
      })
      const auditId = auditRes.data.audit_id
      setActiveAuditId(auditId)

      // 2. Load Graph & Impact in parallel
      const [gRes, impRes] = await Promise.all([
        axios.get(`${API_BASE}/api/v1/audits/${auditId}/graph`),
        axios.get(`${API_BASE}/api/v1/audits/${auditId}/impact`),
      ])
      setGraph(gRes.data.graph ?? gRes.data)
      setImpact(impRes.data)
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || err.message)
    } finally {
      setActionLoading(false)
    }
  }

  // Handle running NVIDIA investigation & probe
  const handleRunInvestigation = async () => {
    if (!activeAuditId) return
    setActionLoading(true)
    setActionError(null)
    try {
      const res = await axios.post(`${API_BASE}/api/v1/audits/${activeAuditId}/diagnose`)
      setDiagnosis(res.data)
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || err.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleProposePatch = async () => {
    if (!activeAuditId || !selectedFixture || !graph) return
    const plan = CANONICAL_DIFFS[selectedFixture]
    if (!plan) {
      setActionError(`No canonical repair diff configured for ${selectedFixture}`)
      return
    }
    setActionLoading(true)
    setActionError(null)
    try {
      const res = await axios.post(`${API_BASE}/api/v1/audits/${activeAuditId}/patch`, {
        diff: plan.diff,
        base_source_hash: graph.source_hash || (examples.find((e) => e.id === selectedFixture)?.source_hash ?? ''),
        target_files: plan.targetFiles,
        explanation: plan.explanation,
      })
      setActivePatch(res.data)
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || err.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleRunGate = async () => {
    if (!activeAuditId) return
    setActionLoading(true)
    setActionError(null)
    try {
      const res = await axios.post(`${API_BASE}/api/v1/audits/${activeAuditId}/verify`, {
        patch_id: activePatch?.patch_id ?? null,
        use_docker: false,
      })
      setGateResult(res.data)
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || err.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleExportBundle = async () => {
    if (!activeAuditId) return
    setActionLoading(true)
    setActionError(null)
    try {
      const res = await axios.post(`${API_BASE}/api/v1/audits/${activeAuditId}/bundle`)
      setBundleInfo({
        name: res.data.bundle_name,
        path: res.data.bundle_path,
        sha256: res.data.sha256,
        byteSize: res.data.byte_size,
        verdict: res.data.manifest.gate_verdict,
      })
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || err.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleValidateBundle = async () => {
    if (!activeAuditId) return
    setActionLoading(true)
    setActionError(null)
    try {
      const res = await axios.post(`${API_BASE}/api/v1/audits/${activeAuditId}/bundle/validate`)
      setValidationResult(res.data)
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || err.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleRunReplay = async () => {
    if (!activeAuditId) return
    setActionLoading(true)
    setActionError(null)
    try {
      const res = await axios.post(`${API_BASE}/api/v1/audits/${activeAuditId}/replay`)
      setReplayResult(res.data)
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || err.message)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <main className="container">
      <header>
        <h1>BenchProof</h1>
        <p className="subtitle">Agentic Engineering Assurance Runtime — Days 4–7 Runtime (P0 Verified)</p>
      </header>

      <section className="panel" aria-labelledby="status-h">
        <h2 id="status-h">Backend status</h2>
        {error && (
          <p className="error" role="alert">
            Cannot reach the API at {API_BASE}: {error}
          </p>
        )}
        {!error && !health && <p>Connecting to {API_BASE}…</p>}
        {health && ready && (
          <dl className="facts">
            <dt>API</dt>
            <dd>
              {health.status} · v{health.version}
            </dd>
            <dt>Mode</dt>
            <dd>{mode}</dd>
            <dt>Model</dt>
            <dd>{ready.provider.model_id ?? 'not selected'}</dd>
            <dt>Runner</dt>
            <dd>
              {ready.runner.mode} · isolated execution{' '}
              {ready.runner.isolated_execution_available ? 'available' : 'not available'}
            </dd>
            <dt>Worker</dt>
            <dd>
              {ready.worker.alive && ready.worker.heartbeat
                ? `alive (${ready.worker.heartbeat.worker_id}, ${ready.worker.heartbeat.age_s}s ago)`
                : 'no recent heartbeat'}
            </dd>
            <dt>Contract hash</dt>
            <dd>
              <code>{short(ready.contract_hash)}</code>
            </dd>
          </dl>
        )}
      </section>

      <section className="panel" aria-labelledby="examples-h">
        <h2 id="examples-h">Development fixtures & Interactive runtime</h2>
        <p className="meta">
          Select a fixture to build the Engineering-State Graph (B-07) and run the NVIDIA Bounded Investigation (B-08).
        </p>
        <table className="examples">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Family</th>
              <th scope="col">Constraint</th>
              <th scope="col">Defect</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {examples.map((e) => (
              <tr key={e.id} className={selectedFixture === e.id ? 'selected-row' : ''}>
                <td>
                  <strong>{e.id}</strong>
                </td>
                <td>{e.family}</td>
                <td>{e.constraint ?? '—'}</td>
                <td>{e.defect ?? 'clean control'}</td>
                <td>
                  <button
                    className="action-btn"
                    onClick={() => handleInspectFixture(e.id)}
                    disabled={actionLoading}
                  >
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Engineering-State Graph & Impact Analysis (Day 4 & Day 5) */}
      {activeAuditId && (
        <section className="panel" aria-labelledby="inspection-h">
          <h2 id="inspection-h">Audit: <code>{activeAuditId}</code> ({selectedFixture})</h2>
          {actionError && <p className="error">{actionError}</p>}

          <div className="tab-grid">
            {graph && (
              <div className="card">
                <h3>Engineering-State Graph (B-07)</h3>
                <dl className="facts">
                  <dt>Graph hash</dt>
                  <dd><code>{short(graph.graph_hash)}</code></dd>
                  <dt>Coverage</dt>
                  <dd>
                    <span className="badge badge-success">{graph.coverage.status}</span>
                  </dd>
                  <dt>Nodes / Edges</dt>
                  <dd>{graph.nodes?.length ?? 0} nodes · {graph.edges?.length ?? 0} edges</dd>
                </dl>
                <div className="node-list">
                  <strong>Symbols & Entrypoints:</strong>
                  <ul>
                    {graph.nodes
                      ?.filter((n) => n.startsWith('symbol:') || n.startsWith('contract:'))
                      .slice(0, 8)
                      .map((n) => (
                        <li key={n}><code>{n}</code></li>
                      ))}
                  </ul>
                </div>
              </div>
            )}

            {impact && (
              <div className="card">
                <h3>Blast Radius & Deterministic Risk (B-08)</h3>
                <dl className="facts">
                  <dt>Risk Severity</dt>
                  <dd>
                    <span className={`badge badge-${impact.risk_severity.toLowerCase()}`}>
                      {impact.risk_severity}
                    </span>
                  </dd>
                  <dt>Impacted contracts</dt>
                  <dd>{impact.impacted_contracts.join(', ') || 'Global scope'}</dd>
                  <dt>Selected checks</dt>
                  <dd>{impact.selected_checks.join(', ')}</dd>
                </dl>
                <div className="node-list">
                  <strong>Risk Reasons:</strong>
                  <ul>
                    {impact.risk_reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          <div className="diagnose-box">
            <button
              className="primary-btn"
              onClick={handleRunInvestigation}
              disabled={actionLoading}
            >
              {actionLoading ? 'Running Investigation…' : 'Run NVIDIA Nemotron Investigation & Probe (B-08)'}
            </button>
          </div>

          {diagnosis && (
            <div className="card diagnosis-card">
              <h3>Investigation Outcome & Falsifiable Evidence</h3>
              <p className="meta">
                Provider: <strong>{diagnosis.provider_metadata.provider}</strong> ({diagnosis.provider_metadata.mode}) ·
                Model: <code>{diagnosis.provider_metadata.model_id ?? 'default'}</code> ·
                Action: <code>{diagnosis.action_id}</code>
              </p>

              <div className="hypotheses-box">
                {diagnosis.hypotheses_evaluation.map((h) => (
                  <div key={h.hypothesis_id} className="hypothesis-item">
                    <div className="hyp-header">
                      <strong>Hypothesis {h.hypothesis_id} ({h.constraint_id}):</strong>
                      <span className={`badge badge-${h.outcome === 'SUPPORTED' ? 'danger' : 'success'}`}>
                        {h.outcome}
                      </span>
                    </div>
                    <p className="hyp-claim">Claim: {h.claim}</p>
                    <p className="hyp-detail">{h.detail}</p>
                  </div>
                ))}
              </div>

              <div className="probe-box">
                <strong>Probe Execution ({diagnosis.probe_result.probe_name}):</strong>{' '}
                Verdict: <span className="badge badge-neutral">{diagnosis.probe_result.gate_verdict}</span> ·
                Failed Checks: {diagnosis.probe_result.failed_checks.length > 0 ? diagnosis.probe_result.failed_checks.join(', ') : 'None (clean)'}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Day 6: Protected Repair & Independent Acceptance Gate (B-09, B-10) */}
      {activeAuditId && (
        <section className="panel" aria-labelledby="gate-h">

          <div className="section-head">
            <h2 id="gate-h">Protected Repair & Acceptance Gate (Day 6 / B-09, B-10)</h2>
            <div className="button-group">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleProposePatch}
                disabled={actionLoading || !CANONICAL_DIFFS[selectedFixture || '']}
              >
                Propose Protected Repair (B-09)
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleRunGate}
                disabled={actionLoading}
              >
                Run Acceptance Gate (B-10)
              </button>
            </div>
          </div>

          {activePatch && (
            <div className="patch-card">
              <h3>Proposed Candidate Repair ({activePatch.patch_id})</h3>
              <p className="meta">
                Policy Result: <span className="badge badge-success">{activePatch.policy_result}</span> ·
                Approved Paths: {activePatch.approved_paths.join(', ')} ·
                Changed Lines: {activePatch.changed_lines} ·
                Diff Hash: <code>{short(activePatch.diff_hash)}</code>
              </p>
              <pre className="code-diff">{CANONICAL_DIFFS[selectedFixture || '']?.diff}</pre>
            </div>
          )}

          {gateResult && (
            <div className="gate-result-card">
              <div className="gate-result-header">
                <h3>Acceptance Gate Verdict:</h3>
                <span className={`badge badge-large badge-${gateResult.verdict === 'VERIFIED' ? 'success' : 'danger'}`}>
                  {gateResult.verdict}
                </span>
              </div>
              <p className="meta">
                Candidate Hash: <code>{short(gateResult.candidate_source_hash)}</code> ·
                Evaluator Hash: <code>{short(gateResult.evaluator_hash)}</code> ·
                Passing: {gateResult.passing_checks.length} · Failing: {gateResult.failing_checks.length}
              </p>

              <div className="checks-table-wrapper">
                <table className="checks-table">
                  <thead>
                    <tr>
                      <th>Check ID</th>
                      <th>Outcome</th>
                      <th>Oracle Kind</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gateResult.checks.map((c: any) => (
                      <tr key={c.check_id}>
                        <td><code>{c.check_id}</code></td>
                        <td>
                          <span className={`badge badge-${c.outcome === 'PASS' ? 'success' : 'danger'}`}>
                            {c.outcome}
                          </span>
                        </td>
                        <td>{c.oracle_kind}</td>
                        <td>{c.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Day 7: Evidence Bundle Export & Independent Replay (B-11) */}
      {activeAuditId && (
        <section className="panel" aria-labelledby="bundle-h">
          <div className="section-head">
            <h2 id="bundle-h">Evidence Bundle & Independent Replay (Day 7 / B-11)</h2>
            <div className="button-group">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleExportBundle}
                disabled={actionLoading}
              >
                Export Bundle (.zip)
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleValidateBundle}
                disabled={actionLoading}
              >
                Verify Manifest (Non-executing)
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleRunReplay}
                disabled={actionLoading}
              >
                Run Independent Replay (B-11)
              </button>
            </div>
          </div>

          {bundleInfo && (
            <div className="card bundle-card">
              <h3>Canonical Evidence Bundle Ready</h3>
              <p className="meta">
                Archive: <code>{bundleInfo.name}</code> ·
                SHA-256: <code>{short(bundleInfo.sha256)}</code> ({bundleInfo.byteSize} bytes) ·
                Verdict: <span className="badge badge-success">{bundleInfo.verdict}</span>
              </p>
              <a
                href={`${API_BASE}/api/v1/audits/${activeAuditId}/bundle`}
                className="btn btn-sm btn-primary"
                download
              >
                Download ZIP Bundle
              </a>
            </div>
          )}

          {validationResult && (
            <div className="card validation-card">
              <h3>Non-Executing Cryptographic Hash Validation</h3>
              <p>
                Status:{' '}
                <span className={`badge badge-${validationResult.valid ? 'success' : 'danger'}`}>
                  {validationResult.valid ? 'PASS — CRYPTOGRAPHIC INTEGRITY VERIFIED' : 'FAIL — TAMPERED'}
                </span>{' '}
                · Verified Files: <strong>{validationResult.verified_files} / {validationResult.total_files}</strong>
              </p>
              {validationResult.discrepancies.length > 0 && (
                <div className="discrepancy-box">
                  <strong>Discrepancies:</strong>
                  <ul>
                    {validationResult.discrepancies.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {replayResult && (
            <div className="card replay-card">
              <div className="replay-head">
                <h3>Fresh Isolated Replay Result</h3>
                <span
                  className={`badge badge-large badge-${
                    replayResult.verdict_matches && replayResult.checks_matched && !replayResult.tampered
                      ? 'success'
                      : 'danger'
                  }`}
                >
                  {replayResult.tampered ? 'TAMPERED / BLOCKED' : replayResult.replayed_verdict}
                </span>
              </div>
              <p className="meta">
                Replay ID: <code>{replayResult.replay_id}</code> ·
                Tamper Status: <strong>{replayResult.tampered ? 'TAMPERED' : 'AUTHENTIC'}</strong> ·
                Checks Matched:{' '}
                <strong>{replayResult.checks_matched ? '100% MATCH' : 'MISMATCH'}</strong> ·
                Verdict Matches:{' '}
                <strong>{replayResult.verdict_matches ? 'YES' : 'NO'}</strong>
              </p>

              <div className="table-responsive">
                <table className="checks-table">
                  <thead>
                    <tr>
                      <th>Check ID</th>
                      <th>Recorded Outcome</th>
                      <th>Replayed Fresh</th>
                      <th>Integrity Match</th>
                    </tr>
                  </thead>
                  <tbody>
                    {replayResult.check_comparisons.map((c) => (
                      <tr key={c.check_id}>
                        <td>
                          <code>{c.check_id}</code>
                        </td>
                        <td>
                          <span className="badge badge-neutral">{c.original_outcome}</span>
                        </td>
                        <td>
                          <span
                            className={`badge badge-${
                              c.replayed_outcome === 'PASS' ? 'success' : 'danger'
                            }`}
                          >
                            {c.replayed_outcome}
                          </span>
                        </td>
                        <td>
                          <span className={`badge badge-${c.match ? 'success' : 'danger'}`}>
                            {c.match ? 'MATCH' : 'MISMATCH'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      <section className="panel" aria-labelledby="constraints-h">

        <h2 id="constraints-h">Accepted constraints</h2>
        {constraints.length === 0 && <p>None loaded.</p>}
        <ul className="list">
          {constraints.map((c) => (
            <li key={c.constraint_id}>
              <strong>
                {c.constraint_id} v{c.version}
              </strong>{' '}
              {c.required ? '(required)' : '(optional)'}
              <p>{c.statement}</p>
              <p className="meta">
                checks: {c.protected_check_ids.join(', ')} · hash <code>{short(c.hash)}</code>
              </p>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}

export default App
