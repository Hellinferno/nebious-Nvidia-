import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios, { AxiosError } from 'axios'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'
const OWNER_KEY = 'benchproof.owner-capability'
const ACTIVE_AUDIT_KEY = 'benchproof.active-audit'
const ACTIVE_FIXTURE_KEY = 'benchproof.active-fixture'

function ownerCapability() {
  const existing = localStorage.getItem(OWNER_KEY)
  if (existing) return existing
  const created = `owner-${crypto.randomUUID()}`
  localStorage.setItem(OWNER_KEY, created)
  return created
}

const OWNER = ownerCapability()
const api = axios.create({
  baseURL: API_BASE,
  headers: { 'X-BenchProof-Owner': OWNER },
})

type Health = { status: string; version: string; runner: string }
type Ready = {
  status: string
  database: boolean
  contract_hash: string
  provider: { name: string; configured: boolean; model_id: string | null }
  runner: { mode: string; isolated_execution_available: boolean; detail?: string }
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
type Audit = {
  audit_id: string
  fixture_id: string
  source_hash: string
  contract_hash: string
  run_state: string
  gate_verdict: string
  mode: 'live' | 'mock'
  created_at: string
}
type AuditEvent = {
  sequence: number
  attempt: number
  event_type: string
  payload: Record<string, unknown>
  created_at: string
}
type GraphData = {
  graph_id: string
  graph_hash: string
  source_hash: string
  coverage: { status: string; total_files: number; total_symbols: number; total_edges: number }
  nodes: string[]
  edges: { from_node: string; to_node: string; edge_type: string; provenance: string }[]
  unresolved_items?: string[]
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
type PatchRecord = {
  patch_id: string
  diff_hash: string
  diff_text?: string
  approved_paths: string[]
  changed_lines: number
  policy_result: string
}
type Check = { check_id: string; outcome: string; oracle_kind: string; reason: string; source_hash?: string; evaluator_hash?: string }
type GateResult = {
  verdict: string
  candidate_source_hash: string
  evaluator_hash: string
  passing_checks: string[]
  failing_checks: string[]
  unknown_checks: string[]
  checks: Check[]
}
type Diagnosis = {
  action_id: string
  provider_metadata: { mode: string; provider: string; model_id?: string; usage?: { total_tokens?: number } }
  probe_result: { probe_name: string; elapsed_ms: number; gate_verdict: string; failed_checks: string[] }
  hypotheses_evaluation: { hypothesis_id: string; claim: string; outcome: string; detail: string }[]
}
type BundleInfo = { name: string; sha256: string; byteSize: number; verdict: string }
type ValidationResult = { valid: boolean; total_files: number; verified_files: number; discrepancies: string[] }
type ReplayResult = {
  replay_id: string
  replayed_verdict: string
  original_verdict: string
  verdict_matches: boolean
  checks_matched: boolean
  tampered: boolean
}
type Issue = { code: string; message: string; next: string }

const TERMINAL = new Set(['COMPLETED', 'FAILED', 'CANCELLED', 'TIMED_OUT', 'BLOCKED'])
const CANONICAL_DIFFS: Record<string, { diff: string; targetFiles: string[]; explanation: string }> = {
  'MC-01': {
    diff: `--- a/app/money.py
+++ b/app/money.py
@@ -4,12 +4,6 @@
 def compute_total(lines: List[str]) -> str:
-    """Faulty: premature rounding of each line."""
+    """Sum unrounded line amounts, then ROUND_HALF_UP once on the invoice total."""
     if not lines:
         return "0.00"
-    total = Decimal("0")
-    for line in lines:
-        val = Decimal(line).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
-        total += val
+    total = sum((Decimal(line) for line in lines), Decimal("0"))
     return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))`,
    targetFiles: ['app/money.py'],
    explanation: 'Sum unrounded items before one ROUND_HALF_UP operation on the invoice total.',
  },
  'AC-01': {
    diff: `--- a/app/schemas.py
+++ b/app/schemas.py
@@ -13,3 +13,2 @@
-    amount: str
+    total_amount: str
+    status: str
--- a/app/services.py
+++ b/app/services.py
@@ -24,2 +24,2 @@
-        "amount": total,
+        "total_amount": total,
+        "status": "processed"`,
    targetFiles: ['app/schemas.py', 'app/services.py'],
    explanation: 'Restore total_amount and status fields in ReceiptResponse.',
  },
}

function short(value?: string) {
  return value ? value.slice(0, 12) : 'unknown'
}

function badge(value: string) {
  const normalized = value.toUpperCase()
  if (['PASS', 'VERIFIED', 'COMPLETED', 'AUTHENTIC', 'MATCH', 'FULL'].includes(normalized)) return 'success'
  if (['FAIL', 'REJECTED', 'FAILED', 'TIMED_OUT', 'TAMPERED', 'MISMATCH'].includes(normalized)) return 'danger'
  if (['BLOCKED', 'CANCEL_PENDING', 'INCONCLUSIVE', 'UNKNOWN'].includes(normalized)) return 'warning'
  return 'neutral'
}

function issueFrom(error: unknown): Issue {
  const response = (error as AxiosError<{ detail?: { code?: string; message?: string } }>).response
  const code = response?.data?.detail?.code ?? 'REQUEST_FAILED'
  const message = response?.data?.detail?.message ?? (error as Error).message
  const nextByCode: Record<string, string> = {
    OWNER_DENIED: 'Return to your own session or start a new curated audit.',
    PROVIDER_UNAVAILABLE: 'Select mock mode or configure the Nebius provider, then retry once.',
    RUNNER_UNAVAILABLE: 'Keep the evidence and retry after an isolated runner is available.',
    BUDGET_EXHAUSTED: 'Review partial evidence; do not start another paid action.',
    STALE_SOURCE: 'Start a fresh audit against the current source hash.',
    PATCH_BASE_MISMATCH: 'Rebuild impact context and propose a patch against the current source.',
    CHECK_UNKNOWN: 'Inspect the unknown check; it cannot produce a VERIFIED verdict.',
    CANCEL_PENDING: 'Wait for remote termination reconciliation; no new work will be started.',
  }
  return { code, message, next: nextByCode[code] ?? 'Review the event trail, keep existing evidence, and retry only if safe.' }
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [ready, setReady] = useState<Ready | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [constraints, setConstraints] = useState<Constraint[]>([])
  const [selectedFixture, setSelectedFixture] = useState('MC-01')
  const [selectedMode, setSelectedMode] = useState<'live' | 'mock'>('mock')
  const [audit, setAudit] = useState<Audit | null>(null)
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [impact, setImpact] = useState<ImpactData | null>(null)
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [activePatch, setActivePatch] = useState<PatchRecord | null>(null)
  const [gateResult, setGateResult] = useState<GateResult | null>(null)
  const [bundleInfo, setBundleInfo] = useState<BundleInfo | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [replayResult, setReplayResult] = useState<ReplayResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [issue, setIssue] = useState<Issue | null>(null)
  const [eventCursor, setEventCursor] = useState(0)
  const cursorRef = useRef(0)

  const activeAuditId = audit?.audit_id ?? null
  const plan = CANONICAL_DIFFS[selectedFixture]
  const isTerminal = audit ? TERMINAL.has(audit.run_state) : false

  const refreshAudit = useCallback(async (auditId: string) => {
    const response = await api.get<Audit>(`/api/v1/audits/${auditId}`)
    setAudit(response.data)
    return response.data
  }, [])

  const loadConnectedAudit = useCallback(async (auditId: string, restoringSession = false) => {
    if (restoringSession) setRestoring(true)
    setIssue(null)
    try {
      const snapshot = await refreshAudit(auditId)
      setSelectedFixture(snapshot.fixture_id)
      setSelectedMode(snapshot.mode)
      localStorage.setItem(ACTIVE_AUDIT_KEY, auditId)
      localStorage.setItem(ACTIVE_FIXTURE_KEY, snapshot.fixture_id)
      const [graphResponse, impactResponse, patchesResponse, gateResponse] = await Promise.all([
        api.get(`/api/v1/audits/${auditId}/graph`),
        api.get<ImpactData>(`/api/v1/audits/${auditId}/impact`),
        api.get<PatchRecord[]>(`/api/v1/audits/${auditId}/patches`),
        api.get(`/api/v1/audits/${auditId}/gate`),
      ])
      setGraph(graphResponse.data.graph ?? graphResponse.data)
      setImpact(impactResponse.data)
      setActivePatch(patchesResponse.data.at(-1) ?? null)
      if (gateResponse.data.checks?.length) {
        const checks: Check[] = gateResponse.data.checks
        setGateResult({
          verdict: gateResponse.data.gate_verdict,
          candidate_source_hash: checks[0]?.source_hash ?? snapshot.source_hash,
          evaluator_hash: checks[0]?.evaluator_hash ?? '',
          passing_checks: checks.filter((item) => item.outcome === 'PASS').map((item) => item.check_id),
          failing_checks: checks.filter((item) => item.outcome === 'FAIL').map((item) => item.check_id),
          unknown_checks: checks.filter((item) => item.outcome === 'UNKNOWN').map((item) => item.check_id),
          checks,
        })
      }
    } catch (error) {
      const nextIssue = issueFrom(error)
      setIssue(nextIssue)
      if ((error as AxiosError).response?.status === 404 || nextIssue.code === 'OWNER_DENIED') localStorage.removeItem(ACTIVE_AUDIT_KEY)
    } finally {
      setRestoring(false)
    }
  }, [refreshAudit])

  useEffect(() => {
    async function boot() {
      try {
        const [healthResponse, readyResponse, examplesResponse, constraintsResponse] = await Promise.all([
          api.get<Health>('/api/v1/health'),
          api.get<Ready>('/api/v1/ready'),
          api.get<Example[]>('/api/v1/examples'),
          api.get<Constraint[]>('/api/v1/constraints'),
        ])
        setHealth(healthResponse.data)
        setReady(readyResponse.data)
        setExamples(examplesResponse.data)
        setConstraints(constraintsResponse.data)
        const savedFixture = localStorage.getItem(ACTIVE_FIXTURE_KEY)
        if (savedFixture) setSelectedFixture(savedFixture)
        const savedAudit = localStorage.getItem(ACTIVE_AUDIT_KEY)
        if (savedAudit) await loadConnectedAudit(savedAudit, true)
      } catch (error) {
        setIssue(issueFrom(error))
      }
    }
    void boot()
  }, [loadConnectedAudit])

  useEffect(() => {
    if (!activeAuditId) return
    const cursorKey = `benchproof.cursor.${activeAuditId}`
    cursorRef.current = Number(localStorage.getItem(cursorKey) ?? '0')
    setEventCursor(cursorRef.current)
    let stopped = false
    let controller: AbortController | null = null
    let retryTimer: number | undefined

    const acceptEvent = (event: AuditEvent) => {
      if (event.sequence <= cursorRef.current) return
      cursorRef.current = event.sequence
      setEventCursor(event.sequence)
      localStorage.setItem(cursorKey, String(event.sequence))
      setEvents((current) => [...current.filter((item) => item.sequence !== event.sequence), event].slice(-30))
      if (event.event_type === 'state_changed' && typeof event.payload.to === 'string') {
        setAudit((current) => current ? { ...current, run_state: String(event.payload.to) } : current)
      }
      if (event.event_type === 'verification_completed' && typeof event.payload.gate_verdict === 'string') {
        setAudit((current) => current ? { ...current, gate_verdict: String(event.payload.gate_verdict) } : current)
      }
    }

    async function connect() {
      controller = new AbortController()
      try {
        const response = await fetch(`${API_BASE}/api/v1/audits/${activeAuditId}/events`, {
          headers: { Accept: 'text/event-stream', 'Last-Event-ID': String(cursorRef.current), 'X-BenchProof-Owner': OWNER },
          signal: controller.signal,
        })
        if (!response.ok || !response.body) throw new Error(`Event stream failed (${response.status})`)
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (!stopped) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
          let boundary = buffer.indexOf('\n\n')
          while (boundary >= 0) {
            const frame = buffer.slice(0, boundary)
            buffer = buffer.slice(boundary + 2)
            const eventName = frame.match(/^event:\s*(.+)$/m)?.[1]
            const data = frame.match(/^data:\s*(.+)$/m)?.[1]
            if (data && eventName !== 'retry' && eventName !== 'end') acceptEvent(JSON.parse(data) as AuditEvent)
            boundary = buffer.indexOf('\n\n')
          }
        }
      } catch (error) {
        if (!stopped && (error as Error).name !== 'AbortError') setIssue(issueFrom(error))
      }
      if (!stopped && !TERMINAL.has(audit?.run_state ?? '')) retryTimer = window.setTimeout(() => void connect(), 1000)
    }

    void connect()
    return () => {
      stopped = true
      controller?.abort()
      if (retryTimer) window.clearTimeout(retryTimer)
    }
  }, [activeAuditId, audit?.run_state])

  async function startAudit(fixtureId: string) {
    setLoading(true)
    setIssue(null)
    setEvents([])
    setDiagnosis(null)
    setActivePatch(null)
    setGateResult(null)
    setBundleInfo(null)
    setValidationResult(null)
    setReplayResult(null)
    setSelectedFixture(fixtureId)
    const pendingKeyName = `benchproof.pending-create.${fixtureId}.${selectedMode}`
    const idempotencyKey = localStorage.getItem(pendingKeyName) ?? crypto.randomUUID()
    localStorage.setItem(pendingKeyName, idempotencyKey)
    try {
      const response = await api.post<Audit>('/api/v1/audits', { fixture_id: fixtureId, mode: selectedMode }, { headers: { 'Idempotency-Key': idempotencyKey } })
      localStorage.removeItem(pendingKeyName)
      cursorRef.current = 0
      await loadConnectedAudit(response.data.audit_id)
    } catch (error) {
      setIssue(issueFrom(error))
    } finally {
      setLoading(false)
    }
  }

  async function runAction(action: () => Promise<void>) {
    setLoading(true)
    setIssue(null)
    try {
      await action()
      if (activeAuditId) await refreshAudit(activeAuditId)
    } catch (error) {
      setIssue(issueFrom(error))
    } finally {
      setLoading(false)
    }
  }

  const nextAction = useMemo(() => {
    if (issue) return issue.next
    if (!audit) return 'Choose one curated synthetic example and start an assurance run.'
    if (audit.run_state === 'CANCEL_PENDING') return 'Wait for remote cancellation reconciliation; do not start duplicate work.'
    if (audit.gate_verdict === 'VERIFIED') return 'Export and independently replay the evidence before accepting the repair.'
    if (audit.gate_verdict === 'REJECTED') return plan ? 'Review failed checks, start a fresh audit, propose the bounded repair, then verify.' : 'Review the failed checks; this fixture has no approved automatic repair.'
    if (gateResult?.unknown_checks.length) return 'Resolve the UNKNOWN required checks; completion does not mean VERIFIED.'
    if (!diagnosis) return 'Run the bounded investigation, or verify directly to observe the clean/rejected path.'
    if (plan && !activePatch) return 'Review and propose the protected minimal diff.'
    return 'Run the independent acceptance gate.'
  }, [activePatch, audit, diagnosis, gateResult, issue, plan])

  return (
    <main className="container">
      <header className="hero">
        <p className="eyebrow">NVIDIA × Nebius · bounded assurance</p>
        <h1>BenchProof</h1>
        <p className="subtitle">From a proposed code change to independently replayable evidence.</p>
      </header>

      <section className="status-strip" aria-label="Runtime status">
        <span><strong>API</strong> {health ? `v${health.version}` : 'connecting'}</span>
        <span><strong>Provider</strong> {ready?.provider.configured ? 'live ready' : 'mock only'}</span>
        <span><strong>Runner</strong> {ready?.runner.mode ?? 'unknown'}</span>
        <span><strong>Worker</strong> {ready?.worker.alive ? 'alive' : 'offline'}</span>
      </section>

      {issue && <section className="alert" role="alert" aria-live="assertive"><strong>{issue.code}</strong><span>{issue.message}</span><small>Next: {issue.next}</small></section>}

      <section className="panel setup-panel" aria-labelledby="examples-h">
        <div className="section-head">
          <div><p className="eyebrow">1 · Select scope</p><h2 id="examples-h">Curated synthetic invoice cases</h2></div>
          <label className="mode-control">Execution mode
            <select value={selectedMode} onChange={(event) => setSelectedMode(event.target.value as 'live' | 'mock')}>
              <option value="mock">Mock investigation</option>
              <option value="live" disabled={!ready?.provider.configured}>Live NVIDIA inference</option>
            </select>
          </label>
        </div>
        <p className="scope-note">Python fixtures only · accepted constraints are protected · arbitrary repository upload is disabled.</p>
        <div className="example-grid">
          {examples.map((example) => <article className={`example-card ${selectedFixture === example.id ? 'selected' : ''}`} key={example.id}>
            <div className="card-title-row"><strong>{example.id}</strong><span className="badge badge-neutral">synthetic</span></div>
            <p>{example.family}</p><small>{example.defect ?? 'Clean control: expected to pass unchanged.'}</small>
            <button type="button" className="btn btn-primary" disabled={loading} onClick={() => void startAudit(example.id)}>Start assurance</button>
          </article>)}
        </div>
      </section>

      {restoring && <p className="restore-note" role="status">Restoring the saved audit without creating a new run…</p>}

      {audit && <>
        <section className="panel run-panel" aria-labelledby="run-h">
          <div className="section-head">
            <div><p className="eyebrow">2 · Follow the run</p><h2 id="run-h">{audit.fixture_id} <code>{audit.audit_id}</code></h2></div>
            <button type="button" className="btn btn-danger" disabled={loading || isTerminal || audit.run_state === 'CANCEL_PENDING'} onClick={() => void runAction(async () => { await api.post(`/api/v1/audits/${audit.audit_id}/cancel`) })}>{audit.run_state === 'CANCEL_PENDING' ? 'Cancel pending' : 'Cancel run'}</button>
          </div>
          <div className="verdict-grid">
            <div><span>Lifecycle</span><strong className={`badge badge-${badge(audit.run_state)}`}>{audit.run_state}</strong></div>
            <div><span>Gate verdict</span><strong className={`badge badge-${badge(audit.gate_verdict)}`}>{audit.gate_verdict}</strong></div>
            <div><span>Mode</span><strong>{audit.mode}</strong></div><div><span>Source</span><code>{short(audit.source_hash)}</code></div>
          </div>
          <div className="next-action"><strong>Recommended next action</strong><span>{nextAction}</span></div>
          <details className="event-log" open><summary>Resumable event trail · cursor {eventCursor}</summary>
            {events.length === 0 ? <p>No new events after the saved cursor.</p> : <ol>{events.map((event) => <li key={`${event.attempt}-${event.sequence}`}><code>#{event.sequence}</code> <strong>{event.event_type.replaceAll('_', ' ')}</strong><time>{new Date(event.created_at).toLocaleTimeString()}</time></li>)}</ol>}
          </details>
        </section>

        <section className="panel" aria-labelledby="impact-h">
          <p className="eyebrow">3 · Inspect impact</p><h2 id="impact-h">Bounded engineering context</h2>
          <div className="two-column">
            <article className="card"><h3>Graph coverage</h3><dl className="facts">
              <dt>Status</dt><dd><span className={`badge badge-${badge(graph?.coverage.status ?? 'UNKNOWN')}`}>{graph?.coverage.status ?? 'UNKNOWN'}</span></dd>
              <dt>Graph hash</dt><dd><code>{short(graph?.graph_hash)}</code></dd><dt>Scale</dt><dd>{graph?.nodes.length ?? 0} nodes · {graph?.edges.length ?? 0} edges</dd>
              <dt>Unknowns</dt><dd>{graph?.unresolved_items?.join(', ') || 'None declared'}</dd>
            </dl></article>
            <article className="card"><h3>Affected paths</h3><p><span className={`badge badge-${badge(impact?.risk_severity ?? 'UNKNOWN')}`}>{impact?.risk_severity ?? 'UNKNOWN'} risk</span></p>
              <ul className="compact-list">{(impact?.impacted_symbols ?? []).slice(0, 8).map((symbol) => <li key={symbol}><code>{symbol}</code></li>)}</ul>
              <p className="meta">Checks: {impact?.selected_checks.join(', ') || 'not loaded'}</p>
            </article>
          </div>
          <button type="button" className="btn btn-secondary" disabled={loading || isTerminal} onClick={() => void runAction(async () => { const response = await api.post<Diagnosis>(`/api/v1/audits/${audit.audit_id}/diagnose`); setDiagnosis(response.data) })}>{loading ? 'Working…' : 'Run bounded investigation'}</button>
          {diagnosis && <article className="card action-result"><h3>Investigation observations</h3><p className="meta">{diagnosis.provider_metadata.provider} · {diagnosis.provider_metadata.mode} · action <code>{diagnosis.action_id}</code></p>
            {diagnosis.hypotheses_evaluation.map((item) => <p key={item.hypothesis_id}><span className={`badge badge-${badge(item.outcome)}`}>{item.outcome}</span> {item.claim} — {item.detail}</p>)}
          </article>}
        </section>

        <section className="panel" aria-labelledby="repair-h">
          <div className="section-head"><div><p className="eyebrow">4 · Review and verify</p><h2 id="repair-h">Protected candidate repair</h2></div><div className="button-group">
            <button type="button" className="btn btn-secondary" disabled={loading || !plan || isTerminal} onClick={() => void runAction(async () => { if (!plan || !graph) return; const response = await api.post<PatchRecord>(`/api/v1/audits/${audit.audit_id}/patch`, { diff: plan.diff, base_source_hash: graph.source_hash, target_files: plan.targetFiles, explanation: plan.explanation }); setActivePatch({ ...response.data, diff_text: plan.diff }) })}>Propose bounded diff</button>
            <button type="button" className="btn btn-primary" disabled={loading || isTerminal} onClick={() => void runAction(async () => { const response = await api.post<GateResult>(`/api/v1/audits/${audit.audit_id}/verify`, { patch_id: activePatch?.patch_id ?? null, use_docker: false }); setGateResult(response.data) })}>Verify independently</button>
          </div></div>
          {!plan && <p className="scope-note">No automatic repair is approved for this case. Verification remains available.</p>}
          {activePatch && <article className="diff-card"><p><strong>{activePatch.patch_id}</strong> · <span className={`badge badge-${badge(activePatch.policy_result)}`}>{activePatch.policy_result}</span> · {activePatch.changed_lines} changed diff lines</p><pre className="code-diff" tabIndex={0} aria-label="Proposed unified diff">{activePatch.diff_text ?? plan?.diff}</pre></article>}
          {gateResult && <div className="result-stack"><div className="result-summary">
            <div><span>Contract gate</span><strong className={`badge badge-${badge(gateResult.verdict)}`}>{gateResult.verdict}</strong></div>
            <div><span>Required checks</span><strong>{gateResult.passing_checks.length} pass · {gateResult.failing_checks.length} fail · {gateResult.unknown_checks.length} unknown</strong></div>
            <div><span>Test strength</span><strong className="badge badge-neutral">NOT RUN · P1</strong></div>
          </div><div className="table-scroll" tabIndex={0} aria-label="Acceptance check results"><table><thead><tr><th>Check</th><th>Outcome</th><th>Oracle</th><th>Observation</th></tr></thead><tbody>
            {gateResult.checks.map((check) => <tr key={check.check_id}><td><code>{check.check_id}</code></td><td><span className={`badge badge-${badge(check.outcome)}`}>{check.outcome}</span></td><td>{check.oracle_kind}</td><td>{check.reason || 'No reason recorded'}</td></tr>)}
          </tbody></table></div></div>}
        </section>

        <section className="panel" aria-labelledby="evidence-h">
          <div className="section-head"><div><p className="eyebrow">5 · Preserve evidence</p><h2 id="evidence-h">Export and independent replay</h2></div><div className="button-group">
            <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => void runAction(async () => { const response = await api.post(`/api/v1/audits/${audit.audit_id}/bundle`); setBundleInfo({ name: response.data.bundle_name, sha256: response.data.sha256, byteSize: response.data.byte_size, verdict: response.data.manifest.gate_verdict }) })}>Build bundle</button>
            <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => void runAction(async () => { const response = await api.post<ValidationResult>(`/api/v1/audits/${audit.audit_id}/bundle/validate`); setValidationResult(response.data) })}>Validate hashes</button>
            <button type="button" className="btn btn-primary" disabled={loading} onClick={() => void runAction(async () => { const response = await api.post<ReplayResult>(`/api/v1/audits/${audit.audit_id}/replay`); setReplayResult(response.data) })}>Replay checks</button>
          </div></div>
          {bundleInfo && <article className="card evidence-card"><p><strong>{bundleInfo.name}</strong> · {bundleInfo.byteSize.toLocaleString()} bytes</p><p className="meta">SHA-256 <code>{short(bundleInfo.sha256)}</code> · recorded verdict <span className={`badge badge-${badge(bundleInfo.verdict)}`}>{bundleInfo.verdict}</span></p>
            <button type="button" className="btn btn-secondary" onClick={() => void runAction(async () => { const response = await api.get(`/api/v1/audits/${audit.audit_id}/bundle`, { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = bundleInfo.name; link.click(); URL.revokeObjectURL(url) })}>Download authenticated ZIP</button>
          </article>}
          {validationResult && <p className="evidence-line"><span className={`badge badge-${validationResult.valid ? 'success' : 'danger'}`}>{validationResult.valid ? 'INTEGRITY PASS' : 'TAMPERED'}</span> {validationResult.verified_files}/{validationResult.total_files} files verified</p>}
          {replayResult && <p className="evidence-line"><span className={`badge badge-${replayResult.tampered || !replayResult.checks_matched ? 'danger' : 'success'}`}>{replayResult.replayed_verdict}</span> replay {replayResult.checks_matched ? 'matches' : 'does not match'} the recorded checks</p>}
        </section>
      </>}

      <section className="panel" aria-labelledby="constraints-h"><p className="eyebrow">Protected policy</p><h2 id="constraints-h">Accepted executable constraints</h2><div className="constraint-list">
        {constraints.map((constraint) => <article key={constraint.constraint_id}><strong>{constraint.constraint_id} v{constraint.version}</strong><p>{constraint.statement}</p><small>{constraint.required ? 'Required' : 'Optional'} · checks {constraint.protected_check_ids.join(', ')}</small></article>)}
      </div></section>
    </main>
  )
}

export default App
