import type { CodingPreferences } from './types'
import type { ReactNode } from 'react'
import { TASK_RECIPES } from './taskRecipes'

type TaskComposerProps = {
  projectName: string
  task: string
  workflow: CodingPreferences['workflow']
  instructions: string
  savedInstructions: string | null
  files: string[]
  editablePaths: string[]
  creating: boolean
  blockedReason: string | null
  onTaskChange: (task: string) => void
  onWorkflowChange: (workflow: CodingPreferences['workflow']) => void
  onInstructionsChange: (instructions: string) => void
  onPathsChange: (paths: string[]) => void
  onSaveInstructions: () => void
  onForgetInstructions: () => void
  onCreate: () => void
  agentSettings?: ReactNode
}

export function TaskComposer(props: TaskComposerProps) {
  return (
    <article className="workspace-card task-composer">
      <div className="card-header-row">
        <div>
          <p className="composer-eyebrow">Your agent, your workflow</p>
          <h2>What are we building?</h2>
        </div>
        <span className="composer-project">{props.projectName}</span>
      </div>

      <form className="task-form" onSubmit={(event) => { event.preventDefault(); props.onCreate() }}>
        {props.agentSettings}
        <fieldset className="recipe-fieldset">
          <legend>Choose a starting point</legend>
          <div className="recipe-grid">
            {TASK_RECIPES.map((recipe) => (
              <label key={recipe.id} className={`recipe-option ${props.workflow === recipe.id ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="task-workflow"
                  value={recipe.id}
                  checked={props.workflow === recipe.id}
                  onChange={() => props.onWorkflowChange(recipe.id)}
                />
                <span><strong>{recipe.label}</strong><small>{recipe.description}</small></span>
              </label>
            ))}
          </div>
          <p className="field-help">Recipes guide the plan and edits. They never expand file access or execution permissions.</p>
          {props.workflow === 'custom' && <p className="field-help">Custom tasks follow the repair flow. If existing checks already pass, choose Add a feature or Refactor.</p>}
        </fieldset>

        <div className="form-field">
          <label htmlFor="task-prompt">Describe the outcome</label>
          <textarea
            id="task-prompt"
            className="form-textarea"
            value={props.task}
            onChange={(event) => props.onTaskChange(event.target.value)}
            placeholder="What should change? Include expected behavior and important edge cases."
            maxLength={4000}
            required
            rows={4}
            aria-describedby="task-prompt-help"
          />
          <small id="task-prompt-help" className="field-help">Be specific about success. {props.task.length.toLocaleString()} / 4,000 characters</small>
        </div>

        <details className="instruction-settings" open={props.instructions.length > 0}>
          <summary>Coding instructions <span>Optional</span></summary>
          <div className="instruction-settings-body">
            <label htmlFor="coding-instructions">Conventions the agent should follow</label>
            <textarea
              id="coding-instructions"
              className="form-textarea"
              value={props.instructions}
              onChange={(event) => props.onInstructionsChange(event.target.value)}
              placeholder="Keep public function signatures. Use descriptive names. Prefer the standard library."
              maxLength={2000}
              rows={3}
              aria-describedby="coding-instructions-help"
            />
            <small id="coding-instructions-help" className="field-help">Included in this task's plan and edits. Do not include secrets. {props.instructions.length.toLocaleString()} / 2,000 characters</small>
            <div className="instruction-actions">
              <button type="button" className="btn btn-secondary" onClick={props.onSaveInstructions} disabled={!props.instructions.trim() || props.savedInstructions === props.instructions}>
                {props.savedInstructions === props.instructions && props.savedInstructions !== null ? 'Saved in this browser' : 'Save for future tasks'}
              </button>
              {props.savedInstructions !== null && (
                <button type="button" className="btn btn-secondary" onClick={props.onForgetInstructions}>Forget saved instructions</button>
              )}
            </div>
            <p className="field-help">Saving is optional and local to this browser. Existing tasks keep their approved instructions.</p>
          </div>
        </details>

        <fieldset className="recipe-fieldset">
          <legend>Files the agent may change <span>({props.editablePaths.length}/3)</span></legend>
          <div className="editable-paths-group">
            {props.files.filter((path) => path.startsWith('app/')).map((path) => {
              const selected = props.editablePaths.includes(path)
              return (
                <label key={path} className={`path-checkbox-label ${selected ? 'selected' : ''}`}>
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={!selected && props.editablePaths.length >= 3}
                    onChange={() => props.onPathsChange(selected ? props.editablePaths.filter((item) => item !== path) : [...props.editablePaths, path])}
                  />
                  {path}
                </label>
              )
            })}
          </div>
          <p className="field-help">Tests stay read-only. Review the exact plan before any code changes.</p>
        </fieldset>

        {props.blockedReason && <p className="composer-blocked" role="status">{props.blockedReason}</p>}
        <div className="composer-footer">
          <p className="field-help">Task settings are pinned when this draft is created.<br />Creating a draft makes no model call.</p>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={props.creating || !!props.blockedReason || !props.task.trim() || props.editablePaths.length === 0}
          >
            {props.creating ? 'Creating draft…' : 'Create task draft'}
          </button>
        </div>
      </form>
    </article>
  )
}
