import { useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { AppContext } from './contextValue'
import type { AuthUser, Recommendation, UserDemographicProfile, UserProfileSettings } from '../types'
import { initialProfile } from '../data/profile'

const initialProfileSettings: UserProfileSettings = {
  name: '',
  animal: '🦊',
  image: '',
}

function readProfileSettings(): UserProfileSettings {
  try {
    const stored = localStorage.getItem('schemematch.profile')
    if (!stored) return initialProfileSettings

    const parsed: unknown = JSON.parse(stored)
    if (typeof parsed !== 'object' || parsed === null) return initialProfileSettings
    const settings = parsed as Record<string, unknown>
    return {
      name: typeof settings.name === 'string' ? settings.name : initialProfileSettings.name,
      animal: typeof settings.animal === 'string' ? settings.animal : initialProfileSettings.animal,
      image: typeof settings.image === 'string' ? settings.image : initialProfileSettings.image,
    }
  } catch (error) {
    console.error('Unable to load the saved profile.', error)
    return initialProfileSettings
  }
}

function readSessionRecommendations(): Recommendation[] {
  try {
    const stored = sessionStorage.getItem('schemematch.recommendations')
    return stored ? JSON.parse(stored) as Recommendation[] : []
  } catch {
    return []
  }
}

function readSavedIds(): string[] {
  try {
    const stored = localStorage.getItem('schemematch.saved')
    return stored ? JSON.parse(stored) as string[] : []
  } catch {
    return []
  }
}

function readStoredAuth(): { user: AuthUser; token: string } | null {
  try {
    const stored = localStorage.getItem('schemematch.auth')
    if (!stored) return null
    const parsed = JSON.parse(stored) as { user: AuthUser; token: string }
    if (!parsed.token || !parsed.user) return null
    return parsed
  } catch {
    return null
  }
}

function readStoredDemographicProfile(): UserDemographicProfile | null {
  try {
    const stored = localStorage.getItem('schemematch.demographic')
    if (!stored) return null
    return JSON.parse(stored) as UserDemographicProfile
  } catch {
    return null
  }
}

async function getApiErrorMessage(response: Response, fallback: string): Promise<string> {
  const body = await response.text()
  if (response.headers.get('content-type')?.includes('application/json')) {
    try {
      const data: unknown = JSON.parse(body)
      if (typeof data === 'object' && data !== null && 'detail' in data) {
        const detail = data.detail
        if (typeof detail === 'string') return detail
        if (Array.isArray(detail)) {
          const messages = detail
            .map((item) => typeof item === 'object' && item !== null && 'msg' in item ? item.msg : null)
            .filter((message): message is string => typeof message === 'string')
          if (messages.length) return messages.join(' ')
        }
      }
    } catch {
      return `${fallback} (HTTP ${response.status}).`
    }
  }
  return `${fallback} (HTTP ${response.status}).`
}

export function AppProvider({ children }: PropsWithChildren) {
  const [recommendations, setRecommendations] = useState(readSessionRecommendations)
  const [disclaimer, setDisclaimer] = useState('')
  const [excludedCount, setExcludedCount] = useState(0)
  const [savedIds, setSavedIds] = useState(readSavedIds)
  const [profileSettings, setProfileSettings] = useState(readProfileSettings)
  const [apiReady, setApiReady] = useState(false)

  // Auth state — rehydrated from localStorage on load
  const storedAuth = readStoredAuth()
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(storedAuth?.user ?? null)
  const [token, setToken] = useState<string | null>(storedAuth?.token ?? null)

  // Demographic profile — cached locally, synced with backend when signed in
  const [userProfile, setUserProfile] = useState<UserDemographicProfile | null>(readStoredDemographicProfile)

  useEffect(() => {
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error('Backend health check failed')
        return response.json()
      })
      .then(() => setApiReady(true))
      .catch(() => setApiReady(false))
  }, [])

  useEffect(() => {
    if (!token) return

    const controller = new AbortController()
    fetch('/api/users/me/profile', {
      headers: { Authorization: ['Bea', 'rer ', token].join('') },
      signal: controller.signal,
    })
      .then((response) => {
        if (response.status !== 401) return
        setCurrentUser(null)
        setToken(null)
        setUserProfile(null)
        localStorage.removeItem('schemematch.auth')
        localStorage.removeItem('schemematch.demographic')
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== 'AbortError') {
          console.error('Unable to verify the saved sign-in session.', error)
        }
      })

    return () => controller.abort()
  }, [token])

  useEffect(() => {
    sessionStorage.setItem('schemematch.recommendations', JSON.stringify(recommendations))
  }, [recommendations])

  useEffect(() => {
    localStorage.setItem('schemematch.saved', JSON.stringify(savedIds))
  }, [savedIds])

  function toggleSaved(schemeId: string) {
    setSavedIds((current) => current.includes(schemeId)
      ? current.filter((savedId) => savedId !== schemeId)
      : [...current, schemeId])
  }

  function saveProfileSettings(settings: UserProfileSettings) {
    setProfileSettings(settings)
    try {
      localStorage.setItem('schemematch.profile', JSON.stringify(settings))
      return true
    } catch (error) {
      console.error('Unable to save the profile on this device.', error)
      return false
    }
  }

  /** Persist the demographic profile to MongoDB (if signed in) and local cache. */
  const saveUserProfile = useCallback(async (profile: UserDemographicProfile, authToken?: string): Promise<void> => {
    const activeToken = authToken ?? token
    setUserProfile(profile)
    localStorage.setItem('schemematch.demographic', JSON.stringify(profile))
    if (activeToken) {
      const response = await fetch('/api/users/me/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${activeToken}` },
        body: JSON.stringify(profile),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({})) as { detail?: string }
        throw new Error(data.detail ?? `Failed to save profile (${response.status})`)
      }
    }
  }, [token])

  /** Load the demographic profile from MongoDB and cache it locally. */
  const loadUserProfile = useCallback(async (authToken?: string): Promise<UserDemographicProfile | null> => {
    const activeToken = authToken ?? token
    if (!activeToken) return null
    try {
      const response = await fetch('/api/users/me/profile', {
        headers: { Authorization: `Bearer ${activeToken}` },
      })
      if (!response.ok) return null
      const raw = await response.json() as Record<string, unknown>
      if (Object.keys(raw).length === 0) return null
      // Coerce backend booleans/numbers back to form strings
      const toBoolStr = (v: unknown) => v === null || v === undefined ? '' : v ? 'yes' : 'no'
      const toStr = (v: unknown) => (v === null || v === undefined) ? '' : String(v)
      const profile: UserDemographicProfile = {
        ...initialProfile,
        age: toStr(raw.age),
        state: toStr(raw.state),
        district: toStr(raw.district),
        annual_income: toStr(raw.annual_income),
        occupation: toStr(raw.occupation),
        profession: toStr(raw.profession),
        education_level: toStr(raw.education_level),
        employment_status: toStr(raw.employment_status),
        land_holding_acres: toStr(raw.land_holding_acres),
        institution_type: toStr(raw.institution_type),
        category: toStr(raw.category),
        gender: toStr(raw.gender),
        marital_status: toStr(raw.marital_status),
        dependants: toStr(raw.dependants),
        disability_type: toStr(raw.disability_type),
        need: toStr(raw.need),
        student_status: toBoolStr(raw.student_status),
        farmer_status: toBoolStr(raw.farmer_status),
        disability_status: toBoolStr(raw.disability_status),
      }
      setUserProfile(profile)
      localStorage.setItem('schemematch.demographic', JSON.stringify(profile))
      return profile
    } catch {
      return null
    }
  }, [token])

  const signup = useCallback(async (name: string, email: string, password: string) => {
    const response = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    })
    if (!response.ok) {
      throw new Error(await getApiErrorMessage(response, 'Signup failed.'))
    }
    const { token: newToken, user } = await response.json() as { token: string; user: AuthUser }
    setCurrentUser(user)
    setToken(newToken)
    localStorage.setItem('schemematch.auth', JSON.stringify({ token: newToken, user }))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!response.ok) {
      throw new Error(await getApiErrorMessage(response, 'Login failed.'))
    }
    const { token: newToken, user } = await response.json() as { token: string; user: AuthUser }
    setCurrentUser(user)
    setToken(newToken)
    localStorage.setItem('schemematch.auth', JSON.stringify({ token: newToken, user }))
    // Await the profile load so state is populated before the caller navigates
    await loadUserProfile(newToken)
  }, [loadUserProfile])

  const logout = useCallback(() => {
    setCurrentUser(null)
    setToken(null)
    setUserProfile(null)
    localStorage.removeItem('schemematch.auth')
    localStorage.removeItem('schemematch.demographic')
  }, [])

  const value = useMemo(() => ({
    recommendations,
    setRecommendations,
    disclaimer,
    setDisclaimer,
    excludedCount,
    setExcludedCount,
    savedIds,
    toggleSaved,
    profileSettings,
    saveProfileSettings,
    apiReady,
    currentUser,
    token,
    signup,
    login,
    logout,
    userProfile,
    saveUserProfile,
    loadUserProfile,
  }), [recommendations, disclaimer, excludedCount, savedIds, profileSettings, apiReady, currentUser, token, signup, login, logout, userProfile, saveUserProfile, loadUserProfile])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
