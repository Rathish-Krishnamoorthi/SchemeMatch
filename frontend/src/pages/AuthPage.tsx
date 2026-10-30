import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAppContext } from '../hooks/useAppContext'

export function AuthPage() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { signup, login } = useAppContext()
  const isSignup = pathname === '/signup'
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSignup && password !== confirmPassword) {
      setMessage("Those passwords don\u2019t match. Please check and try again.")
      return
    }

    setLoading(true)
    setMessage('')
    try {
      if (isSignup) {
        await signup(name, email, password)
        navigate('/onboarding')
      } else {
        await login(email, password)
        navigate('/discover')
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-story" aria-label="About SchemeMatch">
        <Link className="auth-brand" to="/discover" aria-label="SchemeMatch home">
          <span className="brand-mark">s</span>
          <span>scheme<span className="brand-light">match</span></span>
        </Link>

        <div className="auth-story-content">
          <div className="auth-art" aria-hidden="true">
            <span className="auth-art-sun" />
            <span className="auth-art-cloud auth-art-cloud-one" />
            <span className="auth-art-cloud auth-art-cloud-two" />
            <span className="auth-art-hill auth-art-hill-back" />
            <span className="auth-art-hill auth-art-hill-front" />
            <span className="auth-art-path" />
            <span className="auth-art-flower auth-art-flower-one">✳</span>
            <span className="auth-art-flower auth-art-flower-two">✿</span>
          </div>
          <p className="auth-story-kicker">A LITTLE HELP GOES A LONG WAY</p>
          <h1>Find support for the life you&rsquo;re building.</h1>
          <p className="auth-story-copy">
            Discover government schemes that could fit your needs, and take your next step with confidence.
          </p>
          <div className="auth-story-note">
            <span aria-hidden="true">✦</span>
            <p>Clear answers. A more confident next step.</p>
          </div>
        </div>

        <p className="auth-story-footer">MADE FOR EVERY STEP FORWARD</p>
      </section>

      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="auth-panel-top">
          <Link className="auth-back-link" to="/discover">&larr; Back to discovering</Link>
          <p>
            {isSignup ? 'Already have an account?' : 'New to SchemeMatch?'}
            {' '}
            <Link to={isSignup ? '/login' : '/signup'}>{isSignup ? 'Sign in' : 'Create an account'}</Link>
          </p>
        </div>

        <div className="auth-card">
          <div className="auth-heading">
            <span className="auth-heading-icon" aria-hidden="true">{isSignup ? '✳' : '↗'}</span>
            <p className="auth-eyebrow">{isSignup ? 'YOUR NEXT CHAPTER' : 'WELCOME BACK'}</p>
            <h2 id="auth-title">{isSignup ? 'Create your account' : 'Good to see you.'}</h2>
            <p>{isSignup ? 'A little about you helps make this space yours.' : 'Sign in to pick up where you left off.'}</p>
          </div>

          <div className="auth-mode-tabs" aria-label="Account options">
            <Link className={!isSignup ? 'active' : ''} to="/login" aria-current={!isSignup ? 'page' : undefined}>
              Sign in
            </Link>
            <Link className={isSignup ? 'active' : ''} to="/signup" aria-current={isSignup ? 'page' : undefined}>
              Create account
            </Link>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            {isSignup && (
              <label className="auth-field">
                <span>Your name</span>
                <input
                  type="text"
                  name="name"
                  autoComplete="name"
                  placeholder="What should we call you?"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                />
              </label>
            )}
            <label className="auth-field">
              <span>Email address</span>
              <input
                type="email"
                name="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label className="auth-field">
              <span>Password</span>
              <span className="auth-password-wrap">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  autoComplete={isSignup ? 'new-password' : 'current-password'}
                  placeholder={isSignup ? 'At least 8 characters' : 'Enter your password'}
                  minLength={isSignup ? 8 : undefined}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <button
                  className="auth-password-toggle"
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </span>
            </label>
            {isSignup && (
              <label className="auth-field">
                <span>Confirm password</span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="confirm-password"
                  autoComplete="new-password"
                  placeholder="Enter your password again"
                  minLength={8}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  required
                />
              </label>
            )}
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading
                ? (isSignup ? 'Creating account\u2026' : 'Signing in\u2026')
                : (isSignup ? 'Create your account' : 'Sign in')}
              {!loading && <span aria-hidden="true">&rarr;</span>}
            </button>
            {message && <p className="auth-message" role="alert">{message}</p>}
          </form>

          <div className="auth-privacy-note">
            <span aria-hidden="true">⌑</span>
            <p>Your information stays yours. We&rsquo;ll only use it to help you find support.</p>
          </div>
          <p className="auth-disclaimer">
            You can explore the scheme directory without creating an account.
          </p>
        </div>
      </section>
    </main>
  )
}
