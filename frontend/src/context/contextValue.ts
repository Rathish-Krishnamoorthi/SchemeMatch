import { createContext } from 'react'
import type { AuthUser, Recommendation, UserDemographicProfile, UserProfileSettings } from '../types'

export type AppContextValue = {
  recommendations: Recommendation[]
  setRecommendations: (value: Recommendation[]) => void
  disclaimer: string
  setDisclaimer: (value: string) => void
  excludedCount: number
  setExcludedCount: (value: number) => void
  savedIds: string[]
  toggleSaved: (schemeId: string) => void
  profileSettings: UserProfileSettings
  saveProfileSettings: (settings: UserProfileSettings) => boolean
  apiReady: boolean
  // Auth
  currentUser: AuthUser | null
  token: string | null
  signup: (name: string, email: string, password: string) => Promise<void>
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  // Demographic profile
  userProfile: UserDemographicProfile | null
  saveUserProfile: (profile: UserDemographicProfile, token?: string) => Promise<void>
  loadUserProfile: (token?: string) => Promise<UserDemographicProfile | null>
}

export const AppContext = createContext<AppContextValue | null>(null)
