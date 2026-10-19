import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'
import axios, { AxiosError } from 'axios'
import { CodingWorkspace } from './components/coding/CodingWorkspace'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')
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
  coding?: {
    enabled: boolean
    admission_configured: boolean
    blocked_reason: string | null
    worker_alive: boolean
    profile: string
    session_seconds_remaining: number
    hard_model_calls_per_day: number
    hard_executions_per_day: number
    hard_token_cap: boolean
  }
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
  context_hash: string
  current_decision_ids: string[]
  decision_refresh_overhead_ms: number
}
type DecisionDependency = {
  dependency_type: string
  dependency_key: string
  expected_hash: string
  current_hash: string | null
  status: string
  reason?: string | null
}
type DecisionRecord = {
  decision_id: string
  statement: string
  review_status: string
  status: string
  dependencies: DecisionDependency[]
  evidence_ids: string[]
  stale_reason?: string | null
  revisit_condition?: string | null
}
type DecisionLedger = {
  decisions: DecisionRecord[]
  current_decision_ids: string[]
  invalidated_decision_ids: string[]
  refresh_overhead_ms: number
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
  attempt?: number
  policy_result?: string
  state_updated?: boolean
}
type MutationResult = {
  template_id: string
  template_version: number
  family: string
  validity: string
  outcome: string
  reason: string
  duration_ms: number
}
type MutationRun = {
  mutation_run_id: string
  policy: string
  strength_status: string
  counts: { killed: number; survived: number; invalid: number; skipped: number; unknown: number }
  candidate_unchanged: boolean
  overhead_ms: number
  execution_count: number
  template_versions: string[]
  results: MutationResult[]
}
type MutationLedger = { status: string; policy: string; runs: MutationRun[] }
type Diagnosis = {
  action_id: string
  provider_metadata: { mode: string; provider: string; model_id?: string; usage?: { total_tokens?: number } }
  probe_result: { probe_name: string; elapsed_ms: number; gate_verdict: string; failed_checks: string[] }
  hypotheses_evaluation: { hypothesis_id: string; claim: string; outcome: string; detail: string }[]
  strategy: string
  trajectory: TrajectoryStatus
  remaining_limits: Record<string, number>
}
type TrajectoryStatus = {
  outcome?: string
  run_state?: string
  rule_version?: string
  repeat_threshold?: number
  recovery_count: number
  recovery_strategy?: string | null
  remaining_limits: Record<string, number>
}
type BundleInfo = { name: string; sha256: string; byteSize: number; verdict: string }
type BundleResponse = { bundle_name: string; sha256: string; byte_size: number; manifest: { gate_verdict: string } }
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
type Skill = {
  skill_id: string
  slash: string
  title: string
  description: string
  category: string
  method: string
  endpoint: string
  needs_audit: boolean
  costs: string[]
  keywords: string[]
  shortcut: string | null
  available: boolean
  blocked_reason: string | null
}
type SkillCatalog = { version: string; audit_id: string | null; skills: Skill[] }

const TERMINAL = new Set(['COMPLETED', 'FAILED', 'CANCELLED', 'TIMED_OUT', 'BLOCKED'])
const COST_LABELS: Record<string, string> = { 'model-call': 'model call', 'isolated-execution': 'isolated run', none: 'no cost' }
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
  if (['PASS', 'VERIFIED', 'COMPLETED', 'AUTHENTIC', 'MATCH', 'FULL', 'KILLED', 'ADEQUATE_FOR_DECLARED_MUTANTS', 'APPROVED'].includes(normalized)) return 'success'
  if (['FAIL', 'REJECTED', 'FAILED', 'TIMED_OUT', 'TAMPERED', 'MISMATCH', 'STALE', 'CHANGED', 'DELETED', 'SURVIVED'].includes(normalized)) return 'danger'
  if (['CURRENT', 'REVIEWED'].includes(normalized)) return 'success'
  if (['BLOCKED', 'CANCEL_PENDING', 'INCONCLUSIVE', 'UNKNOWN', 'WEAK', 'PENDING'].includes(normalized)) return 'warning'
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
    STALE_CONTEXT: 'Reload the current decision context before requesting another diagnosis or patch.',
    CHECK_UNKNOWN: 'Inspect the unknown check; it cannot produce a VERIFIED verdict.',
    CANCEL_PENDING: 'Wait for remote termination reconciliation; no new work will be started.',
    STALLED: 'Use the single fresh-context recovery; repeated identical work remains stopped.',
    RECOVERY_EXHAUSTED: 'Review preserved evidence; the second stall is terminally blocked.',
    IDEMPOTENCY_CONFLICT: 'The same request key was reused with a different body; start a new request.',
  }
  return { code, message, next: nextByCode[code] ?? 'Review the event trail, keep existing evidence, and retry only if safe.' }
}

