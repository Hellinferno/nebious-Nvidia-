import assert from 'node:assert/strict'
import test from 'node:test'
import { exportSkillMarkdown, parseSkillMarkdown, validateSkill } from '../src/components/coding/agentSkills.ts'
import { compileAgentPreferences, DEFAULT_AGENT_PREFERENCES, exportAgentProfile, parseProfileImport } from '../src/components/coding/agentProfiles.ts'

const skill = { name: 'api-conventions', description: 'When editing public Python functions', instructions: 'Preserve interfaces and describe unsupported cases.' }

test('instruction-only SKILL.md round-trips with CRLF and Unicode', () => {
  const markdown = exportSkillMarkdown({ ...skill, instructions: 'Keep café values intact.\nPreserve names.' })
  assert.deepEqual(parseSkillMarkdown(markdown.replaceAll('\n', '\r\n')), { ...skill, instructions: 'Keep café values intact.\nPreserve names.' })
  assert.equal(parseSkillMarkdown('---\nname: api-rules\ndescription: Public API changes\n---\nKeep stable names.').name, 'api-rules')
})

test('skill imports reject malformed metadata and executable configuration', () => {
  for (const markdown of [
    'No frontmatter',
    '---\nname: invalid name\ndescription: x\n---\nx',
    '---\nname: rules\ndescription: x\ncommand: execute\n---\nx',
    '---\nname: rules\nname: other\ndescription: x\n---\nx',
    '---\nname: rules\ndescription: !!js/function evil\n---\nx',
    '---\nname: rules\ndescription: |\n  long description\n---\nx',
  ]) assert.throws(() => parseSkillMarkdown(markdown))
  assert.throws(() => validateSkill({ ...skill, scripts: ['run.py'] }))
  assert.throws(() => validateSkill({ ...skill, instructions: 'x'.repeat(2001) }))
})

test('selected skills and versioned harness are preserved without turning them into permissions', () => {
  const preferences = { ...DEFAULT_AGENT_PREFERENCES, harness: 'single-pass-v1' as const, skills: [skill] }
  const compiled = compileAgentPreferences(preferences)
  assert.equal(compiled.harness, 'single-pass-v1')
  assert.deepEqual(compiled.skills, [skill])
  assert.equal(compiled.instructions, '')
  const portable = exportAgentProfile({ id: 'profile-12345678-1234-1234-1234-123456789012', name: 'My review', preferences })
  assert.equal(JSON.parse(portable).schema_version, 'benchproof-agent-profile-v2')
  assert.deepEqual(parseProfileImport(portable).preferences, preferences)
  assert.throws(() => compileAgentPreferences({ ...preferences, harness: 'load-arbitrary-package' }))
  assert.throws(() => compileAgentPreferences({ ...preferences, context: [{ content: 'private lookup' }] }))
})

test('legacy profiles and default harness retain their original wire identity', () => {
  assert.deepEqual(compileAgentPreferences({ ...DEFAULT_AGENT_PREFERENCES, harness: 'bounded-v1', skills: [] }), compileAgentPreferences(DEFAULT_AGENT_PREFERENCES))
  const exported = exportAgentProfile({ id: 'profile-12345678-1234-1234-1234-123456789012', name: 'Legacy', preferences: DEFAULT_AGENT_PREFERENCES })
  assert.equal(JSON.parse(exported).schema_version, 'benchproof-agent-profile-v1')
  assert.deepEqual(parseProfileImport(exported).preferences, DEFAULT_AGENT_PREFERENCES)
})

test('skills are unique and limited to three immutable snapshots', () => {
  assert.throws(() => compileAgentPreferences({ ...DEFAULT_AGENT_PREFERENCES, skills: [skill, skill] }))
  assert.throws(() => compileAgentPreferences({ ...DEFAULT_AGENT_PREFERENCES, skills: [1, 2, 3, 4].map((number) => ({ ...skill, name: `rules-${number}` })) }))
  const preferences = { ...DEFAULT_AGENT_PREFERENCES, skills: [skill] }
  const compiled = compileAgentPreferences(preferences)
  compiled.skills![0].instructions = 'Changed copy'
  assert.equal(preferences.skills[0].instructions, skill.instructions)
})
