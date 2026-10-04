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

function short(hash: string) {
  return hash.slice(0, 12)
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [ready, setReady] = useState<Ready | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [constraints, setConstraints] = useState<Constraint[]>([])
  const [error, setError] = useState<string | null>(null)

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

  return (
    <main className="container">
      <header>
        <h1>BenchProof</h1>
        <p className="subtitle">Agentic Engineering Assurance Runtime — Day 1 scaffold</p>
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

      <section className="panel" aria-labelledby="examples-h">
        <h2 id="examples-h">Development examples</h2>
        <p className="meta">
          Synthetic fixtures only. Starting an audit is not available in this build: no isolated
          runner exists yet.
        </p>
        <table className="examples">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Family</th>
              <th scope="col">Constraint</th>
              <th scope="col">Defect</th>
              <th scope="col">Source</th>
            </tr>
          </thead>
          <tbody>
            {examples.map((e) => (
              <tr key={e.id}>
                <td>{e.id}</td>
                <td>{e.family}</td>
                <td>{e.constraint ?? '—'}</td>
                <td>{e.defect ?? 'clean control'}</td>
                <td>
                  <code>{short(e.source_hash)}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}

export default App
