import assert from 'node:assert/strict'
import test from 'node:test'
import {
  AGENT_INSTRUCTION_MODULES,
  DEFAULT_AGENT_PREFERENCES,
  DEFAULT_TASK_LIMITS,
  MAX_PROFILE_IMPORT_LENGTH,
  agentDefaultProfileStorageKey,
  agentProfileStorageKey,
  compileAgentPreferences,
  deleteAgentProfile,
  duplicateAgentProfile,
  exportAgentProfile,
  parseProfileImport,
  readAgentProfiles,
  readDefaultAgentProfile,
  saveAgentProfile,
  setDefaultAgentProfile,
  validateAgentPreferences,
  type AgentPreferences,
} from '../src/components/coding/agentProfiles.ts'

function preferences(overrides: Partial<AgentPreferences> = {}): AgentPreferences {
  return { ...DEFAULT_AGENT_PREFERENCES, limits: { ...DEFAULT_TASK_LIMITS }, instruction_modules: [], ...overrides }
}

function withStorage(run: (saved: Map<string, string>) => void) {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  const saved = new Map<string, string>()
  try {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => saved.get(key) ?? null,
        setItem: (key: string, value: string) => saved.set(key, value),
        removeItem: (key: string) => saved.delete(key),
      },
    })
    run(saved)
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous)
    else Reflect.deleteProperty(globalThis, 'localStorage')
  }
}

function importFile(overrides: Record<string, unknown> = {}) {
  return JSON.stringify({ schema_version: 'benchproof-agent-profile-v1', name: 'Careful fixes', preferences: preferences(), ...overrides })
}

test('profile library scopes saved profiles to the task owner without automatically applying them', () => {
  withStorage(() => {
    const profile = saveAgentProfile('owner-one', { name: 'Careful fixes', preferences: preferences({ workflow: 'bugfix' }) })
    assert.match(profile.id, /^profile-[0-9a-f-]{36}$/)
    assert.equal(readAgentProfiles('owner-one')[0]?.preferences.workflow, 'bugfix')
    assert.deepEqual(readAgentProfiles('owner-two'), [])
    assert.equal(DEFAULT_AGENT_PREFERENCES.workflow, 'custom')
    assert.notEqual(agentProfileStorageKey('owner-one'), agentProfileStorageKey('owner-two'))
  })
})

test('save preserves profile IDs while duplicate creates an independent ID and delete is owner-scoped', () => {
  withStorage(() => {
    const original = saveAgentProfile('owner-one', { name: 'Small changes', preferences: preferences() })
    const updated = saveAgentProfile('owner-one', { name: 'Updated', preferences: preferences({ mode: 'plan_only' }) }, original.id)
    assert.equal(updated.id, original.id)
    assert.equal(readAgentProfiles('owner-one').length, 1)
    const duplicate = duplicateAgentProfile('owner-one', original.id)
    assert.notEqual(duplicate.id, original.id)
    assert.equal(duplicate.name, 'Updated copy')
    assert.deepEqual(duplicate.preferences, updated.preferences)
    deleteAgentProfile('owner-two', original.id)
    assert.equal(readAgentProfiles('owner-one').length, 2)
    deleteAgentProfile('owner-one', original.id)
    assert.deepEqual(readAgentProfiles('owner-one').map((profile) => profile.id), [duplicate.id])
    assert.throws(() => duplicateAgentProfile('owner-one', original.id), /no longer exists/)
    assert.throws(() => saveAgentProfile('owner-one', { name: 'Gone', preferences: preferences() }, original.id), /no longer exists/)
  })
})

test('saved preferences and returned profiles do not share mutable instruction-module or limit objects', () => {
  withStorage(() => {
    const original = preferences({ instruction_modules: ['compatibility'] })
    const profile = saveAgentProfile('owner-one', { name: 'Immutable', preferences: original })
    original.instruction_modules.push('typing')
    original.limits.model_calls = 1
    profile.preferences.instruction_modules.push('stdlib')
    profile.preferences.limits.executions = 1
    assert.deepEqual(readAgentProfiles('owner-one')[0]?.preferences.instruction_modules, ['compatibility'])
    assert.equal(readAgentProfiles('owner-one')[0]?.preferences.limits.model_calls, 4)
    assert.equal(readAgentProfiles('owner-one')[0]?.preferences.limits.executions, 4)
  })
})

test('library enforces ten-profile cap but allows updating an existing profile at the cap', () => {
  withStorage(() => {
    for (let index = 0; index < 10; index += 1) saveAgentProfile('owner-one', { name: `Profile ${index}`, preferences: preferences() })
    const first = readAgentProfiles('owner-one')[0]!
    assert.throws(() => saveAgentProfile('owner-one', { name: 'Eleventh', preferences: preferences() }), /up to 10/)
    assert.throws(() => duplicateAgentProfile('owner-one', first.id), /up to 10/)
    saveAgentProfile('owner-one', { name: 'Updated at cap', preferences: preferences() }, first.id)
    assert.equal(readAgentProfiles('owner-one').length, 10)
  })
})

