import { useState } from 'react'
import type { AxiosInstance } from 'axios'
import type { AgentPreferences } from './agentProfiles'
import { exportSkillMarkdown, parseSkillMarkdown, readSkills, validateSkill, writeSkills } from './agentSkills'
import type { AgentSkill } from './agentSkills'
import type { CodingPreferences } from './types'

type Context = NonNullable<CodingPreferences['context']>[number]
type Connection = { id: string; name: string; tools: string[] }
type Props = {
  api: AxiosInstance
  owner: string
  preferences: AgentPreferences
  onChange: (preferences: AgentPreferences) => void
  context: Context[]
  onContext: (context: Context[]) => void
}

const EMPTY_SKILL: AgentSkill = { name: '', description: '', instructions: '' }

export function AgentExtensions(props: Props) {
  const [library, setLibrary] = useState(() => readSkills(props.owner))
  const [draft, setDraft] = useState<AgentSkill>(EMPTY_SKILL)
  const [message, setMessage] = useState('')
  const [connections, setConnections] = useState<Connection[]>([])
  const [connection, setConnection] = useState('')
  const [tool, setTool] = useState('')
  const [argumentsText, setArgumentsText] = useState('{}')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const selected = props.preferences.skills || []

  const saveSkill = (candidate: AgentSkill) => {
    try {
      const checked = validateSkill(candidate)
      const next = [...library.filter((skill) => skill.name !== checked.name), checked]
      writeSkills(props.owner, next)
      setLibrary(next)
      setDraft(checked)
      setMessage('Skill saved locally. Select it to include its exact text in a new task; existing tasks are unchanged.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not save skill.') }
  }

  const loadConnections = async () => {
    setBusy(true)
    try {
      const response = await props.api.get<{ mcp_connections: Connection[] }>('/api/v1/coding-tasks/extensions/catalog')
      setConnections(response.data.mcp_connections)
      setMessage(response.data.mcp_connections.length ? 'Choose an operator-approved connection and tool.' : 'No MCP connections configured. The operator must configure approved HTTPS endpoints and a daily query allowance.')
    } catch { setMessage('The MCP catalog is unavailable on this deployment.') }
    finally { setBusy(false) }
  }

  const fetchContext = async () => {
    setBusy(true)
    try {
      const argumentsValue: unknown = JSON.parse(argumentsText)
      if (!argumentsValue || typeof argumentsValue !== 'object' || Array.isArray(argumentsValue)) throw new Error('Arguments must be a JSON object.')
      const response = await props.api.post<Context>('/api/v1/coding-tasks/extensions/mcp-context', { connection, tool, arguments: argumentsValue, consent })
      props.onContext([...props.context, response.data])
      setConsent(false)
      setMessage('MCP context fetched and selected for this draft. Review it before creating the task; it is not verification evidence.')
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: { message?: string } } } }).response?.data?.detail?.message
      setMessage(detail || (error instanceof Error ? error.message : 'MCP query failed.'))
    } finally { setBusy(false) }
  }

  return (
    <section className="agent-settings-body extension-settings" aria-label="Skills, MCP and harness">
      <fieldset className="recipe-fieldset">
        <legend>Harness strategy</legend>
        <select id="agent-harness" value={props.preferences.harness || 'bounded-v1'} onChange={(event) => {
          const harness = event.target.value as 'bounded-v1' | 'single-pass-v1'
          props.onChange({ ...props.preferences, harness, limits: { ...props.preferences.limits, patch_attempts: harness === 'single-pass-v1' ? 1 : props.preferences.limits.patch_attempts } })
        }}>
          <option value="bounded-v1">Bounded repair loop · up to two candidates</option>
          <option value="single-pass-v1">Single-pass · one candidate, no automatic revision</option>
        </select>
        <p className="field-help">Versioned built-in strategies change orchestration, not permissions. Single-pass is enforced in the backend and limits edit attempts to one. Arbitrary third-party harness code is not loaded.</p>
      </fieldset>

      <details className="instruction-settings">
        <summary>Skills manager <span>{selected.length}/3 selected</span></summary>
        <div className="instruction-settings-body">
          <p className="field-help">Create or import instruction-only SKILL.md files. Scripts, archives and referenced files are never installed or executed. Skills are saved in this browser; selected snapshots travel with the profile and task.</p>
          {[...library, ...selected.filter((skill) => !library.some((item) => item.name === skill.name))].map((skill) => (
            <div key={skill.name} className="skill-library-row">
              <label><input type="checkbox" checked={selected.some((item) => item.name === skill.name)} disabled={selected.length >= 3 && !selected.some((item) => item.name === skill.name)} onChange={(event) => props.onChange({ ...props.preferences, skills: event.target.checked ? [...selected, skill] : selected.filter((item) => item.name !== skill.name) })} /> <strong>{skill.name}</strong> — {skill.description}</label>
              <div className="agent-settings-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setDraft(skill)}>Edit skill copy</button>
                <button type="button" className="btn btn-secondary" onClick={() => {
                  const url = URL.createObjectURL(new Blob([exportSkillMarkdown(skill)], { type: 'text/markdown' }))
                  const link = document.createElement('a'); link.href = url; link.download = `${skill.name}-SKILL.md`; link.click(); URL.revokeObjectURL(url)
                }}>Export SKILL.md</button>
                <button type="button" className="btn btn-secondary" onClick={() => {
                  try {
                    const next = library.filter((item) => item.name !== skill.name)
                    writeSkills(props.owner, next); setLibrary(next)
                    props.onChange({ ...props.preferences, skills: selected.filter((item) => item.name !== skill.name) })
                  } catch { setMessage('Browser storage is unavailable; skill was not deleted.') }
                }}>Remove skill</button>
              </div>
            </div>
          ))}
          <label htmlFor="skill-name">Skill name<input id="skill-name" value={draft.name} maxLength={64} placeholder="my-python-rules" onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
          <label htmlFor="skill-description">When to use this skill<input id="skill-description" value={draft.description} maxLength={512} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
          <label htmlFor="skill-instructions">Skill instructions<textarea id="skill-instructions" className="form-textarea" value={draft.instructions} maxLength={2000} rows={4} onChange={(event) => setDraft({ ...draft, instructions: event.target.value })} /></label>
          <div className="agent-settings-actions">
            <button type="button" className="btn btn-secondary" onClick={() => saveSkill(draft)}>Save skill</button>
            <button type="button" className="btn btn-secondary" onClick={() => setDraft(EMPTY_SKILL)}>New skill</button>
            <label className="btn btn-secondary profile-import-button">Import SKILL.md<input type="file" aria-label="Import SKILL.md" accept=".md,text/markdown" onChange={async (event) => {
              const file = event.target.files?.[0]; event.target.value = ''
              if (!file) return
              try {
                if (file.size > 8192) throw new Error('Skill file exceeds 8 KiB.')
                saveSkill(parseSkillMarkdown(await file.text()))
              } catch (error) { setMessage(error instanceof Error ? error.message : 'Invalid skill.') }
            }} /></label>
          </div>
          <p className="field-help">After editing a selected skill, deselect and reselect it to explicitly use the new snapshot. Existing tasks and saved profiles never update silently.</p>
        </div>
      </details>

      <details className="instruction-settings">
        <summary>MCP reference context <span>{props.context.length}/2 snapshots</span></summary>
        <div className="instruction-settings-body">
          <p className="field-help">Read-only, operator-allowlisted HTTPS MCP tools. No shell servers, arbitrary URLs, OAuth setup or automatic model tool-calling. Protocol 2026-07-28 JSON responses only. Results are reference text, not test evidence.</p>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void loadConnections()}>Load approved MCP connections</button>
          <label htmlFor="mcp-connection">Connection<select id="mcp-connection" value={connection} onChange={(event) => { setConnection(event.target.value); setTool(''); setConsent(false) }}><option value="">Choose a connection</option>{connections.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label htmlFor="mcp-tool">Read-only tool<select id="mcp-tool" value={tool} onChange={(event) => { setTool(event.target.value); setConsent(false) }}><option value="">Choose a tool</option>{connections.find((item) => item.id === connection)?.tools.map((name) => <option key={name}>{name}</option>)}</select></label>
          <label htmlFor="mcp-arguments">Arguments (JSON)<textarea id="mcp-arguments" className="form-textarea" value={argumentsText} maxLength={2048} onChange={(event) => { setArgumentsText(event.target.value); setConsent(false) }} /></label>
          <label><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> Send these exact arguments to the selected server and include its result in this task's model context. No source is attached automatically.</label>
          <button type="button" className="btn btn-secondary" disabled={busy || !consent || !connection || !tool || props.context.length >= 2} onClick={() => void fetchContext()}>{busy ? 'Fetching…' : 'Fetch and include MCP context'}</button>
          {props.context.map((item, index) => <details key={`${item.sha256}-${index}`}><summary>{item.connection} / {item.tool}</summary><pre className="external-context-preview">{item.content}</pre><button type="button" className="btn btn-secondary" onClick={() => props.onContext(props.context.filter((_, itemIndex) => itemIndex !== index))}>Remove context</button></details>)}
          <p className="field-help">Context is draft-only until creation, then pinned by hash and approval. It is not saved in portable profiles. Failed queries still consume the shared daily allowance.</p>
        </div>
      </details>
      {message && <p className="composer-blocked" role="status">{message}</p>}
    </section>
  )
}
