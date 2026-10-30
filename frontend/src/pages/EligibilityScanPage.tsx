import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { categoryMarks } from '../data/profile'
import { useAppContext } from '../hooks/useAppContext'
import type { EligibilityScanResponse, ScanSchemeResult } from '../types'

// ── Scan card ─────────────────────────────────────────────────────────────────

function ScanCard({ item, isSaved, onToggle }: {
  item: ScanSchemeResult
  isSaved: boolean
  onToggle: (id: string) => void
}) {
  const { scheme, eligibility, group } = item
  const [expanded, setExpanded] = useState(false)

  const pillClass = group === 'eligible'
    ? 'eligible'
    : group === 'unverified' || group === 'unknown'
      ? 'verify'
      : 'ineligible'
  const pillLabel = group === 'eligible'
    ? 'Likely eligible'
    : group === 'unknown'
      ? 'Needs verification'
      : group === 'unverified'
        ? 'Rules not yet defined'
        : 'Not eligible'

  return (
    <article className="scan-card">
      <div className="scan-card-top">
        <span className="dc-category">{categoryMarks[scheme.category] ?? '✳'} {scheme.category}</span>
        <span className={`dc-status ${pillClass}`}>
          <span className="dc-status-dot" />{pillLabel}
        </span>
        {item.trust && <span className={`trust-score-chip ${item.trust.level}`}>Trust evidence {item.trust.score}/100</span>}
        <button
          className={`dc-save ${isSaved ? 'saved' : ''}`}
          type="button"
          aria-label={isSaved ? 'Remove from saved' : 'Save scheme'}
          onClick={() => onToggle(scheme.scheme_id)}
        >
          {isSaved ? '♥' : '♡'}
        </button>
      </div>

      <h3 className="scan-card-name">{scheme.name}</h3>
      <p className="scan-card-desc">{scheme.description}</p>

      {eligibility.reasons.length > 0 && (
        <p className="scan-card-reason">{eligibility.reasons[0]}</p>
      )}

      <button
        className="scan-card-toggle"
        type="button"
        onClick={() => setExpanded(e => !e)}
      >
        {expanded ? 'Hide details ↑' : 'Show details ↓'}
      </button>

      {expanded && (
        <div className="scan-card-details">
          <div className="scan-detail-section">
            <h4>Benefits</h4>
            <p>{scheme.benefits}</p>
          </div>
          {scheme.documents.length > 0 && (
            <div className="scan-detail-section">
              <h4>Documents required</h4>
              <ul>{scheme.documents.map(d => <li key={d}>{d}</li>)}</ul>
            </div>
          )}
          {scheme.application_process.length > 0 && (
            <div className="scan-detail-section">
              <h4>How to apply</h4>
              <ol>{scheme.application_process.map(s => <li key={s}>{s}</li>)}</ol>
            </div>
          )}
          <div className="scan-card-links">
            <a className="scan-official-btn" href={scheme.official_url} target="_blank" rel="noreferrer">
              Official source ↗
            </a>
            <Link className="scan-details-link" to={`/schemes/${scheme.scheme_id}`}>
              Full details →
            </Link>
          </div>
        </div>
      )}
    </article>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function EligibilityScanPage() {
  const { token, currentUser, userProfile, savedIds, toggleSaved } = useAppContext()
  const [data, setData] = useState<EligibilityScanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'eligible' | 'unknown' | 'unverified' | 'ineligible'>('eligible')
  const hasFetched = useRef(false)

  useEffect(() => {
    if (!token || hasFetched.current) return
    hasFetched.current = true
    void runScan()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function runScan() {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/users/me/eligibility-scan', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({})) as { detail?: string }
        throw new Error(d.detail ?? `Error ${res.status}`)
      }
      const json = await res.json() as EligibilityScanResponse
      setData(json)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  if (!currentUser || !token) {
    return (
      <div className="page-wrap">
        <div className="no-results">
          <span className="no-results-icon">✦</span>
          <h3>Sign in to scan your eligibility</h3>
          <p>Your saved profile is used to check every scheme in the database against your details.</p>
          <Link className="details-link" to="/login">Sign in →</Link>
        </div>
      </div>
    )
  }

  if (!userProfile?.age && !userProfile?.state) {
    return (
      <div className="page-wrap">
        <div className="no-results">
          <span className="no-results-icon">⊙</span>
          <h3>Complete your profile first</h3>
          <p>Your eligibility scan uses the details you've saved in your profile.</p>
          <Link className="details-link" to="/profile">Go to profile →</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page-wrap scan-page">
      {/* Header */}
      <div className="scan-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> ELIGIBILITY SCANNER</div>
          <h1 className="scan-title">Your scheme eligibility</h1>
          {data && (
            <p className="scan-subtitle">
              Checked <strong>{data.totals.total}</strong> schemes against your profile
              {data.profile_summary.state ? ` · ${data.profile_summary.state}` : ''}
              {data.profile_summary.age ? ` · Age ${data.profile_summary.age}` : ''}
              {data.profile_summary.occupation ? ` · ${data.profile_summary.occupation}` : ''}
            </p>
          )}
        </div>
        <button
          className="discover-refine-btn"
          type="button"
          onClick={() => { hasFetched.current = false; void runScan() }}
          disabled={loading}
        >
          {loading ? 'Scanning…' : '↺ Re-scan'}
        </button>
      </div>

      {/* Stats */}
      {data && (
        <div className="scan-stats">
          {[
            { key: 'eligible' as const, label: 'Likely eligible', color: '#4d7a56', bg: '#edf5eb', val: data.totals.eligible },
            { key: 'unknown' as const, label: 'Needs verification', color: '#9a7a42', bg: '#fdf5e4', val: data.totals.unknown },
            { key: 'unverified' as const, label: 'Rules not defined', color: '#6b7870', bg: '#f4f6f2', val: data.totals.unverified },
          ].map(({ key, label, color, bg, val }) => (
            <button
              key={key}
              className={`scan-stat-card ${activeTab === key ? 'active' : ''}`}
              style={{ '--stat-color': color, '--stat-bg': bg } as React.CSSProperties}
              type="button"
              onClick={() => setActiveTab(key)}
            >
              <div className="scan-stat-num">{val}</div>
              <div className="scan-stat-label">{label}</div>
            </button>
          ))}
          <button
            className={`scan-stat-card excluded ${activeTab === 'ineligible' ? 'active' : ''}`}
            type="button"
            onClick={() => setActiveTab('ineligible')}
          >
            <div className="scan-stat-num">{data.totals.ineligible}</div>
            <div className="scan-stat-label">Not eligible</div>
          </button>
        </div>
      )}

      {error && (
        <div className="error-banner" role="alert">
          <strong>Scan failed.</strong>
          <span>{error.includes('Profile not set') ? (
            <>Profile not complete — <Link to="/profile">update your profile</Link> first.</>
          ) : error}</span>
        </div>
      )}

      {loading && (
        <div className="discover-skeleton">
          {[1, 2, 3, 4, 5, 6].map(n => <div key={n} className="skeleton-card" />)}
        </div>
      )}

      {/* Results */}
      {data && !loading && (
        <div className="scan-results">
          {activeTab === 'eligible' && (
            <>
              {data.eligible.length === 0
                ? <div className="no-results"><span className="no-results-icon">✓</span><h3>No schemes matched all your criteria.</h3><p>Try adding more profile details for better results.</p></div>
                : <div className="scan-list">
                    {data.eligible.map(item => (
                      <ScanCard key={item.scheme.scheme_id} item={item} isSaved={savedIds.includes(item.scheme.scheme_id)} onToggle={toggleSaved} />
                    ))}
                  </div>
              }
            </>
          )}
          {activeTab === 'unknown' && (
            <div className="scan-list">
              {data.unknown.length === 0
                ? <div className="no-results"><span className="no-results-icon">⌕</span><h3>No schemes in this group.</h3></div>
                : data.unknown.map(item => (
                    <ScanCard key={item.scheme.scheme_id} item={item} isSaved={savedIds.includes(item.scheme.scheme_id)} onToggle={toggleSaved} />
                  ))
              }
            </div>
          )}
          {activeTab === 'unverified' && (
            <div className="scan-list">
              <div className="scan-notice">
                <span>i</span>
                <p>These schemes exist in the catalogue but don't yet have eligibility rules defined. They may be relevant — check the official source.</p>
              </div>
              {data.unverified.map(item => (
                <ScanCard key={item.scheme.scheme_id} item={item} isSaved={savedIds.includes(item.scheme.scheme_id)} onToggle={toggleSaved} />
              ))}
            </div>
          )}
          {activeTab === 'ineligible' && (
            <div className="scan-list">
              {data.ineligible.length === 0
                ? <div className="no-results"><span className="no-results-icon">✓</span><h3>No schemes were ruled out.</h3></div>
                : data.ineligible.map(item => (
                    <ScanCard key={item.scheme.scheme_id} item={item} isSaved={savedIds.includes(item.scheme.scheme_id)} onToggle={toggleSaved} />
                  ))
              }
            </div>
          )}
        </div>
      )}

      <footer className="page-footer" style={{ marginTop: '40px' }}>
        <span>Eligibility is indicative only. Always verify with the official scheme authority.</span>
      </footer>
    </div>
  )
}