test('only explicitly selected saved profiles become defaults and defaults are owner-scoped', () => {
  withStorage(() => {
    const profile = saveAgentProfile('owner-one', { name: 'My default', preferences: preferences({ mode: 'plan_only' }) })
    assert.equal(readDefaultAgentProfile('owner-one'), null)
    assert.throws(() => setDefaultAgentProfile('owner-two', profile.id), /existing saved profile/)
    setDefaultAgentProfile('owner-one', profile.id)
    assert.deepEqual(readDefaultAgentProfile('owner-one'), profile)
    assert.equal(readDefaultAgentProfile('owner-two'), null)
    saveAgentProfile('owner-one', { name: 'Updated default', preferences: preferences() }, profile.id)
    assert.equal(readDefaultAgentProfile('owner-one')?.name, 'Updated default')
    setDefaultAgentProfile('owner-one', null)
    assert.equal(readDefaultAgentProfile('owner-one'), null)
  })
})

test('deleting the selected default clears its key and invalid default records are ignored', () => {
  withStorage((saved) => {
    const profile = saveAgentProfile('owner-one', { name: 'Default', preferences: preferences() })
    setDefaultAgentProfile('owner-one', profile.id)
    deleteAgentProfile('owner-one', profile.id)
    assert.equal(readDefaultAgentProfile('owner-one'), null)
    assert.equal(saved.has(agentDefaultProfileStorageKey('owner-one')), false)
    for (const invalid of ['not a profile', profile.id, JSON.stringify({ profile_id: profile.id })]) {
      saved.set(agentDefaultProfileStorageKey('owner-one'), invalid)
      assert.equal(readDefaultAgentProfile('owner-one'), null)
    }
  })
})

test('portable JSON round-trip includes only version, name and customization configuration', () => {
  withStorage(() => {
    const original = saveAgentProfile('owner-one', {
      name: 'Planning',
      preferences: preferences({ mode: 'plan_only', instruction_modules: ['compatibility', 'concise_changes'], instructions: 'Explain tradeoffs.' }),
    })
    const exported = exportAgentProfile(original)
    const envelope = JSON.parse(exported)
    assert.deepEqual(Object.keys(envelope).sort(), ['name', 'preferences', 'schema_version'])
    assert.equal(exported.includes(original.id), false)
    assert.equal(exported.includes('owner-one'), false)
    assert.deepEqual(parseProfileImport(exported), { name: original.name, preferences: original.preferences })
    const imported = saveAgentProfile('owner-two', parseProfileImport(exported))
    assert.notEqual(imported.id, original.id)
  })
})

test('imports reject malformed JSON, unsupported versions and executable, source or credential configuration', () => {
  assert.throws(() => parseProfileImport('not json'), /valid JSON/)
  assert.throws(() => parseProfileImport('[]'), /must be an object/)
  assert.throws(() => parseProfileImport(importFile({ schema_version: 'future' })), /Unsupported profile version/)
  assert.throws(() => parseProfileImport(' '.repeat(MAX_PROFILE_IMPORT_LENGTH + 1)), /too large/)
  for (const key of ['command', 'tools', 'endpoint', 'api_key', 'source', 'files', 'task', '__proto__']) {
    assert.throws(() => parseProfileImport(importFile({ [key]: key === 'endpoint' ? 'https://invalid.example' : 'not allowed' })), /unsupported fields/)
  }
  for (const key of ['command', 'tools', 'api_key', 'model_id', 'system_prompt', 'task', 'files']) {
    assert.throws(() => parseProfileImport(importFile({ preferences: { ...preferences(), [key]: 'not allowed' } })), /unsupported fields/)
  }
})

test('imports enforce nonempty bounded names and bounded plain-text instructions', () => {
  for (const name of ['', ' '.repeat(3), 'a'.repeat(61), null, 7]) {
    assert.throws(() => parseProfileImport(importFile({ name })), /1–60/)
  }
  assert.equal(parseProfileImport(importFile({ name: '  A valid name  ' })).name, 'A valid name')
  assert.equal(parseProfileImport(importFile({ name: 'a'.repeat(60) })).name.length, 60)
  assert.throws(() => parseProfileImport(importFile({ preferences: preferences({ instructions: 'a'.repeat(2001) }) })), /2,000/)
  assert.equal(parseProfileImport(importFile({ preferences: preferences({ instructions: 'a'.repeat(2000) }) })).preferences.instructions.length, 2000)
})

