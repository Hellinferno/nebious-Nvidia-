import type { CodingPlan } from './types'

export function sameReviewedPlan(reviewed: CodingPlan, current: CodingPlan | null): boolean {
  return current !== null
    && reviewed.schema_version === current.schema_version
    && reviewed.source_hash === current.source_hash
    && reviewed.brief_hash === current.brief_hash
    && reviewed.check_profile === current.check_profile
    && JSON.stringify(reviewed.steps) === JSON.stringify(current.steps)
    && JSON.stringify(reviewed.target_files) === JSON.stringify(current.target_files)
}
