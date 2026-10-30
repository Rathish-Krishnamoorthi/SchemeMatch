export type EligibilityStatus = 'LIKELY_ELIGIBLE' | 'NEEDS_VERIFICATION' | 'NOT_ELIGIBLE'

export type AuthUser = {
  id: string
  name: string
  email: string
  has_profile?: boolean
}

export type AuthResponse = {
  token: string
  user: AuthUser
}

export type UserProfileSettings = {
  name: string
  animal: string
  image: string
}

/** Full demographic profile — mirrors backend UserProfile */
export type UserDemographicProfile = {
  age: string
  state: string
  district: string
  annual_income: string
  occupation: string
  profession: string          // sub-type: role/sector when employed or self-employed
  education_level: string
  employment_status: string
  farmer_status: string       // '' | 'yes' | 'no' — auto-derived from occupation
  land_holding_acres: string  // only when farmer
  student_status: string      // '' | 'yes' | 'no' — auto-derived from occupation
  institution_type: string    // only when student
  category: string
  disability_status: string   // '' | 'yes' | 'no'
  disability_type: string     // only when disability = yes
  gender: string
  marital_status: string
  dependants: string          // number of dependants (used in income-based schemes)
  need: string
}

export type ProfileFormValues = UserDemographicProfile

export type ProfileRequest = Omit<
  ProfileFormValues,
  'age' | 'annual_income' | 'student_status' | 'farmer_status' | 'disability_status' | 'land_holding_acres' | 'dependants'
> & {
  age: number | null
  annual_income: number | null
  student_status: boolean | null
  farmer_status: boolean | null
  disability_status: boolean | null
  land_holding_acres: number | null
  dependants: number | null
}

export type Scheme = {
  scheme_id: string
  name: string
  category: string
  description: string
  benefits: string
  documents: string[]
  application_process: string[]
  official_url: string
  source: string
  last_verified: string | null
  verification_note: string | null
}

export type TrustScore = {
  score: number
  level: 'low' | 'moderate' | 'high'
  evidence: Array<{ factor: string; points: number; detail: string }>
  disclaimer: string
}

export type Recommendation = {
  scheme: Scheme
  eligibility: {
    status: EligibilityStatus
    reasons: string[]
  }
  match_score: number
  explanation: string
}

export type RecommendationResponse = {
  recommendations: Recommendation[]
  excluded_count: number
  disclaimer: string
}

// ── Module 1: Eligibility Scanner ────────────────────────────────────────────

export type ScanSchemeResult = {
  scheme: Scheme
  eligibility: { status: EligibilityStatus; reasons: string[] }
  group: 'eligible' | 'unknown' | 'unverified' | 'ineligible'
  trust?: TrustScore
}

export type EligibleSchemesResponse = {
  schemes: Array<{
    scheme: Scheme
    eligibility: { status: EligibilityStatus; reasons: string[] }
    trust: TrustScore
  }>
  eligible_count: number
  total_schemes: number
  profile_summary: EligibilityScanResponse['profile_summary']
  disclaimer: string
}

export type EligibilityScanResponse = {
  eligible: ScanSchemeResult[]
  unknown: ScanSchemeResult[]
  unverified: ScanSchemeResult[]
  ineligible: ScanSchemeResult[]
  totals: {
    eligible: number
    unknown: number
    unverified: number
    ineligible: number
    total: number
  }
  profile_summary: {
    age: number | null
    state: string | null
    occupation: string | null
    category: string | null
    gender: string | null
    education_level: string | null
    annual_income: number | null
  }
}

// ── Module 2: Semantic Scheme Finder ─────────────────────────────────────────

export type FinderResult = {
  scheme: Scheme
  eligibility: { status: EligibilityStatus; reasons: string[] }
  semantic_score: number
  category_score: number
  benefit_score: number
  weighted_score: number
  explanation: string
  evidence: Array<{ field: string; quote: string }>
  trust: TrustScore
}

export type FinderResponse = {
  results: FinderResult[]
  unknown: ScanSchemeResult[]
  excluded_count: number
  total_candidates: number
  query_text: string
  weights: { semantic: number; category: number; benefit: number }
  disclaimer: string
}

export type TrustScoresResponse = {
  schemes: Array<{ scheme: Scheme; trust: TrustScore }>
  total: number
  disclaimer: string
}

export type QuestionnaireAnswers = {
  category: string
  objective: string
  benefit_needs: string
  location_preference: string
  additional: Record<string, string>
}
