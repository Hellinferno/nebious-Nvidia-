import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { AxiosInstance } from 'axios'
import './CodingWorkspace.css'
import { SAMPLE_PROJECTS } from './sampleProjects'
import type { SampleProjectDef } from './sampleProjects'
import type {
  CheckpointRecord,
  CodingEvent,
  CodingTask,
  ExecutionRecord,
  Project,
  ReadyInfo,
  TaskChanges,
  UsageData,
} from './types'

const ACTIVE_TASK_KEY = 'benchproof.active-coding-task'
const ACTIVE_PROJECT_KEY = 'benchproof.active-coding-project'

interface CodingWorkspaceProps {
  api: AxiosInstance
  ready: ReadyInfo | null
  owner: string
}

export const CodingWorkspace: React.FC<CodingWorkspaceProps> = ({ api, ready, owner }) => {
  // Navigation & Selection State
  const [activeTaskId, setActiveTaskId] = useState<string | null>(() => localStorage.getItem(ACTIVE_TASK_KEY))
  const [activeProjectId, setActiveProjectId] = useState<string | null>(() => localStorage.getItem(ACTIVE_PROJECT_KEY))
  const [selectedSample, setSelectedSample] = useState<SampleProjectDef>(SAMPLE_PROJECTS[0])

  // Data Collections
  const [projectsList, setProjectsList] = useState<Project[]>([])
  const [tasksList, setTasksList] = useState<CodingTask[]>([])
  const [currentTask, setCurrentTask] = useState<CodingTask | null>(null)
  const [sourceFiles, setSourceFiles] = useState<Record<string, string>>({})
  const [selectedFile, setSelectedFile] = useState<string>('')

  // Task Sub-records
  const [taskChanges, setTaskChanges] = useState<TaskChanges | null>(null)
  const [taskExecutions, setTaskExecutions] = useState<ExecutionRecord[]>([])
  const [taskUsage, setTaskUsage] = useState<UsageData | null>(null)
  const [taskCheckpoints, setTaskCheckpoints] = useState<CheckpointRecord[]>([])
  const [taskEvents, setTaskEvents] = useState<CodingEvent[]>([])

  // Task Creation Form State
  const [taskPrompt, setTaskPrompt] = useState<string>(SAMPLE_PROJECTS[0].suggestedPrompt)
  const [selectedEditablePaths, setSelectedEditablePaths] = useState<string[]>(SAMPLE_PROJECTS[0].defaultEditablePaths)

  // Plan Editing State
  const [isEditingPlan, setIsEditingPlan] = useState<boolean>(false)
  const [planSteps, setPlanSteps] = useState<string[]>([])

  // Custom Project Modal State
  const [modalOpen, setModalOpen] = useState<boolean>(false)
  const [customProjectName, setCustomProjectName] = useState<string>('MyPythonService')
  const [customFiles, setCustomFiles] = useState<Array<{ path: string; content: string }>>([
    { path: 'app/service.py', content: 'def process(value: int) -> int:\n    return value * 2\n' },
    { path: 'tests/test_service.py', content: 'import unittest\nfrom app.service import process\n\nclass TestService(unittest.TestCase):\n    def test_double(self):\n        self.assertEqual(process(4), 8)\n' },
  ])

  // Interaction & UI State
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null)
  const [eventFilter, setEventFilter] = useState<string>('ALL')

  const pollingRef = useRef<number | null>(null)

  // Save selected task and project to localStorage
  useEffect(() => {
    if (activeTaskId) localStorage.setItem(ACTIVE_TASK_KEY, activeTaskId)
    else localStorage.removeItem(ACTIVE_TASK_KEY)
  }, [activeTaskId])

  useEffect(() => {
    if (activeProjectId) localStorage.setItem(ACTIVE_PROJECT_KEY, activeProjectId)
    else localStorage.removeItem(ACTIVE_PROJECT_KEY)
  }, [activeProjectId])

  const notify = (type: 'success' | 'error' | 'info', text: string) => {
    setStatusMessage({ type, text })
    setTimeout(() => {
      setStatusMessage((current) => (current?.text === text ? null : current))
    }, 6000)
  }

  // 1. Fetch available projects and tasks
  const refreshProjects = useCallback(async () => {
    try {
      const response = await api.get<Project[]>('/api/v1/projects')
      setProjectsList(response.data)
    } catch {
      // gracefully ignore on initial mount if server is warming up
    }
  }, [api])

  const refreshTasks = useCallback(async () => {
    try {
      const response = await api.get<CodingTask[]>('/api/v1/coding-tasks?limit=50')
      setTasksList(response.data)
    } catch {
      // ignore
    }
  }, [api])

  // 2. Fetch all details for a given task
  const loadTaskData = useCallback(async (taskId: string) => {
    try {
      const [taskRes, sourceRes, changesRes, execRes, usageRes, checkRes, eventsRes] = await Promise.allSettled([
        api.get<CodingTask>(`/api/v1/coding-tasks/${taskId}`),
        api.get<{ source_hash: string; files: Record<string, string> }>(`/api/v1/coding-tasks/${taskId}/source`),
        api.get<TaskChanges>(`/api/v1/coding-tasks/${taskId}/changes`),
        api.get<ExecutionRecord[]>(`/api/v1/coding-tasks/${taskId}/executions`),
        api.get<UsageData>(`/api/v1/coding-tasks/${taskId}/usage`),
        api.get<CheckpointRecord[]>(`/api/v1/coding-tasks/${taskId}/checkpoints`),
        api.get<CodingEvent[]>(`/api/v1/coding-tasks/${taskId}/events?after=0`),
      ])

      if (taskRes.status === 'fulfilled') {
        setCurrentTask(taskRes.value.data)
        if (taskRes.value.data.plan?.steps) {
          setPlanSteps(taskRes.value.data.plan.steps)
        }
      }
      if (sourceRes.status === 'fulfilled') {
        const files = sourceRes.value.data.files || {}
        setSourceFiles(files)
        setSelectedFile((prev) => (prev && files[prev] !== undefined ? prev : Object.keys(files)[0] || ''))
      }
      if (changesRes.status === 'fulfilled') setTaskChanges(changesRes.value.data)
      if (execRes.status === 'fulfilled') setTaskExecutions(execRes.value.data)
      if (usageRes.status === 'fulfilled') setTaskUsage(usageRes.value.data)
      if (checkRes.status === 'fulfilled') setTaskCheckpoints(checkRes.value.data)
      if (eventsRes.status === 'fulfilled') setTaskEvents(eventsRes.value.data)
    } catch {
      // transient network error
    }
  }, [api])

  // Initial load
  useEffect(() => {
    let ignore = false
    const loadInit = async () => {
      try {
        const [projRes, tasksRes] = await Promise.all([
          api.get<Project[]>('/api/v1/projects'),
          api.get<CodingTask[]>('/api/v1/coding-tasks?limit=50'),
        ])
        if (!ignore) {
          setProjectsList(projRes.data)
          setTasksList(tasksRes.data)
        }
      } catch {
        // ignore
      }
    }
    void loadInit()
    return () => {
      ignore = true
    }
  }, [api])

  // Reload task details when activeTaskId changes
  useEffect(() => {
    let ignore = false
    if (!activeTaskId) {
      queueMicrotask(() => {
        if (!ignore) {
          setCurrentTask(null)
          setSourceFiles(selectedSample.files)
          setSelectedFile(Object.keys(selectedSample.files)[0] || '')
          setTaskChanges(null)
          setTaskExecutions([])
          setTaskUsage(null)
          setTaskCheckpoints([])
          setTaskEvents([])
        }
      })
      return () => {
        ignore = true
      }
    }

    const fetchTask = async () => {
      try {
        const [taskRes, sourceRes, changesRes, execRes, usageRes, checkRes, eventsRes] = await Promise.allSettled([
          api.get<CodingTask>(`/api/v1/coding-tasks/${activeTaskId}`),
          api.get<{ source_hash: string; files: Record<string, string> }>(`/api/v1/coding-tasks/${activeTaskId}/source`),
          api.get<TaskChanges>(`/api/v1/coding-tasks/${activeTaskId}/changes`),
          api.get<ExecutionRecord[]>(`/api/v1/coding-tasks/${activeTaskId}/executions`),
          api.get<UsageData>(`/api/v1/coding-tasks/${activeTaskId}/usage`),
          api.get<CheckpointRecord[]>(`/api/v1/coding-tasks/${activeTaskId}/checkpoints`),
          api.get<CodingEvent[]>(`/api/v1/coding-tasks/${activeTaskId}/events?after=0`),
        ])
        if (ignore) return
        if (taskRes.status === 'fulfilled') {
          setCurrentTask(taskRes.value.data)
          if (taskRes.value.data.plan?.steps) {
            setPlanSteps(taskRes.value.data.plan.steps)
          }
        }
        if (sourceRes.status === 'fulfilled') {
          const files = sourceRes.value.data.files || {}
          setSourceFiles(files)
          setSelectedFile((prev) => (prev && files[prev] !== undefined ? prev : Object.keys(files)[0] || ''))
        }
        if (changesRes.status === 'fulfilled') setTaskChanges(changesRes.value.data)
        if (execRes.status === 'fulfilled') setTaskExecutions(execRes.value.data)
        if (usageRes.status === 'fulfilled') setTaskUsage(usageRes.value.data)
        if (checkRes.status === 'fulfilled') setTaskCheckpoints(checkRes.value.data)
        if (eventsRes.status === 'fulfilled') setTaskEvents(eventsRes.value.data)
      } catch {
        // ignore
      }
    }
    void fetchTask()
    return () => {
      ignore = true
    }
  }, [activeTaskId, api, selectedSample])

  // Live polling for running/queued tasks
  useEffect(() => {
    if (!activeTaskId || !currentTask) return
    const isWorking = ['PLANNING', 'QUEUED', 'RUNNING', 'CANCEL_PENDING'].includes(currentTask.state)

    if (isWorking) {
      pollingRef.current = window.setInterval(() => {
        void loadTaskData(activeTaskId)
      }, 1500)
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [activeTaskId, currentTask, loadTaskData])

  // Sample Selection Handlers
  const handleSelectSample = (sample: SampleProjectDef) => {
    setSelectedSample(sample)
    setTaskPrompt(sample.suggestedPrompt)
    setSelectedEditablePaths(sample.defaultEditablePaths)
    if (!activeTaskId) {
      setSourceFiles(sample.files)
      setSelectedFile(Object.keys(sample.files)[0] || '')
    }
  }

  // Create Project & Task from Selected Sample or Upload
  const handleCreateTaskForSample = async () => {
    setLoadingAction('create-task')
    try {
      let targetProjectId: string | undefined
      let targetFixtureId: string | undefined
      let currentSourceHash = ''

      if (selectedSample.isFixture && selectedSample.fixtureId) {
        targetFixtureId = selectedSample.fixtureId
        // Retrieve source hash from ready or fixture check
        try {
          const exRes = await api.get<Array<{ id: string; source_hash: string }>>('/api/v1/examples')
          const found = exRes.data.find((e) => e.id === selectedSample.fixtureId)
          currentSourceHash = found ? found.source_hash : 'fixture-hash'
        } catch {
          currentSourceHash = 'sample-fixture-hash'
        }
      } else {
        // Create or ensure the sample project exists on the backend
        const projRes = await api.post<Project>('/api/v1/projects', {
          name: selectedSample.name,
          runner_profile: selectedSample.runnerProfile,
          files: selectedSample.files,
        })
        targetProjectId = projRes.data.project_id
        currentSourceHash = projRes.data.source_hash
        setActiveProjectId(targetProjectId)
        await refreshProjects()
      }

      // Create the coding task
      const taskRes = await api.post<CodingTask>(
        '/api/v1/coding-tasks',
        {
          project_id: targetProjectId,
          fixture_id: targetFixtureId,
          task: taskPrompt.trim(),
          source_hash: currentSourceHash,
          editable_paths: selectedEditablePaths,
        },
        {
          headers: { 'Idempotency-Key': `key-${crypto.randomUUID()}` },
        }
      )

      notify('success', `Coding task ${taskRes.data.task_id} created successfully!`)
      setActiveTaskId(taskRes.data.task_id)
      await refreshTasks()
      await loadTaskData(taskRes.data.task_id)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to create task.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  // Custom Project Submission
  const handleCreateCustomProject = async () => {
    if (customFiles.length === 0) {
      notify('error', 'Please provide at least one file.')
      return
    }
    const filesDict: Record<string, string> = {}
    let totalBytes = 0
    for (const f of customFiles) {
      const trimmedPath = f.path.trim()
      if (!trimmedPath) continue
      if (trimmedPath.includes('..') || trimmedPath.startsWith('/')) {
        notify('error', `Invalid path "${trimmedPath}": path traversal forbidden.`)
        return
      }
      const bytes = new TextEncoder().encode(f.content).length
      if (bytes > 24576) {
        notify('error', `File "${trimmedPath}" exceeds 24 KiB limit (${bytes} bytes).`)
        return
      }
      totalBytes += bytes
      filesDict[trimmedPath] = f.content
    }

    if (totalBytes > 131072) {
      notify('error', `Total project size exceeds 128 KiB limit (${totalBytes} bytes).`)
      return
    }

    setLoadingAction('create-project')
    try {
      const res = await api.post<Project>('/api/v1/projects', {
        name: customProjectName.trim(),
        runner_profile: 'unittest',
        files: filesDict,
      })
      notify('success', `Custom project "${res.data.name}" created!`)
      setActiveProjectId(res.data.project_id)
      setModalOpen(false)
      await refreshProjects()
      // Pre-select editable app files
      const editable = Object.keys(filesDict).filter((p) => p.startsWith('app/')).slice(0, 3)
      setSelectedEditablePaths(editable.length ? editable : [Object.keys(filesDict)[0]])
      setSourceFiles(filesDict)
      setSelectedFile(Object.keys(filesDict)[0])
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to create custom project.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  // Task Actions
  const handleQueuePlan = async () => {
    if (!activeTaskId) return
    setLoadingAction('queue-plan')
    try {
      await api.post(`/api/v1/coding-tasks/${activeTaskId}/plan`, {}, {
        headers: { 'Idempotency-Key': `key-${crypto.randomUUID()}` },
      })
      notify('info', 'Plan generation queued! Model is preparing implementation plan.')
      await loadTaskData(activeTaskId)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to queue plan.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  const handleApprovePlan = async () => {
    if (!activeTaskId || !currentTask?.plan) return
    setLoadingAction('approve-plan')
    try {
      // If user edited steps, update the plan first
      if (isEditingPlan) {
        await api.post(`/api/v1/coding-tasks/${activeTaskId}/plan/edit`, {
          ...currentTask.plan,
          steps: planSteps,
        })
        setIsEditingPlan(false)
      }

      // Obtain current plan hash from endpoint
      const planRes = await api.get<{ plan_hash: string }>(`/api/v1/coding-tasks/${activeTaskId}/plan`)
      const currentPlanHash = planRes.data.plan_hash

      await api.post(`/api/v1/coding-tasks/${activeTaskId}/approve`, {
        plan_hash: currentPlanHash,
      })
      notify('success', 'Plan approved! Task is ready for execution.')
      await loadTaskData(activeTaskId)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to approve plan.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  const handleStartTask = async () => {
    if (!activeTaskId) return
    setLoadingAction('start-task')
    try {
      await api.post(`/api/v1/coding-tasks/${activeTaskId}/start`, {}, {
        headers: { 'Idempotency-Key': `key-${crypto.randomUUID()}` },
      })
      notify('success', 'Task started! Worker is executing baseline and candidate loops.')
      await loadTaskData(activeTaskId)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to start task.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  const handlePauseTask = async () => {
    if (!activeTaskId) return
    setLoadingAction('pause-task')
    try {
      await api.post(`/api/v1/coding-tasks/${activeTaskId}/pause`)
      notify('info', 'Pause requested. Execution will pause safely at next action boundary.')
      await loadTaskData(activeTaskId)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to pause task.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  const handleResumeTask = async () => {
    if (!activeTaskId) return
    setLoadingAction('resume-task')
    try {
      await api.post(`/api/v1/coding-tasks/${activeTaskId}/resume`)
      notify('success', 'Task resumed successfully!')
      await loadTaskData(activeTaskId)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to resume task.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  const handleCancelTask = async () => {
    if (!activeTaskId) return
    if (!window.confirm('Cancel this task? In-flight container execution will be halted.')) return
    setLoadingAction('cancel-task')
    try {
      await api.post(`/api/v1/coding-tasks/${activeTaskId}/cancel`)
      notify('info', 'Cancellation request submitted.')
      await loadTaskData(activeTaskId)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to cancel task.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  const handleRestoreCheckpoint = async (checkpointId: string, expectedCheckpointId?: string) => {
    if (!activeTaskId) return
    if (!window.confirm('Restore this checkpoint? The code and stage will roll back to PAUSED without refunding spent budgets.')) return
    setLoadingAction(`restore-${checkpointId}`)
    try {
      await api.post(`/api/v1/coding-tasks/${activeTaskId}/restore`, {
        checkpoint_id: checkpointId,
        expected_checkpoint_id: expectedCheckpointId,
      })
      notify('success', `Restored to checkpoint ${checkpointId}. State is PAUSED. Lifetime usage was strictly preserved.`)
      await loadTaskData(activeTaskId)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to restore checkpoint.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  const handleDownloadDiff = () => {
    if (!taskChanges?.diff) {
      notify('info', 'No diff available to download yet.')
      return
    }
    const blob = new Blob([taskChanges.diff], { type: 'text/x-diff;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `task-${activeTaskId}-patch.diff`
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadBundleZip = async () => {
    if (!activeTaskId) return
    setLoadingAction('download-bundle')
    try {
      const response = await api.get(`/api/v1/coding-tasks/${activeTaskId}/bundle?format=zip`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `task-${activeTaskId}-bundle.zip`
      link.click()
      URL.revokeObjectURL(url)
      notify('success', 'Sanitized bundle ZIP downloaded.')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message || 'Failed to download bundle ZIP.'
      notify('error', msg)
    } finally {
      setLoadingAction(null)
    }
  }

  // Filtered Events
  const filteredEvents = useMemo(() => {
    if (eventFilter === 'ALL') return taskEvents
    return taskEvents.filter((ev) => ev.stage === eventFilter || ev.event_type.includes(eventFilter))
  }, [taskEvents, eventFilter])

  // Stepper calculations
  const STAGES = [
    { key: 'DRAFT', label: '1. Draft' },
    { key: 'PLAN', label: '2. Plan' },
    { key: 'APPROVAL', label: '3. Approval' },
    { key: 'BASELINE', label: '4. Baseline' },
    { key: 'EDIT', label: '5. Edit' },
    { key: 'CANDIDATE', label: '6. Candidate' },
    { key: 'FINAL', label: '7. Final' },
    { key: 'REVIEW_READY', label: '8. Review Ready' },
  ]

  const getStageStatus = (stageKey: string): 'completed' | 'active' | 'upcoming' => {
    if (!currentTask) return 'upcoming'
    const s = currentTask.state
    const n = currentTask.next_stage

    if (stageKey === 'DRAFT') {
      return s === 'DRAFT' ? 'active' : 'completed'
    }
    if (stageKey === 'PLAN') {
      if (s === 'DRAFT') return 'upcoming'
      if (s === 'PLANNING') return 'active'
      return 'completed'
    }
    if (stageKey === 'APPROVAL') {
      if (['DRAFT', 'PLANNING'].includes(s)) return 'upcoming'
      if (s === 'AWAITING_APPROVAL') return 'active'
      return 'completed'
    }
    if (stageKey === 'BASELINE') {
      if (['DRAFT', 'PLANNING', 'AWAITING_APPROVAL'].includes(s)) return 'upcoming'
      if (s === 'RUNNING' && n === 'BASELINE') return 'active'
      if (taskExecutions.some((e) => e.stage === 'BASELINE')) return 'completed'
      return 'upcoming'
    }
    if (stageKey === 'EDIT') {
      if (['DRAFT', 'PLANNING', 'AWAITING_APPROVAL'].includes(s)) return 'upcoming'
      if (s === 'RUNNING' && n === 'EDIT') return 'active'
      if (taskChanges?.diff) return 'completed'
      return 'upcoming'
    }
    if (stageKey === 'CANDIDATE') {
      if (['DRAFT', 'PLANNING', 'AWAITING_APPROVAL'].includes(s)) return 'upcoming'
      if (s === 'RUNNING' && n === 'CANDIDATE') return 'active'
      if (taskExecutions.some((e) => e.stage === 'CANDIDATE')) return 'completed'
      return 'upcoming'
    }
    if (stageKey === 'FINAL') {
      if (['DRAFT', 'PLANNING', 'AWAITING_APPROVAL'].includes(s)) return 'upcoming'
      if (s === 'RUNNING' && n === 'FINAL') return 'active'
      if (s === 'REVIEW_READY') return 'completed'
      return 'upcoming'
    }
    if (stageKey === 'REVIEW_READY') {
      return s === 'REVIEW_READY' ? 'active' : 'upcoming'
    }
    return 'upcoming'
  }

  return (
    <div className="coding-workspace">
      {/* ── Header & Status Bar ────────────────────────────────────────── */}
      <header className="workspace-header">
        <div className="workspace-title-group">
          <h1>
            <span>⚡ Autonomous Coding Agent</span>
            {currentTask && (
              <span className={`state-badge ${currentTask.state.toLowerCase()}`}>
                {currentTask.state.replace('_', ' ')}
              </span>
            )}
          </h1>
          <p className="workspace-subtitle">
            Autonomous multi-stage Python coding loop: plan review, model edits, isolated container execution, and verifiable diffs.
          </p>
        </div>

        <div className="workspace-top-controls">
          <div className="task-selector-group">
            <label htmlFor="task-select" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Active Task:</label>
            <select
              id="task-select"
              className="task-selector"
              value={activeTaskId || ''}
              onChange={(e) => setActiveTaskId(e.target.value || null)}
            >
              <option value="">+ New Task Flow</option>
              {tasksList.map((t) => (
                <option key={t.task_id} value={t.task_id}>
                  {t.task_id} ({t.state}) — {t.brief.task.slice(0, 30)}...
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setActiveTaskId(null)
              setSelectedSample(SAMPLE_PROJECTS[0])
            }}
          >
            + Start New Task
          </button>
        </div>
      </header>

      {/* ── System Status Strip ───────────────────────────────────────── */}
      <section className="system-status-strip" aria-label="System status">
        <div className="status-item">
          <span className={`status-dot-pulse ${ready?.provider.configured ? '' : 'offline'}`} />
          <span>
            <strong>Provider:</strong> {ready?.provider.name || 'nebius-token-factory'} ({ready?.provider.model_id || 'mistral-nemo-12b-instruct'})
          </span>
        </div>
        <div className="status-item">
          <span className={`status-dot-pulse ${ready?.runner.isolated_execution_available ? '' : 'offline'}`} />
          <span>
            <strong>Runner:</strong> {ready?.runner.mode || 'isolated'} {ready?.runner.isolated_execution_available ? '· Container Ready' : '· Host Mock'}
          </span>
        </div>
        <div className="status-item">
          <span className={`status-dot-pulse ${ready?.coding?.worker_alive || ready?.worker.alive ? '' : 'offline'}`} />
          <span>
            <strong>Worker:</strong> {ready?.coding?.worker_alive ? 'Active & Healthy' : (ready?.worker.alive ? 'Heartbeat Online' : 'Standby')}
          </span>
        </div>
        <div className="status-item">
          <span>
            <strong>Owner:</strong> <code style={{ fontSize: '0.72rem' }}>{owner.slice(0, 16)}...</code>
          </span>
        </div>
      </section>

      {/* ── Notification Banner ───────────────────────────────────────── */}
      {statusMessage && (
        <div className={`alert ${statusMessage.type === 'error' ? 'alert-danger' : 'alert-info'}`} role="status">
          <strong>{statusMessage.type.toUpperCase()}:</strong> {statusMessage.text}
        </div>
      )}

      {/* ── Multi-stage Visual Stepper ─────────────────────────────────── */}
      <section className="stepper-container" aria-label="Task stage progress">
        {STAGES.map((st, idx) => {
          const status = getStageStatus(st.key)
          return (
            <React.Fragment key={st.key}>
              <div className={`step-node ${status}`}>
                <div className="step-circle">
                  {status === 'completed' ? '✓' : idx + 1}
                </div>
                <span className="step-label">{st.label}</span>
              </div>
              {idx < STAGES.length - 1 && (
                <div className={`step-divider ${status === 'completed' ? 'filled' : ''}`} />
              )}
            </React.Fragment>
          )
        })}
      </section>

      {/* ── Live Control & Action Bar (When task exists) ────────────────── */}
      {currentTask && (
        <section className="live-controls-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <span>Task ID: <code>{currentTask.task_id}</code></span>
            <span>Next Stage: <strong>{currentTask.next_stage}</strong></span>
            {currentTask.pause_requested && <span className="badge badge-warning">PAUSE REQUESTED</span>}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {currentTask.state === 'DRAFT' && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingAction === 'queue-plan'}
                onClick={() => void handleQueuePlan()}
              >
                {loadingAction === 'queue-plan' ? 'Generating Plan...' : 'Generate Plan'}
              </button>
            )}

            {currentTask.state === 'AWAITING_APPROVAL' && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingAction === 'approve-plan'}
                onClick={() => void handleApprovePlan()}
              >
                {loadingAction === 'approve-plan' ? 'Approving...' : '✓ Approve Plan & Ready Run'}
              </button>
            )}

            {['QUEUED', 'AWAITING_APPROVAL'].includes(currentTask.state) && currentTask.approved_plan_hash && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingAction === 'start-task'}
                onClick={() => void handleStartTask()}
              >
                {loadingAction === 'start-task' ? 'Starting...' : '▶ Start Execution Loop'}
              </button>
            )}

            {currentTask.state === 'RUNNING' && (
              <button
                type="button"
                className="btn btn-secondary"
                disabled={loadingAction === 'pause-task' || currentTask.pause_requested}
                onClick={() => void handlePauseTask()}
              >
                ⏸ Pause
              </button>
            )}

            {currentTask.state === 'PAUSED' && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingAction === 'resume-task'}
                onClick={() => void handleResumeTask()}
              >
                ▶ Resume Execution
              </button>
            )}

            {!['REVIEW_READY', 'CANCELLED', 'FAILED'].includes(currentTask.state) && (
              <button
                type="button"
                className="btn btn-danger"
                disabled={loadingAction === 'cancel-task' || currentTask.state === 'CANCEL_PENDING'}
                onClick={() => void handleCancelTask()}
              >
                ⏹ Cancel Task
              </button>
            )}

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void loadTaskData(currentTask.task_id)}
            >
              ↻ Refresh
            </button>
          </div>
        </section>
      )}

      {/* ── Resource Usage Meters ─────────────────────────────────────── */}
      {taskUsage && (
        <section className="usage-meters-grid" aria-label="Usage and budget meters">
          <div className="meter-card">
            <span className="meter-title">Model Calls</span>
            <span className="meter-value">{taskUsage.counters.model_calls} / {taskUsage.limits.model_calls}</span>
            <div className="meter-bar-track">
              <div
                className="meter-bar-fill"
                style={{ width: `${Math.min(100, (taskUsage.counters.model_calls / taskUsage.limits.model_calls) * 100)}%` }}
              />
            </div>
          </div>
          <div className="meter-card">
            <span className="meter-title">Patch Attempts</span>
            <span className="meter-value">{taskUsage.counters.patch_attempts} / {taskUsage.limits.patch_attempts}</span>
            <div className="meter-bar-track">
              <div
                className="meter-bar-fill"
                style={{ width: `${Math.min(100, (taskUsage.counters.patch_attempts / taskUsage.limits.patch_attempts) * 100)}%` }}
              />
            </div>
          </div>
          <div className="meter-card">
            <span className="meter-title">Container Executions</span>
            <span className="meter-value">{taskUsage.counters.executions} / {taskUsage.limits.executions}</span>
            <div className="meter-bar-track">
              <div
                className="meter-bar-fill"
                style={{ width: `${Math.min(100, (taskUsage.counters.executions / taskUsage.limits.executions) * 100)}%` }}
              />
            </div>
          </div>
          <div className="meter-card">
            <span className="meter-title">Active Time</span>
            <span className="meter-value">{Math.round(taskUsage.counters.active_seconds)}s / {taskUsage.limits.active_seconds}s</span>
            <div className="meter-bar-track">
              <div
                className="meter-bar-fill"
                style={{ width: `${Math.min(100, (taskUsage.counters.active_seconds / taskUsage.limits.active_seconds) * 100)}%` }}
              />
            </div>
          </div>
          <div className="meter-card">
            <span className="meter-title">Recorded Tokens</span>
            <span className="meter-value">{taskUsage.recorded_tokens.toLocaleString()}</span>
            <small style={{ fontSize: '0.68rem', color: 'var(--text)' }}>Cost: UNKNOWN · Hard cap: False</small>
          </div>
        </section>
      )}

      {/* ── Main Two-Column Work Area ─────────────────────────────────── */}
      <div className="workspace-grid">
        {/* Left Column: Project Intake & Source Explorer & Task Brief */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Project & Source Card */}
          <article className="workspace-card">
            <div className="card-header-row">
              <h2>📁 Project Source Explorer</h2>
              <div className="sample-projects-bar">
                {SAMPLE_PROJECTS.map((sp) => (
                  <button
                    key={sp.id}
                    type="button"
                    className={`sample-chip ${selectedSample.id === sp.id && !activeTaskId ? 'active' : ''}`}
                    onClick={() => handleSelectSample(sp)}
                  >
                    <span>{sp.name}</span>
                    <span className="badge badge-neutral" style={{ fontSize: '0.62rem' }}>{sp.tag}</span>
                  </button>
                ))}
                <button
                  type="button"
                  className="sample-chip"
                  onClick={() => setModalOpen(true)}
                >
                  + Custom Project
                </button>
                {projectsList.length > 0 && (
                  <select
                    className="sample-chip"
                    aria-label="Uploaded Projects"
                    value={activeProjectId || ''}
                    onChange={(e) => {
                      const pid = e.target.value
                      if (!pid) return
                      const found = projectsList.find((p) => p.project_id === pid)
                      if (found) {
                        setActiveProjectId(pid)
                        if (found.files) {
                          setSourceFiles(found.files)
                          setSelectedFile(Object.keys(found.files)[0] || '')
                        }
                      }
                    }}
                  >
                    <option value="">Uploaded Projects ({projectsList.length})</option>
                    {projectsList.map((p) => (
                      <option key={p.project_id} value={p.project_id}>
                        {p.name} ({p.project_id.slice(0, 10)})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <p style={{ fontSize: '0.82rem', color: 'var(--text)' }}>
              Project files with strict policy enforcement: <code>app/</code> files are candidate-editable; <code>tests/</code> files are protected verifications.
            </p>

            {/* Source Browser */}
            <div className="source-browser-container">
              <div className="file-tree-pane">
                {Object.keys(sourceFiles).map((filePath) => {
                  const isApp = filePath.startsWith('app/')
                  const isTest = filePath.startsWith('tests/')
                  return (
                    <button
                      key={filePath}
                      type="button"
                      className={`file-item-btn ${selectedFile === filePath ? 'active' : ''}`}
                      onClick={() => setSelectedFile(filePath)}
                    >
                      <span>{filePath}</span>
                      <span className={`file-badge ${isApp ? 'editable' : (isTest ? 'protected' : '')}`}>
                        {isApp ? 'edit' : (isTest ? 'test' : 'file')}
                      </span>
                    </button>
                  )
                })}
              </div>

              <div className="code-viewer-pane">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', color: '#688998', fontSize: '0.72rem' }}>
                  <span>{selectedFile || 'Select a file'}</span>
                  <span>{sourceFiles[selectedFile]?.length || 0} bytes</span>
                </div>
                {selectedFile && sourceFiles[selectedFile] ? (
                  sourceFiles[selectedFile].split('\n').map((line, idx) => (
                    <div key={idx} className="code-line">
                      <span className="line-number">{idx + 1}</span>
                      <span>{line || ' '}</span>
                    </div>
                  ))
                ) : (
                  <p style={{ color: '#64748b' }}>Select a file from the explorer to view contents.</p>
                )}
              </div>
            </div>
          </article>

          {/* Task Brief & Creation Card (When in Draft / Setup) */}
          {(!currentTask || currentTask.state === 'DRAFT') && (
            <article className="workspace-card">
              <div className="card-header-row">
                <h2>📝 Task Brief & Instructions</h2>
                <span className="badge badge-neutral">Profile: unittest</span>
              </div>

              <form className="task-form" onSubmit={(e) => { e.preventDefault(); void handleCreateTaskForSample() }}>
                <div className="form-field">
                  <label htmlFor="task-prompt">Instruction Prompt:</label>
                  <textarea
                    id="task-prompt"
                    className="form-textarea"
                    value={taskPrompt}
                    onChange={(e) => setTaskPrompt(e.target.value)}
                    placeholder="Describe the bug fix or feature change in detail..."
                    rows={3}
                  />
                </div>

                <div className="form-field">
                  <label>Editable Paths (Max 3 files in <code>app/</code>):</label>
                  <div className="editable-paths-group">
                    {Object.keys(sourceFiles)
                      .filter((p) => p.startsWith('app/'))
                      .map((p) => {
                        const isSelected = selectedEditablePaths.includes(p)
                        return (
                          <label key={p} className={`path-checkbox-label ${isSelected ? 'selected' : ''}`}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  if (selectedEditablePaths.length < 3) {
                                    setSelectedEditablePaths([...selectedEditablePaths, p])
                                  } else {
                                    notify('info', 'Maximum 3 editable paths allowed.')
                                  }
                                } else {
                                  setSelectedEditablePaths(selectedEditablePaths.filter((item) => item !== p))
                                }
                              }}
                            />
                            {p}
                          </label>
                        )
                      })}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                  <small style={{ color: 'var(--text)' }}>
                    Hard limits: 4 model calls · 2 patch attempts · 4 test runs · 300s window.
                  </small>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loadingAction === 'create-task' || !taskPrompt.trim() || selectedEditablePaths.length === 0}
                  >
                    {loadingAction === 'create-task' ? 'Creating...' : 'Create Coding Task'}
                  </button>
                </div>
              </form>
            </article>
          )}

          {/* Plan Review Card */}
          {currentTask && currentTask.plan && (
            <article className="workspace-card">
              <div className="card-header-row">
                <h2>📋 Model Implementation Plan</h2>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {currentTask.state === 'AWAITING_APPROVAL' && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setIsEditingPlan(!isEditingPlan)}
                    >
                      {isEditingPlan ? 'Done Editing' : 'Edit Plan Steps'}
                    </button>
                  )}
                  {currentTask.approved_plan_hash ? (
                    <span className="badge badge-success">APPROVED</span>
                  ) : (
                    <span className="badge badge-warning">AWAITING REVIEW</span>
                  )}
                </div>
              </div>

              <div className="plan-container">
                <p className="plan-summary-text">{currentTask.plan.summary}</p>
                <div style={{ fontSize: '0.78rem', color: 'var(--text)' }}>
                  Targeted Paths: {currentTask.plan.editable_paths.map((p) => <code key={p} style={{ marginRight: '6px' }}>{p}</code>)}
                </div>

                <ol className="plan-steps-list">
                  {planSteps.map((step, idx) => (
                    <li key={idx}>
                      {isEditingPlan ? (
                        <input
                          type="text"
                          value={step}
                          style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border)' }}
                          onChange={(e) => {
                            const updated = [...planSteps]
                            updated[idx] = e.target.value
                            setPlanSteps(updated)
                          }}
                        />
                      ) : (
                        <span>{step}</span>
                      )}
                    </li>
                  ))}
                </ol>

                {currentTask.state === 'AWAITING_APPROVAL' && (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={loadingAction === 'approve-plan'}
                      onClick={() => void handleApprovePlan()}
                    >
                      {loadingAction === 'approve-plan' ? 'Approving...' : '✓ Approve Plan & Ready Run'}
                    </button>
                  </div>
                )}
              </div>
            </article>
          )}

          {/* Test Execution Console */}
          {taskExecutions.length > 0 && (
            <article className="workspace-card">
              <div className="card-header-row">
                <h2>🧪 Test Execution Console ({taskExecutions.length})</h2>
                <span className="badge badge-neutral">Isolated Docker / Runner</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {taskExecutions.map((exec) => {
                  const passed = exec.result?.passed ?? (exec.result?.exit_code === 0)
                  return (
                    <div key={exec.action_id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                        <span>
                          <strong>{exec.stage} Execution</strong> · Exit Code: <code>{exec.result?.exit_code ?? 'None'}</code>
                        </span>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span>{exec.result?.duration_ms ?? 0} ms</span>
                          <span className={`badge ${passed ? 'badge-success' : 'badge-danger'}`}>
                            {passed ? 'PASSED' : 'FAILED'}
                          </span>
                        </div>
                      </div>

                      <pre className="terminal-output" tabIndex={0} aria-label={`Test output for ${exec.stage}`}>
                        {exec.result?.stdout || exec.result?.stderr || 'No console output recorded for this run.'}
                      </pre>
                    </div>
                  )
                })}
              </div>
            </article>
          )}
        </div>

        {/* Right Column: Changes & Diff Viewer, Checkpoints, and Live Activity Log */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Changes & Unified Diff Viewer Card */}
          <article className="workspace-card">
            <div className="card-header-row">
              <h2>🔍 Code Changes & Tested Diff</h2>
              <div style={{ display: 'flex', gap: '8px' }}>
                {taskChanges?.tested_final && (
                  <span className="badge badge-success">TESTED FINAL PASS</span>
                )}
                {taskChanges?.diff && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ minHeight: '32px', padding: '4px 10px', fontSize: '0.72rem' }}
                    onClick={handleDownloadDiff}
                  >
                    Download .diff
                  </button>
                )}
              </div>
            </div>

            {taskChanges && taskChanges.diff ? (
              <div className="diff-viewer">
                <div className="diff-toolbar">
                  <span>Author: {taskChanges.author || 'nvidia/mistral-nemo-12b-instruct'}</span>
                  <span>Base: <code>{taskChanges.base_source_hash.slice(0, 10)}...</code></span>
                </div>
                <div tabIndex={0} aria-label="Unified diff view">
                  {taskChanges.diff.split('\n').map((line, idx) => {
                    let lineClass = ''
                    if (line.startsWith('+') && !line.startsWith('+++')) lineClass = 'addition'
                    else if (line.startsWith('-') && !line.startsWith('---')) lineClass = 'deletion'
                    else if (line.startsWith('@@') || line.startsWith('diff --git')) lineClass = 'header'
                    return (
                      <div key={idx} className={`diff-line ${lineClass}`}>
                        {line || ' '}
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text)', fontSize: '0.85rem' }}>
                No candidate edits generated yet. Once the agent executes an edit action, the unified diff and verdict will render here.
              </p>
            )}
          </article>

          {/* Export Bundle & Downloads */}
          {currentTask && (
            <article className="workspace-card">
              <div className="card-header-row">
                <h2>📦 Export Task Evidence Bundle</h2>
                <span className="badge badge-neutral">Sanitized & Authenticated</span>
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text)' }}>
                Export contains <code>manifest.json</code>, <code>patch.diff</code>, <code>plan.json</code>, test execution reports, event trajectory, and markdown summary. Credentials strictly excluded.
              </p>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={loadingAction === 'download-bundle'}
                  onClick={() => void handleDownloadBundleZip()}
                >
                  {loadingAction === 'download-bundle' ? 'Downloading...' : '⬇ Download Complete Bundle (.zip)'}
                </button>
                {taskChanges?.diff && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleDownloadDiff}
                  >
                    ⬇ Download Patch (.diff)
                  </button>
                )}
              </div>
            </article>
          )}

          {/* Checkpoint History & CAS Restore Card */}
          <article className="workspace-card">
            <div className="card-header-row">
              <h2>⏪ Versioned Checkpoint Timeline ({taskCheckpoints.length})</h2>
              <span className="badge badge-neutral">Monotonic Lifetime Budgets</span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text)' }}>
              Conflict-checked compare-and-swap (CAS) rollback. Restores stage & code state to <code>PAUSED</code>; lifetime resource meters never decrement.
            </p>

            <div className="checkpoint-timeline">
              {taskCheckpoints.map((cp) => (
                <div key={cp.checkpoint_id} className="checkpoint-row">
                  <div>
                    <strong>Seq #{cp.sequence}</strong> · <span>{cp.stage}</span> ·{' '}
                    <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>{cp.state}</span>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text)', marginTop: '2px' }}>
                      ID: <code>{cp.checkpoint_id}</code> · {new Date(cp.created_at).toLocaleTimeString()}
                    </div>
                  </div>

                  {currentTask?.state !== 'RUNNING' && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ minHeight: '32px', padding: '4px 10px', fontSize: '0.72rem' }}
                      disabled={loadingAction === `restore-${cp.checkpoint_id}`}
                      onClick={() => void handleRestoreCheckpoint(cp.checkpoint_id, currentTask?.checkpoint ? (currentTask.checkpoint as unknown as { checkpoint_id?: string }).checkpoint_id : undefined)}
                    >
                      Restore (Rollback)
                    </button>
                  )}
                </div>
              ))}
              {taskCheckpoints.length === 0 && (
                <p style={{ color: 'var(--text)', fontSize: '0.82rem' }}>No checkpoints established yet. Checkpoints are recorded upon plan approval and completed actions.</p>
              )}
            </div>
          </article>

          {/* Live Activity & Event Stream Card */}
          <article className="workspace-card">
            <div className="card-header-row">
              <h2>📡 Live Event Log ({filteredEvents.length})</h2>
              <div style={{ display: 'flex', gap: '6px' }}>
                <select
                  value={eventFilter}
                  onChange={(e) => setEventFilter(e.target.value)}
                  style={{ minWidth: '120px', minHeight: '32px', fontSize: '0.75rem', padding: '4px 8px' }}
                >
                  <option value="ALL">All Stages</option>
                  <option value="BASELINE">Baseline</option>
                  <option value="EDIT">Edit</option>
                  <option value="CANDIDATE">Candidate</option>
                  <option value="FINAL">Final</option>
                </select>
              </div>
            </div>

            <div className="event-log" style={{ borderTop: 'none', paddingTop: 0 }}>
              <ol style={{ maxHeight: '260px' }}>
                {filteredEvents.map((ev) => (
                  <li key={ev.sequence}>
                    <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>#{ev.sequence}</span>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-h)' }}>{ev.event_type}</span>
                      <small style={{ color: 'var(--text)', fontSize: '0.72rem' }}>
                        Stage: {ev.stage} {ev.payload && Object.keys(ev.payload).length > 0 ? `· ${JSON.stringify(ev.payload).slice(0, 60)}...` : ''}
                      </small>
                    </div>
                    <time>{new Date(ev.created_at).toLocaleTimeString()}</time>
                  </li>
                ))}
                {filteredEvents.length === 0 && (
                  <p style={{ color: 'var(--text)', fontSize: '0.82rem' }}>No events recorded for this task yet.</p>
                )}
              </ol>
            </div>
          </article>
        </div>
      </div>

      {/* ── Custom Project Intake Modal ─────────────────────────────────── */}
      {modalOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Custom Project Intake">
          <div className="modal-content">
            <div className="card-header-row">
              <h2>Upload Custom Project</h2>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ minHeight: '30px', padding: '4px 10px' }}
                onClick={() => setModalOpen(false)}
              >
                ✕ Close
              </button>
            </div>

            <p style={{ fontSize: '0.82rem', color: 'var(--text)' }}>
              Intake limits: At most 20 files, max 24 KiB per file, max 128 KiB total. Relative paths in <code>app/</code> and <code>tests/</code> only.
            </p>

            <div className="task-form" style={{ marginTop: '16px' }}>
              <div className="form-field">
                <label htmlFor="custom-proj-name">Project Name:</label>
                <input
                  id="custom-proj-name"
                  type="text"
                  value={customProjectName}
                  onChange={(e) => setCustomProjectName(e.target.value)}
                  style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border)' }}
                />
              </div>

              <div className="form-field">
                <label>Files ({customFiles.length}/20):</label>
                {customFiles.map((file, idx) => (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="text"
                        placeholder="e.g. app/module.py"
                        value={file.path}
                        style={{ flex: 1, padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border)', font: '0.8rem var(--mono)' }}
                        onChange={(e) => {
                          const updated = [...customFiles]
                          updated[idx].path = e.target.value
                          setCustomFiles(updated)
                        }}
                      />
                      {customFiles.length > 1 && (
                        <button
                          type="button"
                          className="btn btn-danger"
                          style={{ minHeight: '30px', padding: '4px 8px' }}
                          onClick={() => setCustomFiles(customFiles.filter((_, i) => i !== idx))}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    <textarea
                      rows={5}
                      style={{ padding: '8px', borderRadius: '4px', border: '1px solid var(--border)', font: '0.78rem var(--mono)' }}
                      value={file.content}
                      onChange={(e) => {
                        const updated = [...customFiles]
                        updated[idx].content = e.target.value
                        setCustomFiles(updated)
                      }}
                    />
                  </div>
                ))}

                {customFiles.length < 20 && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ alignSelf: 'flex-start' }}
                    onClick={() => setCustomFiles([...customFiles, { path: `app/module_${customFiles.length + 1}.py`, content: '' }])}
                  >
                    + Add Another File
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '14px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={loadingAction === 'create-project'}
                  onClick={() => void handleCreateCustomProject()}
                >
                  {loadingAction === 'create-project' ? 'Validating & Uploading...' : 'Upload & Select Project'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
