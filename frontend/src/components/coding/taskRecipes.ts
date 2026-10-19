import type { CodingPreferences } from './types'

export const TASK_RECIPES: Array<{
  id: CodingPreferences['workflow']
  label: string
  description: string
}> = [
  { id: 'bugfix', label: 'Fix a bug', description: 'Focus on the cause and preserve working behavior.' },
  { id: 'feature', label: 'Add a feature', description: 'Build a small change that fits the existing code.' },
  { id: 'refactor', label: 'Refactor', description: 'Improve structure without changing behavior.' },
  { id: 'custom', label: 'Custom task', description: 'Describe your own goal and coding conventions.' },
]

export function recipeLabel(workflow?: CodingPreferences['workflow']) {
  return TASK_RECIPES.find((recipe) => recipe.id === workflow)?.label || 'Custom task'
}

export function instructionStorageKey(owner: string) {
  return `benchproof.coding-instructions:${owner}`
}

export function readSavedInstructions(owner: string): string | null {
  try {
    const stored = localStorage.getItem(instructionStorageKey(owner))
    return stored !== null && stored.length <= 2000 ? stored : null
  } catch {
    return null
  }
}
