export type AgentSkill = { name: string; description: string; instructions: string }

export function validateSkill(value: unknown): AgentSkill {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Skill must be an object.')
  const skill = value as Record<string, unknown>
  if (Object.keys(skill).sort().join(',') !== 'description,instructions,name') throw new Error('Only instruction-only skill fields are accepted.')
  if (typeof skill.name !== 'string' || skill.name.length > 64 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(skill.name)) throw new Error('Skill name must be a lowercase hyphenated name, at most 64 characters.')
  if (typeof skill.description !== 'string' || !skill.description.trim() || skill.description.length > 512) throw new Error('Skill description must contain 1–512 characters.')
  if (typeof skill.instructions !== 'string' || !skill.instructions.trim() || skill.instructions.length > 2000) throw new Error('Skill instructions must contain 1–2,000 characters.')
  return { name: skill.name, description: skill.description, instructions: skill.instructions }
}

export function parseSkillMarkdown(text: string): AgentSkill {
  if (text.length > 8192) throw new Error('SKILL.md exceeds 8 KiB of text.')
  const normalized = text.replace(/\r\n/g, '\n').replace(/^\uFEFF/, '')
  const match = normalized.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
  if (!match) throw new Error('SKILL.md needs YAML frontmatter with name and description, then Markdown instructions.')
  const metadata: Record<string, string> = {}
  for (const line of match[1].split('\n')) {
    if (!line.trim() || line.trim().startsWith('#')) continue
    const entry = line.match(/^([a-z-]+):\s*(.+)$/)
    if (!entry || !['name', 'description', 'license', 'compatibility'].includes(entry[1]) || entry[1] in metadata) throw new Error('Use unique plain or quoted scalar metadata. Script permissions, YAML tags, nested and multiline metadata are unsupported.')
    let value = entry[2].trim()
    if (value.startsWith('"')) {
      try { value = JSON.parse(value) } catch { throw new Error('Invalid quoted skill metadata.') }
    } else if (value.startsWith("'")) {
      if (!value.endsWith("'")) throw new Error('Invalid quoted skill metadata.')
      value = value.slice(1, -1).replace(/''/g, "'")
    } else if (['!', '&', '*', '[', ']', '{', '|', '>'].includes(value[0])) throw new Error('Only plain scalar skill metadata is supported.')
    if (typeof value !== 'string') throw new Error('Skill metadata must be text.')
    metadata[entry[1]] = value
  }
  return validateSkill({ name: metadata.name, description: metadata.description, instructions: match[2].trim() })
}

export function exportSkillMarkdown(skill: AgentSkill): string {
  const checked = validateSkill(skill)
  return `---\nname: ${checked.name}\ndescription: ${JSON.stringify(checked.description)}\n---\n\n${checked.instructions}\n`
}

export function readSkills(owner: string): AgentSkill[] {
  try {
    const raw = localStorage.getItem(`benchproof.skills.v1:${owner}`)
    if (!raw) return []
    if (raw.length > 40_000) return []
    const values: unknown = JSON.parse(raw)
    if (!Array.isArray(values) || values.length > 10) return []
    const skills = values.map(validateSkill)
    return new Set(skills.map((skill) => skill.name)).size === skills.length ? skills : []
  } catch { return [] }
}

export function writeSkills(owner: string, skills: AgentSkill[]) {
  if (skills.length > 10 || new Set(skills.map((skill) => skill.name)).size !== skills.length) throw new Error('Save at most ten uniquely named skills.')
  localStorage.setItem(`benchproof.skills.v1:${owner}`, JSON.stringify(skills.map(validateSkill)))
}
