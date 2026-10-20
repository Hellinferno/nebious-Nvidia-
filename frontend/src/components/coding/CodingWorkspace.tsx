import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { AxiosInstance } from 'axios'
import './CodingWorkspace.css'
import { SAMPLE_PROJECTS } from './sampleProjects'
import type { SampleProjectDef } from './sampleProjects'
import { TaskComposer } from './TaskComposer'
import { AgentSettings } from './AgentSettings'
import { AgentExtensions } from './AgentExtensions'
import {
  compileAgentPreferences, DEFAULT_AGENT_PREFERENCES, deleteAgentProfile, duplicateAgentProfile,
  exportAgentProfile, MAX_PROFILE_IMPORT_LENGTH, parseProfileImport, readAgentProfiles,
  readDefaultAgentProfile, saveAgentProfile, setDefaultAgentProfile,
} from './agentProfiles'
import type { AgentPreferences, AgentProfile } from './agentProfiles'
import { ExecutionResults } from './ExecutionResults'
import { formatTimestamp, taskResultMessage } from './presentation'
import { instructionStorageKey, readSavedInstructions, recipeLabel } from './taskRecipes'
import { sameReviewedPlan } from './planReview'
import type {
  CheckpointRecord,
  CodingEvent,
  CodingPreferences,
  CodingPlan,
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
  const [draftProject, setDraftProject] = useState<Project | null>(null)

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
  const [initialProfile] = useState(() => readDefaultAgentProfile(owner))
  const [agentPreferences, setAgentPreferences] = useState<AgentPreferences>(() => initialProfile?.preferences || {
    ...DEFAULT_AGENT_PREFERENCES, workflow: 'bugfix', instructions: readSavedInstructions(owner) || '',
  })
  const workflow = agentPreferences.workflow
  const instructions = agentPreferences.instructions
  const setWorkflow = (value: CodingPreferences['workflow']) => setAgentPreferences((current) => ({ ...current, workflow: value }))
  const setInstructions = (value: string) => setAgentPreferences((current) => ({ ...current, instructions: value }))
  const [agentProfiles, setAgentProfiles] = useState(() => readAgentProfiles(owner))
  const [selectedProfileId, setSelectedProfileId] = useState(initialProfile?.id || '')
  const [defaultProfileId, setDefaultProfileId] = useState<string | null>(initialProfile?.id || null)
  const [profileName, setProfileName] = useState(initialProfile?.name || '')
  const [externalContext, setExternalContext] = useState<NonNullable<CodingPreferences['context']>>([])
  const [savedInstructions, setSavedInstructions] = useState<string | null>(() => readSavedInstructions(owner))

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
        setTasksList((tasks) => tasks.map((task) => task.task_id === taskId ? taskRes.value.data : task))
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
          if (!activeProjectId) {
            setSourceFiles(selectedSample.files)
            setSelectedFile(Object.keys(selectedSample.files)[0] || '')
          }
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
          setTasksList((tasks) => tasks.map((task) => task.task_id === activeTaskId ? taskRes.value.data : task))
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
  }, [activeTaskId, activeProjectId, api, selectedSample])

  useEffect(() => {
    if (!activeProjectId || activeTaskId) return
    let ignore = false
    const loadProject = async () => {
      try {
        const response = await api.get<Project>(`/api/v1/projects/${activeProjectId}`)
        if (ignore) return
        const files = response.data.files || {}
        setDraftProject(response.data)
        setSourceFiles(files)
        setSelectedFile(Object.keys(files)[0] || '')
        setSelectedEditablePaths(Object.keys(files).filter((path) => path.startsWith('app/')).slice(0, 3))
      } catch {
        if (!ignore) {
          setDraftProject(null)
          setSourceFiles({})
          setStatusMessage({ type: 'error', text: 'Could not load the selected project. Select it again or choose a sample.' })
        }
      }
    }
    void loadProject()
    return () => { ignore = true }
  }, [activeProjectId, activeTaskId, api])

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
    setExternalContext([])
    setActiveTaskId(null)
    setActiveProjectId(null)
    setDraftProject(null)
    setSelectedSample(sample)
    setTaskPrompt(sample.suggestedPrompt)
    if (!selectedProfileId) setWorkflow(sample.tag === 'Feature' ? 'feature' : 'bugfix')
    setSelectedEditablePaths(sample.defaultEditablePaths)
    setSourceFiles(sample.files)
    setSelectedFile(Object.keys(sample.files)[0] || '')
  }

  const handleSaveInstructions = () => {
    try {
      localStorage.setItem(instructionStorageKey(owner), instructions)
      setSavedInstructions(instructions)
      notify('success', 'Instructions saved in this browser for future tasks.')
    } catch {
      notify('error', 'Browser storage is unavailable. Your instructions will still be included in this task.')
    }
  }

  const handleForgetInstructions = () => {
    try {
      localStorage.removeItem(instructionStorageKey(owner))
      setSavedInstructions(null)
      setInstructions('')
      notify('info', 'Saved instructions removed. Existing tasks are unchanged.')
    } catch {
      notify('error', 'Browser storage is unavailable; saved instructions could not be removed.')
    }
  }

  const applyAgentProfile = (profile: AgentProfile) => {
    setSelectedProfileId(profile.id)
    setProfileName(profile.name)
    setAgentPreferences(profile.preferences)
  }

  const profileAction = (action: () => void) => {
    try {
      action()
      setAgentProfiles(readAgentProfiles(owner))
      setDefaultProfileId(readDefaultAgentProfile(owner)?.id || null)
    } catch (error) {
      notify('error', error instanceof Error ? error.message : 'Could not update the profile.')
    }
  }

  const handleSaveProfile = (asNew: boolean) => profileAction(() => {
    const profile = saveAgentProfile(owner, { name: profileName, preferences: agentPreferences }, asNew ? undefined : selectedProfileId || undefined)
    applyAgentProfile(profile)
    notify('success', 'Agent profile saved in this browser. Existing tasks are unchanged.')
  })

  const handleExportProfile = () => profileAction(() => {
    const contents = exportAgentProfile({ id: `profile-${crypto.randomUUID()}`, name: profileName, preferences: agentPreferences })
    const url = URL.createObjectURL(new Blob([contents], { type: 'application/json;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `${profileName.replace(/[^a-zA-Z0-9_-]+/g, '-').slice(0, 60) || 'agent-profile'}.json`
    link.click()
    URL.revokeObjectURL(url)
  })

  const handleImportProfile = async (file: File) => {
    try {
      if (file.size > MAX_PROFILE_IMPORT_LENGTH) throw new Error('Profile files must be at most 16 KiB.')
      const configuration = parseProfileImport(await file.text())
      profileAction(() => {
        const profile = saveAgentProfile(owner, configuration)
        applyAgentProfile(profile)
        notify('success', 'Profile imported and selected. No task was started and no code was installed.')
      })
    } catch (error) {
      notify('error', error instanceof Error ? error.message : 'Could not import the profile.')
    }
  }

  // Create Project & Task from Selected Sample or Upload
  const handleCreateTaskForSample = async () => {
    if (activeProjectId && draftProject?.project_id !== activeProjectId) {
      notify('error', 'Wait for the selected project to load before creating a task.')
      return
    }
    setLoadingAction('create-task')
    try {
      const preferences: CodingPreferences = { ...compileAgentPreferences(agentPreferences), ...(externalContext.length ? { context: externalContext } : {}) }
      let targetProjectId: string | undefined
      let targetFixtureId: string | undefined
      let currentSourceHash = ''

      if (activeProjectId && draftProject) {
        targetProjectId = draftProject.project_id
        currentSourceHash = draftProject.source_hash
      } else if (selectedSample.isFixture && selectedSample.fixtureId) {
        targetFixtureId = selectedSample.fixtureId
        const exRes = await api.get<Array<{ id: string; source_hash: string }>>('/api/v1/examples')
        const found = exRes.data.find((example) => example.id === selectedSample.fixtureId)
        if (!found) throw new Error('The prepared project is unavailable.')
        currentSourceHash = found.source_hash
      } else {
        // Create or ensure the sample project exists on the backend
        const projRes = await api.post<Project>('/api/v1/projects', {
          name: selectedSample.name,
          runner_profile: selectedSample.runnerProfile,
          files: selectedSample.files,
        })
        targetProjectId = projRes.data.project_id
        currentSourceHash = projRes.data.source_hash
        setDraftProject(projRes.data)
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
          preferences,
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
      setExternalContext([])
      setActiveProjectId(res.data.project_id)
      setActiveTaskId(null)
      setDraftProject(res.data)
      setModalOpen(false)
      await refreshProjects()
      // Pre-select editable app files
      const editable = Object.keys(filesDict).filter((p) => p.startsWith('app/')).slice(0, 3)
      setSelectedEditablePaths(editable)
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
    const reviewedPlan = { ...currentTask.plan, steps: planSteps }
    setLoadingAction('approve-plan')
    try {
      // If user edited steps, update the plan first
      if (JSON.stringify(planSteps) !== JSON.stringify(currentTask.plan.steps)) {
        await api.post(`/api/v1/coding-tasks/${activeTaskId}/plan/edit`, {
          ...reviewedPlan,
        })
        setIsEditingPlan(false)
      }

      // Obtain current plan hash from endpoint
      const planRes = await api.get<{ plan: CodingPlan | null; plan_hash: string }>(`/api/v1/coding-tasks/${activeTaskId}/plan`)
      if (!sameReviewedPlan(reviewedPlan, planRes.data.plan)) {
        notify('error', 'The plan changed since you reviewed it. Review the updated plan before approving.')
        await loadTaskData(activeTaskId)
        return
      }
      const currentPlanHash = planRes.data.plan_hash

      await api.post(`/api/v1/coding-tasks/${activeTaskId}/approve`, {
        plan_hash: currentPlanHash,
      })
      notify('success', currentTask.brief.preferences?.mode === 'plan_only'
        ? 'Reviewed plan saved. This task cannot edit code or run tests.'
        : 'Plan approved. Choose Start task when you are ready to run it.')
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
    return taskEvents.filter((event) => (event.stage || event.payload.stage) === eventFilter || event.event_type.includes(eventFilter))
  }, [taskEvents, eventFilter])

  const codingBlockedReason = !ready
    ? 'Checking service availability. You can prepare your task while you wait.'
    : !ready.coding
      ? 'This deployment does not yet expose the coding-task service. You can explore the workspace, but task creation is unavailable.'
      : !ready.coding.enabled
        ? 'Coding tasks are disabled on this deployment.'
        : ready.coding.blocked_reason
          ? 'The coding service is not accepting new work. Its provider, runner, session window or daily allowance needs attention.'
          : null

  const draftBlockedReason = codingBlockedReason || (activeProjectId && draftProject?.project_id !== activeProjectId
    ? 'Loading your selected project. Its exact source revision is required before creating a task.' : null)

  let preferencesError: string | null = null
  try {
    compileAgentPreferences(agentPreferences)
  } catch (error) {
    preferencesError = error instanceof Error ? error.message : 'Check your agent settings.'
  }
  const selectedAgentProfile = agentProfiles.find((profile) => profile.id === selectedProfileId)
  const profileModified = !!selectedAgentProfile && (profileName.trim() !== selectedAgentProfile.name
    || JSON.stringify(agentPreferences) !== JSON.stringify(selectedAgentProfile.preferences))
  const planOnlyTask = currentTask?.brief.preferences?.mode === 'plan_only'
  const planEditsPending = !!currentTask?.plan && JSON.stringify(planSteps) !== JSON.stringify(currentTask.plan.steps)

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
      if (['PLANNING', 'QUEUED', 'RUNNING'].includes(s) && n === 'PLAN') return 'active'
      return 'completed'
    }
    if (stageKey === 'APPROVAL') {
      if (['DRAFT', 'PLANNING'].includes(s) || n === 'PLAN') return 'upcoming'
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
            <span>Build with an agent. Stay in control.</span>
            {currentTask && (
              <span className={`state-badge ${currentTask.state.toLowerCase()}`}>
                {currentTask.state.replace('_', ' ')}
              </span>
            )}
          </h1>
          <p className="workspace-subtitle">
            Choose a Python project, set your conventions, and review a plan before the agent changes code.
          </p>
        </div>

        <div className="workspace-top-controls">
          <div className="task-selector-group">
            <label htmlFor="task-select" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Active Task:</label>
            <select
              id="task-select"
              className="task-selector"
              value={activeTaskId || ''}
              onChange={(event) => event.target.value ? setActiveTaskId(event.target.value) : handleSelectSample(SAMPLE_PROJECTS[0])}
            >
              <option value="">New task</option>
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
              handleSelectSample(SAMPLE_PROJECTS[0])
            }}
          >
            + New task
          </button>
        </div>
      </header>

      {/* ── System Status Strip ───────────────────────────────────────── */}
      <section className="system-status-strip" aria-label="System status">
        <div className="status-item">
          <span className={`status-dot-pulse ${ready?.provider.configured ? '' : 'offline'}`} />
          <span>
            <strong>Model:</strong> {ready?.provider.model_id || 'Not configured'}
          </span>
        </div>
        <div className="status-item">
          <span className={`status-dot-pulse ${ready?.runner.isolated_execution_available ? '' : 'offline'}`} />
          <span>
            <strong>Execution:</strong> {ready?.runner.isolated_execution_available ? 'Isolated runner available' : 'Isolated runner unavailable'}
          </span>
        </div>
        <div className="status-item">
          <span className={`status-dot-pulse ${ready?.coding?.worker_alive ? '' : 'offline'}`} />
          <span>
            <strong>Task worker:</strong> {ready?.coding?.worker_alive ? 'Online' : 'Not confirmed'}
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
      {currentTask && <section className="stepper-container" aria-label="Task stage progress">
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
      </section>}

      {currentTask && (
        <section className="task-context-summary" aria-label="Task instructions">
          <div className="task-context-heading"><strong>{recipeLabel(currentTask.brief.preferences?.workflow)}</strong><span>Instructions pinned to this task</span></div>
          {planOnlyTask && <p className="plan-only-notice">Plan only: edits and test executions are disabled for this task, including direct API requests.</p>}
          <p className="field-help">Harness: {currentTask.brief.preferences?.harness || 'bounded-v1'} · Skills: {currentTask.brief.preferences?.skills?.map((skill) => skill.name).join(', ') || 'none'} · MCP snapshots: {currentTask.brief.preferences?.context?.length || 0}</p>
          <p className="field-help">Pinned budget: {currentTask.limits.model_calls} model calls · {currentTask.limits.patch_attempts} edits · {currentTask.limits.executions} test executions · {currentTask.limits.active_seconds} active seconds.</p>
          <p>{currentTask.brief.task}</p>
          {currentTask.brief.preferences?.instructions && (
            <details><summary>Coding conventions</summary><p>{currentTask.brief.preferences.instructions}</p></details>
          )}
          {taskResultMessage(currentTask.result) && <p className="task-result-message" role="status">{taskResultMessage(currentTask.result)}</p>}
          <p className="field-help">Review generated changes and test results before accepting them. Passing checks do not prove every requirement.</p>
        </section>
      )}

      {/* ── Live Control & Action Bar (When task exists) ────────────────── */}
      {currentTask && (
        <>
        {codingBlockedReason && <p className="composer-blocked" role="status">{codingBlockedReason}</p>}
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
                disabled={loadingAction === 'queue-plan' || !!codingBlockedReason}
                onClick={() => void handleQueuePlan()}
              >
                {loadingAction === 'queue-plan' ? 'Generating Plan...' : 'Generate Plan'}
              </button>
            )}

            {(currentTask.state === 'AWAITING_APPROVAL' || (currentTask.state === 'APPROVED' && planEditsPending)) && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingAction === 'approve-plan'}
                onClick={() => void handleApprovePlan()}
              >
                {loadingAction === 'approve-plan' ? 'Saving…' : planOnlyTask ? 'Save reviewed plan' : 'Approve plan'}
              </button>
            )}

            {!planOnlyTask && currentTask.state === 'APPROVED' && currentTask.approved_plan_hash && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingAction === 'start-task' || !!codingBlockedReason || isEditingPlan || planEditsPending}
                onClick={() => void handleStartTask()}
              >
                {loadingAction === 'start-task' ? 'Starting…' : 'Start task'}
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

            {currentTask.state === 'PAUSED' && (!planOnlyTask || currentTask.next_stage === 'PLAN') && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingAction === 'resume-task'}
                onClick={() => void handleResumeTask()}
              >
                {planOnlyTask ? 'Resume planning' : '▶ Resume Execution'}
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
        </>
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
              <h2>Your project</h2>
              <div className="sample-projects-bar">
                {SAMPLE_PROJECTS.map((sp) => (
                  <button
                    key={sp.id}
                    type="button"
                    className={`sample-chip ${selectedSample.id === sp.id && !activeTaskId && !activeProjectId ? 'active' : ''}`}
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
                        setExternalContext([])
                        setActiveTaskId(null)
                        setDraftProject(null)
                        setActiveProjectId(pid)
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
              Browse your source before creating a task. Select up to three <code>app/</code> files for changes; imported <code>tests/</code> stay read-only.
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
                  <span>{new TextEncoder().encode(sourceFiles[selectedFile] || '').length} bytes</span>
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
          {/* Plan Review Card */}
          {currentTask && currentTask.plan && (
            <article className="workspace-card">
              <div className="card-header-row">
                <h2>Review the plan</h2>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {['AWAITING_APPROVAL', 'APPROVED'].includes(currentTask.state) && (
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
                <p className="plan-summary-text">{currentTask.brief.task}</p>
                <div style={{ fontSize: '0.78rem', color: 'var(--text)' }}>
                  Files to change: {currentTask.plan.target_files.map((path) => <code key={path} style={{ marginRight: '6px' }}>{path}</code>)}
                </div>

                <ol className="plan-steps-list">
                  {planSteps.map((step, idx) => (
                    <li key={idx}>
                      {isEditingPlan ? (
                        <input
                          type="text"
                          maxLength={400}
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

                {planEditsPending && <p className="field-help">Save and approve your edited steps before starting. The previously approved plan does not include these edits.</p>}
                {(currentTask.state === 'AWAITING_APPROVAL' || (currentTask.state === 'APPROVED' && planEditsPending)) && (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={loadingAction === 'approve-plan'}
                      onClick={() => void handleApprovePlan()}
                    >
                      {loadingAction === 'approve-plan' ? 'Saving…' : planOnlyTask ? 'Save reviewed plan' : 'Approve plan'}
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
                <h2>Test results ({taskExecutions.length})</h2>
              </div>

              <ExecutionResults records={taskExecutions} />
            </article>
          )}
        </div>

        {/* Right Column: Changes & Diff Viewer, Checkpoints, and Live Activity Log */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {!currentTask && (
            <TaskComposer
              projectName={activeProjectId ? draftProject?.name || 'Loading project…' : selectedSample.name}
              task={taskPrompt}
              workflow={workflow}
              instructions={instructions}
              savedInstructions={savedInstructions}
              files={Object.keys(sourceFiles)}
              editablePaths={selectedEditablePaths}
              creating={loadingAction === 'create-task'}
              blockedReason={draftBlockedReason || preferencesError}
              onTaskChange={setTaskPrompt}
              onWorkflowChange={setWorkflow}
              onInstructionsChange={setInstructions}
              onPathsChange={setSelectedEditablePaths}
              onSaveInstructions={handleSaveInstructions}
              onForgetInstructions={handleForgetInstructions}
              onCreate={() => void handleCreateTaskForSample()}
              agentSettings={(
                <AgentSettings
                  preferences={agentPreferences}
                  profiles={agentProfiles}
                  selectedProfileId={selectedProfileId}
                  defaultProfileId={defaultProfileId}
                  profileName={profileName}
                  modified={profileModified}
                  error={preferencesError}
                  onChange={setAgentPreferences}
                  onSelect={(id) => {
                    const profile = agentProfiles.find((item) => item.id === id)
                    if (profile) applyAgentProfile(profile)
                    else { setSelectedProfileId(''); setProfileName('') }
                  }}
                  onNameChange={setProfileName}
                  onSave={handleSaveProfile}
                  onDuplicate={() => profileAction(() => applyAgentProfile(duplicateAgentProfile(owner, selectedProfileId)))}
                  onDelete={() => profileAction(() => {
                    deleteAgentProfile(owner, selectedProfileId)
                    setSelectedProfileId('')
                    setProfileName('')
                    notify('info', 'Profile deleted. The current draft settings remain; existing tasks are unchanged.')
                  })}
                  onMakeDefault={() => profileAction(() => {
                    setDefaultAgentProfile(owner, selectedProfileId)
                    notify('success', 'This saved profile will be selected when you reopen the new-task workspace.')
                  })}
                  onClearDefault={() => profileAction(() => setDefaultAgentProfile(owner, null))}
                  onExport={handleExportProfile}
                  onImport={(file) => void handleImportProfile(file)}
                  extensions={<AgentExtensions api={api} owner={owner} preferences={agentPreferences} onChange={setAgentPreferences} context={externalContext} onContext={setExternalContext} />}
                />
              )}
            />
          )}
          {currentTask && <>
          {/* Changes & Unified Diff Viewer Card */}
          <article className="workspace-card">
            <div className="card-header-row">
              <h2>Code changes</h2>
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
                  <span>Author: {taskChanges.author || 'Not recorded'}</span>
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
                <h2>Download your work</h2>
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text)' }}>
                Download the patch, plan, recorded checks and usage together. Exports are scrubbed for known secret patterns; review them before sharing.
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
              <h2>Checkpoints ({taskCheckpoints.length})</h2>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text)' }}>
              Restore a saved task revision and pause there. This does not change your local repository or refund spent usage.
            </p>

            <div className="checkpoint-timeline">
              {taskCheckpoints.map((cp) => (
                <div key={cp.checkpoint_id} className="checkpoint-row">
                  <div>
                    <strong>Seq #{cp.sequence}</strong> · <span>{cp.stage}</span> ·{' '}
                    <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>{cp.state}</span>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text)', marginTop: '2px' }}>
                      ID: <code>{cp.checkpoint_id}</code> · {formatTimestamp(cp.created_at)}
                    </div>
                  </div>

                  {!planOnlyTask && currentTask?.state !== 'RUNNING' && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ minHeight: '32px', padding: '4px 10px', fontSize: '0.72rem' }}
                      disabled={loadingAction === `restore-${cp.checkpoint_id}`}
                      onClick={() => void handleRestoreCheckpoint(cp.checkpoint_id, taskCheckpoints.at(-1)?.checkpoint_id)}
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
              <h2>Activity ({filteredEvents.length})</h2>
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
                        Stage: {String(ev.stage || ev.payload.stage || 'Task')} {ev.payload && Object.keys(ev.payload).length > 0 ? `· ${JSON.stringify(ev.payload).slice(0, 60)}...` : ''}
                      </small>
                    </div>
                    <time>{formatTimestamp(ev.created_at)}</time>
                  </li>
                ))}
                {filteredEvents.length === 0 && (
                  <p style={{ color: 'var(--text)', fontSize: '0.82rem' }}>No events recorded for this task yet.</p>
                )}
              </ol>
            </div>
          </article>
          </>}
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
