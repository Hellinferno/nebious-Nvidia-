import { validateSkill } from './agentSkills.ts'
import type { AgentSkill } from './agentSkills.ts'

export type AgentWorkflow = 'custom' | 'bugfix' | 'feature' | 'refactor'
export type AgentMode = 'implement' | 'plan_only'
export type AgentInstructionModuleId = 'compatibility' | 'stdlib' | 'typing' | 'error_handling' | 'concise_changes'

export type TaskLimits = {
  model_calls: number
  patch_attempts: number
  executions: number
  active_seconds: number
}

export type AgentPreferences = {
  workflow: AgentWorkflow
  instructions: string
  mode: AgentMode
  limits: TaskLimits
  instruction_modules: AgentInstructionModuleId[]
  harness?: 'bounded-v1' | 'single-pass-v1'
  skills?: AgentSkill[]
}

export type AgentProfileConfiguration = {
  name: string
  preferences: AgentPreferences
}

export type AgentProfile = AgentProfileConfiguration & { id: string }

export type CompiledAgentPreferences = {
  workflow: AgentWorkflow
  instructions: string
  mode?: 'plan_only'
  limits?: TaskLimits
  harness?: 'single-pass-v1'
  skills?: AgentSkill[]
}

export const MAX_AGENT_PROFILES = 10
export const MAX_PROFILE_IMPORT_LENGTH = 16_384
export const DEFAULT_TASK_LIMITS: TaskLimits = {
  model_calls: 4,
  patch_attempts: 2,
  executions: 4,
  active_seconds: 300,
}

export const AGENT_INSTRUCTION_MODULES: ReadonlyArray<{
  id: AgentInstructionModuleId
  label: string
  description: string
  instructions: string
}> = [
  {
    id: 'compatibility',
    label: 'Preserve compatibility',
    description: 'Keep public interfaces and existing behavior stable.',
    instructions: 'Preserve public interfaces and existing behavior unless the task explicitly requires a change. Follow the repository conventions.',
  },
  {
    id: 'stdlib',
    label: 'Prefer the standard library',
    description: 'Avoid adding dependencies for a small change.',
    instructions: 'Prefer the standard library and existing dependencies. Do not add a dependency unless the task explicitly requires it.',
  },
  {
    id: 'typing',
    label: 'Match typing conventions',
    description: 'Keep type information consistent with nearby code.',
    instructions: 'Use clear types consistent with the repository. Preserve useful type information and avoid weakening existing type checks.',
  },
  {
    id: 'error_handling',
    label: 'Handle errors clearly',
    description: 'Make failure cases explicit without hiding failures.',
    instructions: 'Handle expected failure cases explicitly. Preserve useful error information and do not silently suppress failures.',
  },
  {
    id: 'concise_changes',
    label: 'Keep changes focused',
    description: 'Avoid unrelated cleanup and broad rewrites.',
    instructions: 'Make the smallest clear change that solves the task. Avoid unrelated formatting, renaming, cleanup, or architectural rewrites.',
  },
]

export const DEFAULT_AGENT_PREFERENCES: AgentPreferences = {
  workflow: 'custom',
  instructions: '',
  mode: 'implement',
  limits: { ...DEFAULT_TASK_LIMITS },
  instruction_modules: [],
}

const PROFILE_SCHEMA = 'benchproof-agent-profile-v1'
const STORAGE_SCHEMA = 'benchproof-agent-profiles-v1'
const PROFILE_ID = /^profile-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const LIMIT_BOUNDS: Record<keyof TaskLimits, readonly [number, number]> = {
  model_calls: [1, 4],
  patch_attempts: [1, 2],
  executions: [1, 4],
  active_seconds: [30, 300],
}