test('only supported workflows, modes and unique trusted instruction modules are accepted', () => {
  assert.deepEqual(AGENT_INSTRUCTION_MODULES.map((module) => module.id), ['compatibility', 'stdlib', 'typing', 'error_handling', 'concise_changes'])
  assert.ok(AGENT_INSTRUCTION_MODULES.every((module) => module.label && module.description && module.instructions))
  for (const value of [
    { workflow: 'autonomous' },
    { mode: 'unrestricted' },
    { instruction_modules: ['external_tool'] },
    { instruction_modules: ['compatibility', 'compatibility'] },
    { instruction_modules: { compatibility: true } },
    { instruction_modules: [null] },
    { instructions: 42 },
  ]) {
    assert.throws(() => validateAgentPreferences({ ...preferences(), ...value }))
  }
})

test('profile budgets accept only integer lower limits inside the server hard bounds', () => {
  const minimum = { model_calls: 1, patch_attempts: 1, executions: 1, active_seconds: 30 }
  assert.deepEqual(validateAgentPreferences(preferences({ limits: minimum })).limits, minimum)
  for (const [key, invalidValues] of Object.entries({ model_calls: [0, 5, 1.5], patch_attempts: [0, 3], executions: [0, 5], active_seconds: [29, 301, Infinity, NaN] })) {
    for (const invalid of invalidValues) {
      assert.throws(() => validateAgentPreferences(preferences({ limits: { ...DEFAULT_TASK_LIMITS, [key]: invalid } })), /Profiles can only lower/)
    }
  }
  assert.throws(() => validateAgentPreferences({ ...preferences(), limits: { ...DEFAULT_TASK_LIMITS, wall_seconds: 60 } }), /unsupported fields/)
  assert.throws(() => validateAgentPreferences({ ...preferences(), limits: { model_calls: 1 } }), /missing/)
})

test('compiler uses only trusted module rules, omits default backend fields and does not export module IDs', () => {
  assert.deepEqual(compileAgentPreferences(preferences()), { workflow: 'custom', instructions: '' })
  const compiled = compileAgentPreferences(preferences({
    workflow: 'refactor', mode: 'plan_only', instructions: 'Keep the API stable.',
    instruction_modules: ['concise_changes', 'compatibility'],
    limits: { ...DEFAULT_TASK_LIMITS, model_calls: 1 },
  }))
  assert.equal(compiled.mode, 'plan_only')
  assert.equal(compiled.limits?.model_calls, 1)
  assert.equal(compiled.workflow, 'refactor')
  assert.equal(Object.hasOwn(compiled, 'instruction_modules'), false)
  assert.equal(compiled.instructions, ['Keep the API stable.', AGENT_INSTRUCTION_MODULES[0]!.instructions, AGENT_INSTRUCTION_MODULES[4]!.instructions].join('\n\n'))
})

test('compiler rejects combined instruction overflow rather than silently dropping guidance', () => {
  const tooLong = preferences({ instructions: 'a'.repeat(1999), instruction_modules: ['compatibility'] })
  assert.throws(() => compileAgentPreferences(tooLong), /together exceed/)
  assert.throws(() => parseProfileImport(importFile({ preferences: tooLong })), /together exceed/)
  withStorage(() => assert.throws(() => saveAgentProfile('owner-one', { name: 'Overflow', preferences: tooLong }), /together exceed/))
})

test('unavailable, malformed and unsupported storage reads safely without overwriting existing data', () => {
  withStorage((saved) => {
    for (const contents of ['invalid json', '{}', JSON.stringify({ schema_version: 'future', profiles: [] })]) {
      saved.set(agentProfileStorageKey('owner-one'), contents)
      assert.deepEqual(readAgentProfiles('owner-one'), [])
      assert.throws(() => saveAgentProfile('owner-one', { name: 'New', preferences: preferences() }), /were not changed/)
      assert.equal(saved.get(agentProfileStorageKey('owner-one')), contents)
    }
  })
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  try {
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, get() { throw new Error('Unavailable') } })
    assert.deepEqual(readAgentProfiles('owner-one'), [])
    assert.throws(() => saveAgentProfile('owner-one', { name: 'New', preferences: preferences() }), /unavailable/)
    assert.throws(() => deleteAgentProfile('owner-one', 'missing'), /Could not delete/)
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous)
    else Reflect.deleteProperty(globalThis, 'localStorage')
  }
})

test('storage write errors are visible rather than falsely reporting a saved profile', () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  try {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: { getItem: () => null, setItem: () => { throw new Error('Quota exceeded') } },
    })
    assert.throws(() => saveAgentProfile('owner-one', { name: 'Unsaved', preferences: preferences() }), /Could not save/)
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous)
    else Reflect.deleteProperty(globalThis, 'localStorage')
  }
})
