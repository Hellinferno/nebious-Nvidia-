export type Project = {
  project_id: string
  name: string
  source_hash: string
  runner_profile: string
  file_count: number
  raw_bytes: number
  created_at: string
  files?: Record<string, string>
}

export type CodingTask = {
  task_id: string
  fixture_id: string | null
  project_id?: string | null
  brief: {
    task: string
    source_hash: string
    editable_paths: string[]
  }
  contract_hash: string
  runtime_config: {
    model_id: string
    max_output_tokens: number
    engine_version: string
  }
  plan: {
    task: string
    summary: string
    steps: string[]
    editable_paths: string[]
  } | null
  approved_plan_hash: string | null
  state:
    | 'DRAFT'
    | 'PLANNING'
    | 'AWAITING_APPROVAL'
    | 'QUEUED'
    | 'RUNNING'
    | 'PAUSED'
    | 'REVIEW_READY'
    | 'BLOCKED'
    | 'FAILED'
    | 'STALLED'
    | 'CANCEL_PENDING'
    | 'CANCELLED'
    | 'INTERRUPTED'
  next_stage: 'PLAN' | 'BASELINE' | 'EDIT' | 'CANDIDATE' | 'FINAL' | 'COMPLETE'
  checkpoint: {
    stage?: string
    candidate_hash?: string
    patch?: {
      diff: string
      author?: string
    }
  } | null
  result: {
    outcome: string
    stop_reason?: string
    summary?: string
  } | null
  counters: {
    model_calls: number
    patch_attempts: number
    executions: number
    active_seconds: number
  }
  limits: {
    model_calls: number
    patch_attempts: number
    executions: number
    active_seconds: number
  }
  pause_requested: boolean
  created_at: string
  updated_at: string
}

export type CodingEvent = {
  sequence: number
  stage: string
  event_type: string
  payload: Record<string, unknown>
  created_at: string
}

export type TaskChanges = {
  state: string
  base_source_hash: string
  candidate_source_hash: string | null
  diff: string
  author: string | null
  tested_final: boolean
}

export type ExecutionRecord = {
  action_id: string
  stage: string
  status: string
  details?: Record<string, unknown>
  result?: {
    exit_code?: number
    passed?: boolean
    duration_ms?: number
    checks_total?: number
    checks_passed?: number
    stdout?: string
    stderr?: string
    command?: string
  } | null
}

export type UsageData = {
  counters: {
    model_calls: number
    patch_attempts: number
    executions: number
    active_seconds: number
  }
  limits: {
    model_calls: number
    patch_attempts: number
    executions: number
    active_seconds: number
  }
  recorded_tokens: number
  unknown_model_actions: number
  monetary_cost: string
  hard_token_cap: boolean
  output_tokens_per_call: number | null
}

export type CheckpointRecord = {
  checkpoint_id: string
  task_id: string
  sequence: number
  stage: string
  state: string
  created_at: string
  checkpoint: Record<string, unknown>
}

export type ReadyInfo = {
  status: string
  database: boolean
  contract_hash: string
  provider: { name: string; configured: boolean; model_id: string | null }
  runner: { mode: string; isolated_execution_available: boolean; detail?: string }
  worker: { alive: boolean; heartbeat: { worker_id: string; age_s: number } | null }
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