function record(value: unknown, label: string, keys: string[], optional: string[] = []): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be an object.`)
  }
  const prototype = Object.getPrototypeOf(value)
  if (prototype !== Object.prototype && prototype !== null) {
    throw new Error(`${label} must be a plain configuration object.`)
  }
  const result = value as Record<string, unknown>
  if (Object.keys(result).some((key) => !keys.includes(key) && !optional.includes(key)) || keys.some((key) => !Object.hasOwn(result, key))) {
    throw new Error(`${label} contains missing or unsupported fields.`)
  }
  return result
}

function profileName(value: unknown): string {
  if (typeof value !== 'string' || !value.trim() || value.length > 60) {
    throw new Error('Profile name must contain 1–60 characters.')
  }
  return value.trim()
}

export function validateAgentPreferences(value: unknown): AgentPreferences {
  const preferences = record(value, 'Agent preferences', ['workflow', 'instructions', 'mode', 'limits', 'instruction_modules'], ['harness', 'skills'])
  if (!['custom', 'bugfix', 'feature', 'refactor'].includes(preferences.workflow as string)) {
    throw new Error('Choose a supported workflow.')
  }
  if (typeof preferences.instructions !== 'string' || preferences.instructions.length > 2000) {
    throw new Error('Custom instructions must contain at most 2,000 characters.')
  }
  if (preferences.mode !== 'implement' && preferences.mode !== 'plan_only') {
    throw new Error('Choose implement or plan-only mode.')
  }
  const rawLimits = record(preferences.limits, 'Task limits', Object.keys(LIMIT_BOUNDS))
  const limits = {} as TaskLimits
  for (const key of Object.keys(LIMIT_BOUNDS) as Array<keyof TaskLimits>) {
    const limit = rawLimits[key]
    const [minimum, maximum] = LIMIT_BOUNDS[key]
    if (typeof limit !== 'number' || !Number.isInteger(limit) || limit < minimum || limit > maximum) {
      throw new Error(`${key} must be a whole number from ${minimum} to ${maximum}. Profiles can only lower task limits.`)
    }
    limits[key] = limit
  }
  const modules = preferences.instruction_modules
  if (!Array.isArray(modules) || modules.length > AGENT_INSTRUCTION_MODULES.length || new Set(modules).size !== modules.length) {
    throw new Error('Instruction modules must be a unique list from the trusted catalog.')
  }
  if (modules.some((moduleId) => typeof moduleId !== 'string' || !AGENT_INSTRUCTION_MODULES.some((module) => module.id === moduleId))) {
    throw new Error('Unknown instruction module. Only built-in prompt guidance is supported.')
  }
  if (preferences.harness !== undefined && !['bounded-v1', 'single-pass-v1'].includes(preferences.harness as string)) throw new Error('Choose a reviewed built-in harness.')
  let skills: AgentSkill[] = []
  if (preferences.skills !== undefined) {
    if (!Array.isArray(preferences.skills) || preferences.skills.length > 3) throw new Error('Select at most three instruction-only skills.')
    skills = preferences.skills.map(validateSkill)
    if (new Set(skills.map((skill) => skill.name)).size !== skills.length) throw new Error('Selected skill names must be unique.')
  }
  return {
    workflow: preferences.workflow as AgentWorkflow,
    instructions: preferences.instructions,
    mode: preferences.mode,
    limits,
    instruction_modules: [...modules] as AgentInstructionModuleId[],
    ...(preferences.harness === 'single-pass-v1' ? { harness: 'single-pass-v1' as const } : {}),
    ...(skills.length ? { skills } : {}),
  }
}

export function compileAgentPreferences(value: unknown): CompiledAgentPreferences {
  const preferences = validateAgentPreferences(value)
  const selected = new Set(preferences.instruction_modules)
  const instructions = [
    preferences.instructions,
    ...AGENT_INSTRUCTION_MODULES.filter((module) => selected.has(module.id)).map((module) => module.instructions),
  ].filter(Boolean).join('\n\n')
  if (instructions.length > 2000) {
    throw new Error('Custom instructions and selected modules together exceed 2,000 characters. Shorten the instructions or deselect a module.')
  }
  const result: CompiledAgentPreferences = { workflow: preferences.workflow, instructions }
  if (preferences.harness === 'single-pass-v1') result.harness = 'single-pass-v1'
  if (preferences.skills?.length) result.skills = preferences.skills
  if (preferences.mode === 'plan_only') result.mode = 'plan_only'
  if ((Object.keys(DEFAULT_TASK_LIMITS) as Array<keyof TaskLimits>).some((key) => preferences.limits[key] !== DEFAULT_TASK_LIMITS[key])) {
    result.limits = { ...preferences.limits }
  }
  return result
}

function validateConfiguration(value: unknown): AgentProfileConfiguration {
  const configuration = record(value, 'Profile', ['name', 'preferences'])
  const preferences = validateAgentPreferences(configuration.preferences)
  compileAgentPreferences(preferences)
  return { name: profileName(configuration.name), preferences }
}

export function validateAgentProfile(value: unknown): AgentProfile {
  const profile = record(value, 'Saved profile', ['id', 'name', 'preferences'])
  if (typeof profile.id !== 'string' || !PROFILE_ID.test(profile.id)) {
    throw new Error('Saved profile ID is invalid.')
  }
  return { id: profile.id, ...validateConfiguration({ name: profile.name, preferences: profile.preferences }) }
}

export function parseProfileImport(contents: string): AgentProfileConfiguration {
  if (typeof contents !== 'string' || contents.length > MAX_PROFILE_IMPORT_LENGTH) {
    throw new Error('Profile JSON is too large. The maximum is 16 KiB of text.')
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(contents)
  } catch {
    throw new Error('Profile file must contain valid JSON.')
  }
  const envelope = record(parsed, 'Imported profile', ['schema_version', 'name', 'preferences'])
  if (![PROFILE_SCHEMA, 'benchproof-agent-profile-v2'].includes(envelope.schema_version as string)) {
    throw new Error('Unsupported profile version. Import a benchproof-agent-profile-v1 file.')
  }
  return validateConfiguration({ name: envelope.name, preferences: envelope.preferences })
}

export function exportAgentProfile(value: AgentProfile): string {
  const profile = validateAgentProfile(value)
  const version = profile.preferences.skills?.length || profile.preferences.harness ? 'benchproof-agent-profile-v2' : PROFILE_SCHEMA
  return JSON.stringify({ schema_version: version, name: profile.name, preferences: profile.preferences }, null, 2)
}

export function agentProfileStorageKey(owner: string): string {
  if (typeof owner !== 'string' || !owner || owner.length > 256) {
    throw new Error('A valid task owner is required for profile storage.')
  }
  return `benchproof.agent-profiles.v1:${encodeURIComponent(owner)}`
}

export function agentDefaultProfileStorageKey(owner: string): string {
  return `${agentProfileStorageKey(owner)}:default`
}

function storedProfiles(owner: string): AgentProfile[] {
  const contents = globalThis.localStorage.getItem(agentProfileStorageKey(owner))
  if (contents === null) return []
  if (contents.length > MAX_PROFILE_IMPORT_LENGTH * MAX_AGENT_PROFILES) throw new Error('Saved profile library is too large.')
  const envelope = record(JSON.parse(contents), 'Saved profile library', ['schema_version', 'profiles'])
  if (envelope.schema_version !== STORAGE_SCHEMA || !Array.isArray(envelope.profiles) || envelope.profiles.length > MAX_AGENT_PROFILES) {
    throw new Error('Saved profile library is invalid or uses an unsupported version.')
  }
  const profiles = envelope.profiles.map(validateAgentProfile)
  if (new Set(profiles.map((profile) => profile.id)).size !== profiles.length) {
    throw new Error('Saved profile library contains duplicate IDs.')
  }
  return profiles
}

export function readAgentProfiles(owner: string): AgentProfile[] {
  try {
    return storedProfiles(owner)
  } catch {
    return []
  }
}

export function readDefaultAgentProfile(owner: string): AgentProfile | null {
  try {
    const profileId = globalThis.localStorage.getItem(agentDefaultProfileStorageKey(owner))
    if (profileId === null || !PROFILE_ID.test(profileId)) return null
    return storedProfiles(owner).find((profile) => profile.id === profileId) ?? null
  } catch {
    return null
  }
}

export function setDefaultAgentProfile(owner: string, profileId: string | null): void {
  try {
    if (profileId === null) {
      globalThis.localStorage.removeItem(agentDefaultProfileStorageKey(owner))
      return
    }
    if (!storedProfiles(owner).some((profile) => profile.id === profileId)) {
      throw new Error('Profile does not exist.')
    }
    globalThis.localStorage.setItem(agentDefaultProfileStorageKey(owner), profileId)
  } catch {
    throw new Error('Could not set the default profile. Select an existing saved profile and ensure browser storage is available.')
  }
}

function writeProfiles(owner: string, profiles: AgentProfile[]): void {
  globalThis.localStorage.setItem(agentProfileStorageKey(owner), JSON.stringify({ schema_version: STORAGE_SCHEMA, profiles }))
}

export function saveAgentProfile(owner: string, value: AgentProfileConfiguration, existingId?: string): AgentProfile {
  const configuration = validateConfiguration(value)
  let profiles: AgentProfile[]
  try {
    profiles = storedProfiles(owner)
  } catch {
    throw new Error('Profile storage is unavailable or invalid. Existing saved profiles were not changed.')
  }
  const existingIndex = existingId === undefined ? -1 : profiles.findIndex((profile) => profile.id === existingId)
  if (existingId !== undefined && existingIndex < 0) throw new Error('The selected profile no longer exists. Save it as a new profile.')
  if (existingIndex < 0 && profiles.length >= MAX_AGENT_PROFILES) throw new Error('You can save up to 10 profiles. Delete a profile before adding another.')
  const profile = { id: existingId ?? `profile-${globalThis.crypto.randomUUID()}`, ...configuration }
  if (existingIndex < 0) profiles.push(profile)
  else profiles[existingIndex] = profile
  try {
    writeProfiles(owner, profiles)
  } catch {
    throw new Error('Could not save the profile. Browser storage may be blocked or full.')
  }
  return validateAgentProfile(profile)
}

export function deleteAgentProfile(owner: string, profileId: string): void {
  try {
    const profiles = storedProfiles(owner)
    if (globalThis.localStorage.getItem(agentDefaultProfileStorageKey(owner)) === profileId) {
      globalThis.localStorage.removeItem(agentDefaultProfileStorageKey(owner))
    }
    writeProfiles(owner, profiles.filter((profile) => profile.id !== profileId))
  } catch {
    throw new Error('Could not delete the profile. Browser storage may be blocked or full.')
  }
}

export function duplicateAgentProfile(owner: string, profileId: string, name?: string): AgentProfile {
  let original: AgentProfile | undefined
  try {
    original = storedProfiles(owner).find((profile) => profile.id === profileId)
  } catch {
    throw new Error('Profile storage is unavailable or invalid.')
  }
  if (!original) throw new Error('The selected profile no longer exists.')
  return saveAgentProfile(owner, {
    name: name ?? `${original.name.slice(0, 55)} copy`,
    preferences: original.preferences,
  })
}