function App() {
  const [activeTab, setActiveTab] = useState<'coding' | 'legacy'>(() => {
    return (localStorage.getItem('benchproof.active-tab') as 'coding' | 'legacy') || 'coding'
  })
  const [health, setHealth] = useState<Health | null>(null)
  const [ready, setReady] = useState<Ready | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [constraints, setConstraints] = useState<Constraint[]>([])
  const [selectedFixture, setSelectedFixture] = useState('MC-01')
  const [selectedMode, setSelectedMode] = useState<'live' | 'mock'>(import.meta.env.DEV ? 'mock' : 'live')
  const [audit, setAudit] = useState<Audit | null>(null)
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [impact, setImpact] = useState<ImpactData | null>(null)
  const [decisionLedger, setDecisionLedger] = useState<DecisionLedger | null>(null)
  const [decisionStatement, setDecisionStatement] = useState('Preserve the accepted contract while applying the smallest relevant repair.')
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [trajectory, setTrajectory] = useState<TrajectoryStatus | null>(null)
  const [activePatch, setActivePatch] = useState<PatchRecord | null>(null)
  const [gateResult, setGateResult] = useState<GateResult | null>(null)
  const [mutationRun, setMutationRun] = useState<MutationRun | null>(null)
  const [bundleInfo, setBundleInfo] = useState<BundleInfo | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [replayResult, setReplayResult] = useState<ReplayResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [issue, setIssue] = useState<Issue | null>(null)
  const [eventCursor, setEventCursor] = useState(0)
  const [skills, setSkills] = useState<Skill[]>([])
  const [skillsVersion, setSkillsVersion] = useState('')
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [paletteIndex, setPaletteIndex] = useState(0)
  const cursorRef = useRef(0)
  const paletteInput = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    localStorage.setItem('benchproof.active-tab', activeTab)
  }, [activeTab])

  const activeAuditId = audit?.audit_id ?? null
  const plan = CANONICAL_DIFFS[selectedFixture]
  const isTerminal = audit ? TERMINAL.has(audit.run_state) : false

  const refreshAudit = useCallback(async (auditId: string) => {
    const response = await api.get<Audit>(`/api/v1/audits/${auditId}`)
    setAudit(response.data)
    return response.data
  }, [])

  const loadSkills = useCallback(async (auditId: string | null) => {
    try {
      const response = await api.get<SkillCatalog>(auditId ? `/api/v1/audits/${auditId}/skills` : '/api/v1/skills')
      setSkills(response.data.skills)
      setSkillsVersion(response.data.version)
    } catch {
      setSkills([]) // the buttons then fall back to their local rules
    }
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
      const [graphResponse, impactResponse, decisionsResponse, trajectoryResponse, patchesResponse, gateResponse, mutationResponse] = await Promise.all([
        api.get(`/api/v1/audits/${auditId}/graph`),
        api.get<ImpactData>(`/api/v1/audits/${auditId}/impact`),
        api.get<DecisionLedger>(`/api/v1/audits/${auditId}/decisions`),
        api.get<TrajectoryStatus>(`/api/v1/audits/${auditId}/trajectory`),
        api.get<PatchRecord[]>(`/api/v1/audits/${auditId}/patches`),
        api.get(`/api/v1/audits/${auditId}/gate`),
        api.get<MutationLedger>(`/api/v1/audits/${auditId}/mutations`),
      ])
      setGraph(graphResponse.data.graph ?? graphResponse.data)
      setImpact(impactResponse.data)
      setDecisionLedger(decisionsResponse.data)
      setTrajectory(trajectoryResponse.data)
      setActivePatch(patchesResponse.data.at(-1) ?? null)
      setMutationRun(mutationResponse.data.runs.at(-1) ?? null)
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
          attempt: gateResponse.data.attempt,
        })
      }
      await loadSkills(auditId)
    } catch (error) {
      const nextIssue = issueFrom(error)
      setIssue(nextIssue)
      if ((error as AxiosError).response?.status === 404 || nextIssue.code === 'OWNER_DENIED') localStorage.removeItem(ACTIVE_AUDIT_KEY)
    } finally {
      setRestoring(false)
    }
  }, [loadSkills, refreshAudit])

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
        else await loadSkills(null)
      } catch (error) {
        setIssue(issueFrom(error))
      }
    }
    void boot()
  }, [loadConnectedAudit, loadSkills])

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
        void loadSkills(activeAuditId)
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
  }, [activeAuditId, audit?.run_state, loadSkills])

  async function startAudit(fixtureId: string) {
    setLoading(true)
    setIssue(null)
    setEvents([])
    setDiagnosis(null)
    setDecisionLedger(null)
    setTrajectory(null)
    setActivePatch(null)
    setGateResult(null)
    setMutationRun(null)
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

  async function refreshReadiness() {
    setIssue(null)
    try {
      const response = await api.get<Ready>('/api/v1/ready?refresh=true')
      setReady(response.data)
      await loadSkills(activeAuditId)
    } catch (error) {
      setIssue(issueFrom(error))
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
      void loadSkills(activeAuditId)
    }
  }

  // Every skill maps to one owner-scoped endpoint; the server repeats every check on invocation.
  const skillActions: Record<string, () => Promise<void>> = {
    start: () => startAudit(selectedFixture),
    'refresh-readiness': refreshReadiness,
    diagnose: async () => {
      if (!audit) return
      const response = await api.post<Diagnosis>(`/api/v1/audits/${audit.audit_id}/diagnose`)
      setDiagnosis(response.data)
      setTrajectory(response.data.trajectory)
    },
    recover: async () => {
      if (!audit) return
      const response = await api.post<{ result: Diagnosis }>(`/api/v1/audits/${audit.audit_id}/recover`)
      setDiagnosis(response.data.result)
      setTrajectory(response.data.result.trajectory)
    },
    decision: async () => {
      if (!audit || !decisionStatement.trim()) return
      await api.post(`/api/v1/audits/${audit.audit_id}/decisions`, {
        statement: decisionStatement,
        review_status: 'REVIEWED',
        dependency_paths: plan?.targetFiles ?? [],
        include_contract: true,
        include_source: !plan,
        evidence_ids: graph ? [graph.graph_hash] : [],
        revisit_condition: 'Re-review when a declared dependency changes or is deleted.',
      })
      const [ledgerResponse, impactResponse] = await Promise.all([
        api.get<DecisionLedger>(`/api/v1/audits/${audit.audit_id}/decisions`),
        api.get<ImpactData>(`/api/v1/audits/${audit.audit_id}/impact`),
      ])
      setDecisionLedger(ledgerResponse.data)
      setImpact(impactResponse.data)
    },
    repair: async () => {
      if (!audit || !plan || !graph) return
      const response = await api.post<PatchRecord>(`/api/v1/audits/${audit.audit_id}/patch`, {
        diff: plan.diff,
        base_source_hash: graph.source_hash,
        target_files: plan.targetFiles,
        explanation: plan.explanation,
        context_hash: impact?.context_hash,
      })
      setActivePatch({ ...response.data, diff_text: plan.diff })
    },
    verify: async () => {
      if (!audit) return
      const response = await api.post<GateResult>(`/api/v1/audits/${audit.audit_id}/verify`, { patch_id: activePatch?.patch_id ?? null, use_docker: true })
      setGateResult(response.data)
      const patches = await api.get<PatchRecord[]>(`/api/v1/audits/${audit.audit_id}/patches`)
      setActivePatch((current) => {
        const judged = patches.data.find((item) => item.patch_id === current?.patch_id)
        return current && judged ? { ...current, policy_result: judged.policy_result } : current
      })
    },
    strength: async () => {
      if (!audit) return
      const response = await api.post<MutationRun>(`/api/v1/audits/${audit.audit_id}/mutations`, { patch_id: activePatch?.patch_id ?? null, max_mutants: 3 })
      setMutationRun(response.data)
    },
    export: async () => {
      if (!audit) return
      const response = await api.post<BundleResponse>(`/api/v1/audits/${audit.audit_id}/bundle`)
      setBundleInfo({ name: response.data.bundle_name, sha256: response.data.sha256, byteSize: response.data.byte_size, verdict: response.data.manifest.gate_verdict })
    },
    validate: async () => {
      if (!audit) return
      const response = await api.post<ValidationResult>(`/api/v1/audits/${audit.audit_id}/bundle/validate`)
      setValidationResult(response.data)
    },
    replay: async () => {
      if (!audit) return
      const response = await api.post<ReplayResult>(`/api/v1/audits/${audit.audit_id}/replay`)
      setReplayResult(response.data)
    },
    cancel: async () => {
      if (!audit) return
      await api.post(`/api/v1/audits/${audit.audit_id}/cancel`)
    },
  }

  const skillById = useMemo(() => new Map(skills.map((skill) => [skill.skill_id, skill])), [skills])
  const can = (skillId: string, fallback: boolean) => skillById.get(skillId)?.available ?? fallback
  const why = (skillId: string, fallback?: string) => {
    const skill = skillById.get(skillId)
    return skill && !skill.available ? skill.blocked_reason ?? undefined : fallback
  }

  async function runSkill(skillId: string) {
    const skill = skillById.get(skillId)
    setPaletteOpen(false)
    setPaletteQuery('')
    if (skill && !skill.available) {
      setIssue({
        code: 'SKILL_BLOCKED',
        message: `${skill.slash} is not available: ${skill.blocked_reason ?? 'no reason recorded'}`,
        next: 'Pick an available skill; reasons come from the audit record, the budgets and runtime readiness.',
      })
      return
    }
    const action = skillActions[skillId]
    if (!action) return
    if (skillId === 'start' || skillId === 'refresh-readiness') {
      await action()
      return
    }
    await runAction(action)
  }

  const runSkillRef = useRef(runSkill)
  useEffect(() => {
    runSkillRef.current = runSkill
  })

  const normalizedQuery = paletteQuery.trim().replace(/^\//, '').toLowerCase()
  const filteredSkills = useMemo(() => {
    const matches = skills.filter((skill) => !normalizedQuery || [skill.slash, skill.skill_id, skill.title, skill.category, ...skill.keywords].some((term) => term.toLowerCase().includes(normalizedQuery)))
    const exact = `/${normalizedQuery}`
    return matches.sort((a, b) => Number(b.slash === exact) - Number(a.slash === exact))
  }, [normalizedQuery, skills])

  useEffect(() => {
    if (paletteOpen) paletteInput.current?.focus()
  }, [paletteOpen])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      const typing = !!target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable)
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteIndex(0)
        setPaletteOpen((open) => !open)
      } else if (event.key === '/' && !typing && !paletteOpen) {
        event.preventDefault()
        setPaletteIndex(0)
        setPaletteOpen(true)
      } else if (event.key === 'Escape' && paletteOpen) {
        setPaletteOpen(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [paletteOpen])

  function onPaletteKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setPaletteIndex((index) => Math.min(index + 1, Math.max(filteredSkills.length - 1, 0)))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setPaletteIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const chosen = filteredSkills[paletteIndex]
      if (chosen) void runSkillRef.current(chosen.skill_id)
    }
  }

  const nextAction = useMemo((): { text: string; skill: string | null } => {
    if (issue) return { text: issue.next, skill: null }
    if (!audit) return { text: 'Choose one curated synthetic example and start an assurance run.', skill: 'start' }
    if (audit.run_state === 'STALLED') {
      return trajectory?.recovery_count
        ? { text: 'The recovery has stalled; preserve evidence and stop.', skill: 'export' }
        : { text: 'Run the single changed-strategy recovery with the remaining original budget.', skill: 'recover' }
    }
    if (audit.run_state === 'BLOCKED') return { text: 'No more retries are allowed; review the preserved partial evidence.', skill: 'export' }
    if (audit.run_state === 'CANCEL_PENDING') return { text: 'Wait for remote cancellation reconciliation; do not start duplicate work.', skill: null }
    if (audit.gate_verdict === 'VERIFIED') return { text: 'Export and independently replay the evidence before accepting the repair.', skill: bundleInfo ? 'replay' : 'export' }
    if (audit.gate_verdict === 'REJECTED') {
      return plan
        ? { text: 'Review the failed checks, propose the bounded repair, then verify again.', skill: activePatch ? 'verify' : 'repair' }
        : { text: 'Review the failed checks; this fixture has no approved automatic repair.', skill: 'export' }
    }
    if (gateResult?.unknown_checks.length) return { text: 'Resolve the UNKNOWN required checks; completion does not mean VERIFIED.', skill: 'refresh-readiness' }
    if (!diagnosis) return { text: 'Run the bounded investigation, or verify directly to observe the clean/rejected path.', skill: 'diagnose' }
    if (plan && !activePatch) return { text: 'Review and propose the protected minimal diff.', skill: 'repair' }
    return { text: 'Run the independent acceptance gate.', skill: 'verify' }
  }, [activePatch, audit, bundleInfo, diagnosis, gateResult, issue, plan, trajectory?.recovery_count])
  const suggestedSkill = nextAction.skill ? skillById.get(nextAction.skill) : undefined
  const availableCount = skills.filter((skill) => skill.available).length

  return (
    <main className="container" id="workspace">
      <nav className="topbar" aria-label="Main navigation">
        <a className="brand" href="#workspace" aria-label="BenchProof workspace">
          <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M12 3 4.5 6v6c0 4.5 7.5 9 7.5 9s7.5-4.5 7.5-9V6L12 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="m8.5 12 2.2 2.2 4.8-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
          BenchProof<span className="workspace-label">Coding workspace</span>
        </a>
        <div className="topbar-actions"><span className="topbar-caption">NVIDIA inference · Nebius</span><button type="button" className="btn btn-secondary" aria-haspopup="dialog" aria-expanded={paletteOpen} onClick={() => { setPaletteIndex(0); setPaletteOpen(true) }}>Commands<span className="shortcut">Ctrl K</span></button></div>
      </nav>

      <div className="tab-navigation" role="tablist" aria-label="BenchProof Modules" style={{ marginTop: '16px', marginBottom: '20px' }}>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'coding'}
          className={`nav-tab-btn ${activeTab === 'coding' ? 'active' : ''}`}
          onClick={() => setActiveTab('coding')}
        >
          Coding workspace
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'legacy'}
          className={`nav-tab-btn ${activeTab === 'legacy' ? 'active' : ''}`}
          onClick={() => setActiveTab('legacy')}
        >
          Assurance checks
        </button>
      </div>

      {activeTab === 'coding' ? (
        <CodingWorkspace api={api} ready={ready} owner={OWNER} />
      ) : (
        <>
          <div className="scope-note" style={{ marginTop: '16px', marginBottom: '16px' }}>
            <strong>Historical Assurance View:</strong> This view contains the contract verification dashboard on prepared invoice fixtures. For the autonomous coding agent with live task planning, code edits, isolated container execution, diffs, checkpoints, and downloads, use the <strong>⚡ Autonomous Coding Agent</strong> tab above.
          </div>
          <header className="hero">
        <div><p className="eyebrow">Bounded engineering assurance</p>
          <h1>Code changes.<br />Proof, not guesswork.</h1>
          <p className="subtitle">Investigate a change, verify it in isolation, and keep evidence anyone with the bundle can independently replay.</p>
        </div>
        <div className="workflow" aria-label="Assurance workflow"><span><b>01</b>Select scope</span><i aria-hidden="true" /><span><b>02</b>Verify change</span><i aria-hidden="true" /><span><b>03</b>Keep the proof</span></div>
      </header>

      <section className="status-strip" aria-label="Runtime status">
        <div><span className={`status-dot ${health ? 'ready' : ''}`} aria-hidden="true" /><span className="status-copy"><strong>API</strong><span className="status-value">{health ? `v${health.version}` : 'Connecting…'}</span></span></div>
        <div><span className={`status-dot ${ready?.provider.configured ? 'ready' : ''}`} aria-hidden="true" /><span className="status-copy"><strong>Provider</strong><span className="status-value">{ready ? ready.provider.configured ? 'Live ready' : 'Mock only' : 'Checking…'}</span></span></div>
        <div><span className={`status-dot ${ready?.runner.isolated_execution_available ? 'ready' : ''}`} aria-hidden="true" /><span className="status-copy"><strong>Runner</strong><span className="status-value">{ready?.runner.mode ?? 'Checking…'}{ready && !ready.runner.isolated_execution_available ? ' · isolation unavailable' : ''}</span></span></div>
        <div><span className={`status-dot ${ready?.worker.alive ? 'ready' : ''}`} aria-hidden="true" /><span className="status-copy"><strong>Worker</strong><span className="status-value">{ready ? ready.worker.alive ? 'Alive' : 'Offline' : 'Checking…'}</span></span></div>
      </section>

      <section className="skill-bar" aria-label="Skills">
        <nav className="workspace-nav" aria-label="Workspace sections"><a href="#examples-h">Cases</a>{audit && <><a href="#run-h">Active run</a><a href="#repair-h">Verification</a><a href="#evidence-h">Evidence</a></>}<a href="#constraints-h">Policy</a></nav>
        <span className="meta">{skills.length ? `${availableCount} / ${skills.length} commands available` : 'Direct controls available while the command catalog loads.'}</span>
      </section>

      {issue && <section className="alert" role="alert" aria-live="assertive"><strong>{issue.code}</strong><span>{issue.message}</span><small>Next: {issue.next}</small></section>}

      <section className="panel setup-panel" aria-labelledby="examples-h">
        <div className="section-head">
          <div><p className="eyebrow">01 / Select scope</p><h2 id="examples-h">Choose a case to investigate</h2><p className="section-description">Five synthetic invoice cases. One protected acceptance boundary.</p></div>
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
            <button type="button" className={`btn ${selectedFixture === example.id ? 'btn-primary' : 'btn-secondary'}`} disabled={loading} onClick={() => void startAudit(example.id)}>Start assurance</button>
          </article>)}
        </div>
      </section>

      {restoring && <p className="restore-note" role="status">Restoring the saved audit without creating a new run…</p>}

      {!audit && <div className="next-action"><strong>Recommended next action</strong><span>{nextAction.text}</span></div>}

      {audit && <>
        <section className="panel run-panel" aria-labelledby="run-h">
          <div className="section-head">
            <div><p className="eyebrow">02 / Active run</p><h2 id="run-h">{audit.fixture_id} <code>{audit.audit_id}</code></h2></div>
            <button type="button" className="btn btn-danger" disabled={loading || !can('cancel', !isTerminal && audit.run_state !== 'CANCEL_PENDING')} title={why('cancel')} onClick={() => void runSkill('cancel')}>{audit.run_state === 'CANCEL_PENDING' ? 'Cancel pending' : 'Cancel run'}</button>
          </div>
          <div className="verdict-grid">
            <div><span>Lifecycle</span><strong className={`badge badge-${badge(audit.run_state)}`}>{audit.run_state}</strong></div>
            <div><span>Gate verdict</span><strong className={`badge badge-${badge(audit.gate_verdict)}`}>{audit.gate_verdict}</strong></div>
            <div><span>Mode</span><strong>{audit.mode}</strong></div><div><span>Source</span><code>{short(audit.source_hash)}</code></div>
          </div>
          <div className="next-action"><strong>Recommended next action</strong><span>{nextAction.text}</span>
            {suggestedSkill && <button type="button" className="btn btn-secondary next-action-btn" disabled={loading || !suggestedSkill.available} title={suggestedSkill.blocked_reason ?? undefined} onClick={() => void runSkill(suggestedSkill.skill_id)}>Run {suggestedSkill.slash}</button>}
          </div>
          {trajectory && <div className="trajectory-strip"><span><strong>Actions</strong> {trajectory.remaining_limits.used_actions ?? 0} used · {trajectory.remaining_limits.max_actions ?? 0} left</span><span><strong>Recovery</strong> {trajectory.recovery_count}/1</span><span><strong>Rule</strong> {trajectory.repeat_threshold ?? 2} repeated no-progress attempts</span></div>}
          <details className="event-log" open><summary>Resumable event trail · cursor {eventCursor}</summary>
            {events.length === 0 ? <p>No new events after the saved cursor.</p> : <ol>{events.map((event) => <li key={`${event.attempt}-${event.sequence}`}><code>#{event.sequence}</code> <strong>{event.event_type.replaceAll('_', ' ')}</strong><time>{new Date(event.created_at).toLocaleTimeString()}</time></li>)}</ol>}
          </details>
        </section>

        <section className="panel" aria-labelledby="impact-h">
          <p className="eyebrow">03 / Inspect impact</p><h2 id="impact-h">Understand the blast radius</h2>
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
          <div className="button-group"><button type="button" className="btn btn-secondary" disabled={loading || !can('diagnose', !isTerminal && audit.run_state !== 'STALLED')} title={why('diagnose')} onClick={() => void runSkill('diagnose')}>{loading ? 'Working…' : 'Run bounded investigation'}</button>
            {audit.run_state === 'STALLED' && <button type="button" className="btn btn-primary" disabled={loading || !can('recover', (trajectory?.recovery_count ?? 0) < 1)} title={why('recover')} onClick={() => void runSkill('recover')}>Run one fresh-context recovery</button>}
          </div>
          {diagnosis && <article className="card action-result"><h3>Investigation observations</h3><p className="meta">{diagnosis.provider_metadata.provider} · {diagnosis.provider_metadata.mode} · action <code>{diagnosis.action_id}</code></p>
            <p className="meta">Strategy <code>{diagnosis.strategy}</code> · trajectory <span className={`badge badge-${badge(diagnosis.trajectory.outcome ?? 'PROGRESSING')}`}>{diagnosis.trajectory.outcome ?? 'PROGRESSING'}</span></p>
            {diagnosis.hypotheses_evaluation.map((item) => <p key={item.hypothesis_id}><span className={`badge badge-${badge(item.outcome)}`}>{item.outcome}</span> {item.claim} — {item.detail}</p>)}
          </article>}
          <article className="card decision-ledger" aria-labelledby="decisions-h">
            <div className="section-head"><div><h3 id="decisions-h">Reviewed decision ledger</h3><p className="meta">Current-only context <code>{short(impact?.context_hash)}</code> · refresh {decisionLedger?.refresh_overhead_ms ?? impact?.decision_refresh_overhead_ms ?? 0} ms</p></div></div>
            <div className="decision-compose">
              <label>Decision statement<input value={decisionStatement} onChange={(event) => setDecisionStatement(event.target.value)} /></label>
              <button type="button" className="btn btn-secondary" disabled={loading || !decisionStatement.trim() || !can('decision', !isTerminal)} title={why('decision')} onClick={() => void runSkill('decision')}>Record reviewed decision</button>
            </div>
            {!decisionLedger?.decisions.length ? <p className="meta">No decisions recorded. Proposed records stay outside active context until reviewed.</p> : <div className="decision-list">{decisionLedger.decisions.map((decision) => <div key={decision.decision_id} className="decision-row">
              <p><code>{decision.decision_id}</code> <span className={`badge badge-${badge(decision.review_status)}`}>{decision.review_status}</span> <span className={`badge badge-${badge(decision.status)}`}>{decision.status}</span></p>
              <strong>{decision.statement}</strong>
              {decision.stale_reason && <p className="stale-reason">Stale reason: {decision.stale_reason}</p>}
              <ul className="compact-list">{decision.dependencies.map((dependency) => <li key={`${dependency.dependency_type}:${dependency.dependency_key}`}><span className={`badge badge-${badge(dependency.status)}`}>{dependency.status}</span> <code>{dependency.dependency_key}</code> expected <code>{short(dependency.expected_hash)}</code> · current <code>{short(dependency.current_hash ?? undefined)}</code></li>)}</ul>
            </div>)}</div>}
          </article>
        </section>

        <section className="panel" aria-labelledby="repair-h">
          <div className="section-head"><div><p className="eyebrow">04 / Review and verify</p><h2 id="repair-h">Independent acceptance gate</h2></div><div className="button-group">
            <button type="button" className="btn btn-secondary" disabled={loading || !plan || !graph || !can('repair', !isTerminal)} title={why('repair')} onClick={() => void runSkill('repair')}>Propose bounded diff</button>
            <button type="button" className="btn btn-primary" disabled={loading || !can('verify', !isTerminal && !!ready?.runner.isolated_execution_available)} title={why('verify', !ready?.runner.isolated_execution_available ? 'Requires the isolated Docker runner' : undefined)} onClick={() => void runSkill('verify')}>Verify independently</button>
            <button type="button" className="btn btn-secondary" disabled={loading || !can('strength', gateResult?.verdict === 'VERIFIED' && !!ready?.runner.isolated_execution_available)} title={why('strength', !ready?.runner.isolated_execution_available ? 'Requires the isolated Docker runner' : undefined)} onClick={() => void runSkill('strength')}>Assess test strength</button>
          </div></div>
          {!plan && <p className="scope-note">No automatic repair is approved for this case. Verification remains available.</p>}
          {activePatch && <article className="diff-card"><p><strong>{activePatch.patch_id}</strong> · <span className={`badge badge-${badge(activePatch.policy_result)}`}>{activePatch.policy_result}</span> · {activePatch.changed_lines} changed diff lines{activePatch.policy_result === 'PENDING' && <small className="meta"> · validated against the patch rules; only the protected gate can approve or reject it</small>}</p><pre className="code-diff" tabIndex={0} aria-label="Proposed unified diff">{activePatch.diff_text ?? plan?.diff}</pre></article>}
          {gateResult && <div className="result-stack"><div className="result-summary">
            <div><span>Contract gate{gateResult.attempt ? ` · attempt ${gateResult.attempt}` : ''}</span><strong className={`badge badge-${badge(gateResult.verdict)}`}>{gateResult.verdict}</strong></div>
            <div><span>Required checks</span><strong>{gateResult.passing_checks.length} pass · {gateResult.failing_checks.length} fail · {gateResult.unknown_checks.length} unknown</strong></div>
            <div><span>Test strength</span><strong className={`badge badge-${badge(mutationRun?.strength_status ?? 'NOT_RUN')}`}>{mutationRun?.strength_status ?? 'NOT_RUN'} · OPTIONAL</strong></div>
          </div><div className="table-scroll" tabIndex={0} aria-label="Acceptance check results"><table><thead><tr><th>Check</th><th>Outcome</th><th>Oracle</th><th>Observation</th></tr></thead><tbody>
            {gateResult.checks.map((check) => <tr key={check.check_id}><td><code>{check.check_id}</code></td><td><span className={`badge badge-${badge(check.outcome)}`}>{check.outcome}</span></td><td>{check.oracle_kind}</td><td>{check.reason || 'No reason recorded'}</td></tr>)}
          </tbody></table></div></div>}
          {mutationRun && <article className="card action-result"><h3>Trusted semantic mutation evidence</h3>
            <p><span className={`badge badge-${badge(mutationRun.strength_status)}`}>{mutationRun.strength_status}</span> {mutationRun.counts.killed} killed · {mutationRun.counts.survived} survived · {mutationRun.counts.invalid} invalid · {mutationRun.counts.skipped} skipped · {mutationRun.counts.unknown} unknown</p>
            <p className="meta">{mutationRun.execution_count} shared-budget executions · {mutationRun.overhead_ms} ms · candidate {mutationRun.candidate_unchanged ? 'unchanged' : 'changed'} · policy {mutationRun.policy}</p>
            <ul className="compact-list">{mutationRun.results.map((result) => <li key={result.template_id}><code>{result.template_id}@{result.template_version}</code> <span className={`badge badge-${badge(result.outcome)}`}>{result.outcome}</span> {result.reason}</li>)}</ul>
          </article>}
        </section>

        <section className="panel" aria-labelledby="evidence-h">
          <div className="section-head"><div><p className="eyebrow">05 / Preserve evidence</p><h2 id="evidence-h">Take the proof with you</h2></div><div className="button-group">
            <button type="button" className="btn btn-secondary" disabled={loading || !can('export', true)} title={why('export')} onClick={() => void runSkill('export')}>Build bundle</button>
            <button type="button" className="btn btn-secondary" disabled={loading || !can('validate', true)} title={why('validate')} onClick={() => void runSkill('validate')}>Validate hashes</button>
            <button type="button" className="btn btn-primary" disabled={loading || !can('replay', !!ready?.runner.isolated_execution_available)} title={why('replay', !ready?.runner.isolated_execution_available ? 'Requires the isolated Docker runner' : undefined)} onClick={() => void runSkill('replay')}>Replay checks</button>
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
        </>
      )}

      <footer className="workspace-footer"><span>BenchProof · bounded, independently checked, replayable.</span><span>VERIFIED applies only to the declared checks and source version.</span></footer>

      {paletteOpen && <div className="palette-backdrop" role="presentation" onMouseDown={() => setPaletteOpen(false)}>
        <section className="palette" role="dialog" aria-modal="true" aria-label="Skill palette" onMouseDown={(event) => event.stopPropagation()}>
          <input
            ref={paletteInput}
            className="palette-input"
            role="combobox"
            aria-expanded="true"
            aria-controls="skill-options"
            aria-activedescendant={filteredSkills[paletteIndex] ? `skill-${filteredSkills[paletteIndex].skill_id}` : undefined}
            placeholder="Type a skill, e.g. /verify"
            value={paletteQuery}
            onChange={(event) => { setPaletteQuery(event.target.value); setPaletteIndex(0) }}
            onKeyDown={onPaletteKeyDown}
          />
          <p className="meta palette-hint">{skillsVersion || 'catalog'} · ↑↓ to move · Enter runs the highlighted skill · Esc closes · costs and blocked reasons are computed by the server</p>
          <ol id="skill-options" className="palette-list" role="listbox" aria-label="Skills">
            {filteredSkills.map((skill, index) => <li
              key={skill.skill_id}
              id={`skill-${skill.skill_id}`}
              role="option"
              aria-selected={index === paletteIndex}
              aria-disabled={!skill.available}
              onMouseEnter={() => setPaletteIndex(index)}
              onClick={() => void runSkill(skill.skill_id)}
            >
              <div className="palette-row-head"><code>{skill.slash}</code><strong>{skill.title}</strong><span className="palette-category">{skill.category}</span></div>
              <p>{skill.description}</p>
              <div className="palette-row-meta">
                {skill.costs.map((cost) => <span key={cost} className={`badge badge-${cost === 'none' ? 'neutral' : 'warning'}`}>{COST_LABELS[cost] ?? cost}</span>)}
                <span className="meta">{skill.method} {skill.endpoint}</span>
                {!skill.available && <span className="palette-blocked">{skill.blocked_reason}</span>}
              </div>
            </li>)}
            {filteredSkills.length === 0 && <li className="palette-empty" aria-disabled="true">{skills.length ? `No skill matches “${paletteQuery}”.` : 'The skill catalog could not be loaded from the API.'}</li>}
          </ol>
        </section>
      </div>}
    </main>
  )
}

export default App
