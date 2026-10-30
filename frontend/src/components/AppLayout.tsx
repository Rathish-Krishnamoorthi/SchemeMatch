import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAppContext } from '../hooks/useAppContext'

export function AppLayout() {
  const { apiReady, savedIds, profileSettings, currentUser, logout } = useAppContext()
  const location = useLocation()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }
  const pageName = location.pathname.startsWith('/profile')
    ? 'Profile'
    : location.pathname.startsWith('/saved')
      ? 'Saved schemes'
      : location.pathname.startsWith('/eligibility-scan')
        ? 'Eligibility scan'
        : location.pathname.startsWith('/scheme-finder')
          ? 'Required scheme finder'
          : location.pathname.startsWith('/llm-reasoning')
            ? 'LLM scheme reasoning'
          : location.pathname.startsWith('/trust-score')
            ? 'Trust scores'
            : location.pathname.startsWith('/schemes/')
              ? 'Scheme details'
              : 'Discover'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to="/discover" aria-label="SchemeMatch home">
          <span className="brand-mark">s</span>
          <span>scheme<span className="brand-light">match</span></span>
        </NavLink>
        <div className="sidebar-label">YOUR SPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to="/discover">
            <span className="nav-icon">⌕</span> Discover schemes
            <span className="nav-arrow">›</span>
          </NavLink>
          <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to="/eligibility-scan">
            <span className="nav-icon">✓</span> Eligibility scan
            <span className="nav-arrow">›</span>
          </NavLink>
          <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to="/scheme-finder">
            <span className="nav-icon">↗</span> Required scheme finder
            <span className="nav-arrow">›</span>
          </NavLink>
          <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to="/llm-reasoning">
            <span className="nav-icon">✧</span> LLM scheme reasoning
            <span className="nav-arrow">›</span>
          </NavLink>
          <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to="/trust-score">
            <span className="nav-icon">◎</span> Trust scores
            <span className="nav-arrow">›</span>
          </NavLink>
          <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to="/saved">
            <span className="nav-icon">♡</span> Saved schemes
            {savedIds.length > 0 && <span className="saved-count">{savedIds.length}</span>}
          </NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="side-help">
            <div className="help-mark">?</div>
            <strong>Need a hand?</strong>
            <p>Every scheme links to its official source. Always verify details before you apply.</p>
            <a href="https://www.myscheme.gov.in/" target="_blank" rel="noreferrer">Visit myScheme <span>↗</span></a>
          </div>
          <div className={`api-status ${apiReady ? 'connected' : ''}`}>
            <span className="status-dot" />
            {apiReady ? 'Local service connected' : 'Waiting for local service'}
          </div>
          <div className="sidebar-foot">MADE FOR EVERY STEP FORWARD</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb"><NavLink to="/discover">Home</NavLink> <span>/</span> <strong>{pageName}</strong></div>
          <div className="topbar-actions">
            <a className="topbar-link" href="https://www.myscheme.gov.in/" target="_blank" rel="noreferrer">
              Official scheme directory <span>↗</span>
            </a>
            {currentUser ? (
              <button className="auth-nav-link" type="button" onClick={handleLogout}>
                Sign out
              </button>
            ) : (
              <NavLink className="auth-nav-link" to="/login">Sign in</NavLink>
            )}
            <NavLink className={({ isActive }) => `profile-trigger ${isActive ? 'selected' : ''}`} to="/profile" aria-label="Open your profile">
              <span className="profile-trigger-avatar">
                {profileSettings.image ? <img src={profileSettings.image} alt="" /> : profileSettings.animal}
              </span>
              <span className="profile-trigger-label">
                {currentUser?.name ?? profileSettings.name ?? 'My profile'}
              </span>
            </NavLink>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  )
}
