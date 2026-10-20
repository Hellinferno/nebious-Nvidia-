import { AGENT_INSTRUCTION_MODULES } from './agentProfiles'
import type { AgentPreferences, AgentProfile } from './agentProfiles'
import type { ReactNode } from 'react'
import './AgentSettings.css'

type AgentSettingsProps = {
  preferences: AgentPreferences
  profiles: AgentProfile[]
  selectedProfileId: string
  defaultProfileId: string | null
  profileName: string
  modified: boolean
  error: string | null
  onChange: (preferences: AgentPreferences) => void
  onSelect: (id: string) => void
  onNameChange: (name: string) => void
  onSave: (asNew: boolean) => void
  onDuplicate: () => void
  onDelete: () => void
  onMakeDefault: () => void
  onClearDefault: () => void
  onExport: () => void
  onImport: (file: File) => void
  extensions?: ReactNode
}

const BUDGET_FIELDS = [
  { key: 'model_calls', label: 'Model calls', min: 1, max: 4 },
  { key: 'patch_attempts', label: 'Edit attempts', min: 1, max: 2 },
  { key: 'executions', label: 'Test executions', min: 1, max: 4 },
  { key: 'active_seconds', label: 'Active seconds', min: 30, max: 300 },
] as const

export function AgentSettings(props: AgentSettingsProps) {
  const { preferences } = props
  const implementationMayStopEarly = preferences.mode === 'implement'
    && (preferences.limits.model_calls < 2 || preferences.limits.executions < 3)

  return (
    <section className="agent-settings" aria-label="Agent customization">
      <div className="agent-profile-selector">
        <label htmlFor="agent-profile">Agent profile</label>
        <select id="agent-profile" value={props.selectedProfileId} onChange={(event) => props.onSelect(event.target.value)}>
          <option value="">Custom settings</option>
          {props.profiles.map((profile) => (
            <option key={profile.id} value={profile.id}>{profile.name}{props.defaultProfileId === profile.id ? ' · default' : ''}</option>
          ))}
        </select>
        {props.modified && <span className="profile-modified">Unsaved changes</span>}
      </div>

      <details className="agent-customization-details">
        <summary>Customize agent <span>{preferences.mode === 'plan_only' ? 'Plan only' : 'Approval before implementation'} · {preferences.instruction_modules.length} instruction modules</span></summary>
        <div className="agent-settings-body">
          {props.extensions}
          <fieldset className="recipe-fieldset">
            <legend>What may this agent do?</legend>
            <div className="agent-mode-options">
              <label><input type="radio" name="agent-mode" value="implement" checked={preferences.mode === 'implement'} onChange={() => props.onChange({ ...preferences, mode: 'implement' })} /><span><strong>Plan and implement</strong><small>Approve the exact plan before edits and checks.</small></span></label>
              <label><input type="radio" name="agent-mode" value="plan_only" checked={preferences.mode === 'plan_only'} onChange={() => props.onChange({ ...preferences, mode: 'plan_only' })} /><span><strong>Plan only</strong><small>Generate and refine a plan. The backend refuses edits and test executions.</small></span></label>
            </div>
          </fieldset>

          <fieldset className="recipe-fieldset">
            <legend>Instruction modules</legend>
            <p className="field-help">Combine reusable coding rules. These are prompt instructions, not installed plugins or executable tools.</p>
            <div className="instruction-module-list">
              {AGENT_INSTRUCTION_MODULES.map((module) => {
                const enabled = preferences.instruction_modules.includes(module.id)
                return (
                  <label key={module.id}>
                    <input type="checkbox" checked={enabled} value={module.id} onChange={() => props.onChange({
                      ...preferences,
                      instruction_modules: enabled ? preferences.instruction_modules.filter((id) => id !== module.id) : [...preferences.instruction_modules, module.id],
                    })} />
                    <span><strong>{module.label}</strong><small>{module.description}</small></span>
                  </label>
                )
              })}
            </div>
          </fieldset>

          <fieldset className="recipe-fieldset">
            <legend>Task budget</legend>
            <p className="field-help">Lower the demo limits for this task. Daily server limits still apply; these are not a currency or total-token guarantee.</p>
            <div className="agent-budget-presets">
              <button type="button" className="btn btn-secondary" onClick={() => props.onChange({ ...preferences, limits: { model_calls: 2, patch_attempts: 1, executions: 3, active_seconds: 120 } })}>Lean budget</button>
              <button type="button" className="btn btn-secondary" onClick={() => props.onChange({ ...preferences, limits: { model_calls: 4, patch_attempts: 2, executions: 4, active_seconds: 300 } })}>Default budget</button>
            </div>
            <div className="agent-budget-grid">
              {BUDGET_FIELDS.map((field) => (
                <label key={field.key} htmlFor={`agent-budget-${field.key}`}>{field.label}
                  <input
                    id={`agent-budget-${field.key}`}
                    type="number"
                    min={field.min}
                    max={field.max}
                    step={1}
                    disabled={preferences.mode === 'plan_only' && ['patch_attempts', 'executions'].includes(field.key)}
                    value={preferences.limits[field.key]}
                    onChange={(event) => props.onChange({ ...preferences, limits: { ...preferences.limits, [field.key]: Number(event.target.value) } })}
                  />
                </label>
              ))}
            </div>
            {implementationMayStopEarly && <p className="composer-blocked">Implementation needs at least 2 model calls and 3 test executions to complete the first edit and fresh final checks. This budget may stop earlier.</p>}
          </fieldset>

          <div className="profile-manager">
            <label htmlFor="agent-profile-name">Save this setup as a named profile</label>
            <input id="agent-profile-name" value={props.profileName} maxLength={60} onChange={(event) => props.onNameChange(event.target.value)} placeholder="e.g. My careful Python reviewer" />
            <div className="agent-settings-actions">
              <button type="button" className="btn btn-secondary" disabled={!props.profileName.trim() || !!props.error} onClick={() => props.onSave(false)}>{props.selectedProfileId ? 'Update profile' : 'Save profile'}</button>
              {props.selectedProfileId && <button type="button" className="btn btn-secondary" disabled={!props.profileName.trim() || !!props.error} onClick={() => props.onSave(true)}>Save as new</button>}
              {props.selectedProfileId && <button type="button" className="btn btn-secondary" onClick={props.onDuplicate}>Duplicate saved profile</button>}
              {props.selectedProfileId && <button type="button" className="btn btn-secondary" onClick={props.onDelete}>Delete profile</button>}
            </div>
            <div className="agent-settings-actions">
              {props.selectedProfileId && props.selectedProfileId !== props.defaultProfileId && <button type="button" className="btn btn-secondary" disabled={props.modified} onClick={props.onMakeDefault}>Make default</button>}
              {props.selectedProfileId === props.defaultProfileId && props.defaultProfileId && <button type="button" className="btn btn-secondary" onClick={props.onClearDefault}>Remove default</button>}
              <button type="button" className="btn btn-secondary" disabled={!props.profileName.trim() || !!props.error} onClick={props.onExport}>Export profile JSON</button>
              <label className="btn btn-secondary profile-import-button">Import profile JSON<input aria-label="Import agent profile" type="file" accept=".json,application/json" onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) props.onImport(file)
                event.target.value = ''
              }} /></label>
            </div>
            <p className="field-help">Profiles are stored in this browser. Imports only read validated settings; they cannot install code, change providers, or enable network access. Do not put secrets in profile text.</p>
            <p className="field-help">Save updates before making a profile default. Existing tasks keep their original instructions, mode and limits.</p>
          </div>
          {props.error && <p className="composer-blocked" role="alert">{props.error}</p>}
        </div>
      </details>
    </section>
  )
}
