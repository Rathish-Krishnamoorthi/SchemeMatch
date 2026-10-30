import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import { AppLayout } from './components/AppLayout'
import { DiscoverPage } from './pages/DiscoverPage'
import { RecommendationsPage } from './pages/RecommendationsPage'
import { SavedSchemesPage } from './pages/SavedSchemesPage'
import { SchemeDetailsPage } from './pages/SchemeDetailsPage'
import { ProfilePage } from './pages/ProfilePage'
import { AuthPage } from './pages/AuthPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { EligibilityScanPage } from './pages/EligibilityScanPage'
import { SchemeFinderPage } from './pages/SchemeFinderPage'
import { TrustScorePage } from './pages/TrustScorePage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Routes>
          <Route path="/login" element={<AuthPage key="login" />} />
          <Route path="/signup" element={<AuthPage key="signup" />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route element={<AppLayout />}>
            <Route index element={<Navigate to="/discover" replace />} />
            <Route path="/discover" element={<DiscoverPage />} />
            <Route path="/eligibility-scan" element={<EligibilityScanPage />} />
            <Route path="/scheme-finder" element={<SchemeFinderPage />} />
            <Route path="/llm-reasoning" element={<SchemeFinderPage />} />
            <Route path="/trust-score" element={<TrustScorePage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/saved" element={<SavedSchemesPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/schemes/:schemeId" element={<SchemeDetailsPage />} />
            <Route path="*" element={<Navigate to="/discover" replace />} />
          </Route>
        </Routes>
      </AppProvider>
    </BrowserRouter>
  )
}

export default App
