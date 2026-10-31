import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Pagination } from '../components/Pagination'
import { usePagination } from '../hooks/usePagination'
import { useAppContext } from '../hooks/useAppContext'
import type { EligibleSchemesResponse } from '../types'

export function DiscoverPage() {
  const { currentUser, token, userProfile, savedIds, toggleSaved } = useAppContext()
  const [requestState, setRequestState] = useState<{
    key: string
    data?: EligibleSchemesResponse
    error?: string
  }>({ key: '' })
  const [refreshKey, setRefreshKey] = useState(0)
  const requestKey = `${token ?? 'signed-out'}:${refreshKey}`
  const data = requestState.key === requestKey ? requestState.data ?? null : null
  const error = requestState.key === requestKey ? requestState.error ?? '' : ''
  const loading = Boolean(token) && requestState.key !== requestKey
  const pagination = usePagination(data?.schemes ?? [])

  useEffect(() => {
    if (!token) return

    const controller = new AbortController()
    fetch('/api/users/me/eligible-schemes', {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => ({})) as { detail?: string }
          throw new Error(body.detail ?? `Could not load eligible schemes (${response.status}).`)
        }
        return response.json() as Promise<EligibleSchemesResponse>
      })
      .then((responseData) => setRequestState({ key: requestKey, data: responseData }))
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== 'AbortError') {
          setRequestState({ key: requestKey, error: reason.message })
        }
      })
    return () => controller.abort()
  }, [token, refreshKey, requestKey])

  if (!currentUser || !token) {
    return (
      <div className="page-wrap">
        <div className="discover-cold">
          <div className="discover-cold-text">
            <div className="eyebrow"><span className="eyebrow-line" /> PROFILE-BASED DISCOVERY</div>
            <h1>Find support<br /><em>built for you.</em></h1>
            <p>Sign in to compare your saved profile against the eligibility rules recorded for every scheme.</p>
          </div>
          <div className="discover-cold-actions">
            <Link className="discover-cta-primary" to="/login">Sign in <span>→</span></Link>
            <Link className="discover-cta-secondary" to="/signup">Create an account</Link>
          </div>
        </div>
      </div>
    )
  }

  const profileSummary = data?.profile_summary
  const noSavedProfile = error.toLowerCase().includes('profile not set')

  return (
    <div className="page-wrap discover-page">
      <div className="discover-header">
        <div className="discover-header-left">
          <div className="eyebrow"><span className="eyebrow-line" /> RULE-BASED DISCOVERY</div>
          <h1 className="discover-title">{loading ? 'Checking your eligibility…' : 'Schemes you may qualify for'}</h1>
          <p className="discover-profile-summary">
            Evaluated against your saved profile
            {profileSummary?.occupation && <> · <span>{profileSummary.occupation}</span></>}
            {profileSummary?.state && <> · <span>{profileSummary.state}</span></>}
            {profileSummary?.age != null && <> · <span>Age {profileSummary.age}</span></>}
            {!profileSummary && userProfile?.occupation && <> · <span>{userProfile.occupation}</span></>}
          </p>
        </div>
        <div className="discover-header-right">
          <Link className="discover-edit-link" to="/profile">Edit profile →</Link>
          <Link className="discover-edit-link" to="/eligibility-scan">Eligibility scan →</Link>
        </div>
      </div>

      <div className="discover-module-links">
        <Link to="/scheme-finder">Looking for a specific type of support? Open the Required Scheme Finder →</Link>
        <Link to="/trust-score">How scheme trust scores are calculated →</Link>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          <strong>{noSavedProfile ? 'Complete your profile first.' : 'Could not load eligible schemes.'}</strong>
          <span>
            {noSavedProfile
              ? <><Link to="/profile">Add profile details</Link> before checking eligibility.</>
              : error}
          </span>
        </div>
      )}

      {loading && (
        <div className="discover-skeleton">
          {[1, 2, 3, 4].map((number) => <div key={number} className="skeleton-card" />)}
        </div>
      )}

      {data && !loading && (
        <>
          <div className="discover-results-meta">
            <span className="result-count">
              {data.eligible_count} eligible of {data.total_schemes} schemes checked
            </span>
            <button
              className="discover-refresh-btn"
              type="button"
              onClick={() => {
                pagination.setPage(1)
                setRefreshKey((current) => current + 1)
              }}
            >
              ↺ Refresh
            </button>
          </div>

          {data.schemes.length === 0 ? (
            <div className="no-results">
              <span className="no-results-icon">⌕</span>
              <h3>No schemes match all recorded eligibility rules.</h3>
              <p>Check the Eligibility Scan for schemes needing more profile details or verified rules.</p>
              <Link className="details-link" to="/eligibility-scan">View eligibility scan →</Link>
            </div>
          ) : (
            <>
              <div className="scan-list discover-eligible-list">
              {pagination.items.map(({ scheme, eligibility, trust }, index) => {
                const isSaved = savedIds.includes(scheme.scheme_id)
                return (
                  <article className="scan-card" key={scheme.scheme_id}>
                    <div className="scan-card-top">
                      <span className="dc-category">{scheme.category}</span>
                      <span className="dc-status eligible"><span className="dc-status-dot" />Likely eligible</span>
                      <span className={`trust-score-chip ${trust.level}`}>Trust evidence {trust.score}/100</span>
                      <button
                        className={`dc-save ${isSaved ? 'saved' : ''}`}
                        type="button"
                        aria-label={isSaved ? 'Remove from saved' : 'Save scheme'}
                        onClick={() => toggleSaved(scheme.scheme_id)}
                      >
                        {isSaved ? '♥' : '♡'}
                      </button>
                    </div>
                    <h2 className="scan-card-name">{(pagination.page - 1) * pagination.pageSize + index + 1}. {scheme.name}</h2>
                    <p className="scan-card-desc">{scheme.description}</p>
                    {eligibility.reasons.map((reason) => <p className="scan-card-reason" key={reason}>{reason}</p>)}
                    <div className="scan-card-details discover-scheme-details">
                      <div className="scan-detail-section">
                        <h4>Benefits</h4>
                        <p>{scheme.benefits}</p>
                      </div>
                      <div className="scan-detail-section">
                        <h4>Eligibility details</h4>
                        <p>{eligibility.reasons.join(' ')}</p>
                      </div>
                      <div className="scan-detail-section">
                        <h4>Required documents</h4>
                        {scheme.documents.length
                          ? <ul>{scheme.documents.map((document) => <li key={document}>{document}</li>)}</ul>
                          : <p>Not listed in the catalogue; confirm requirements with the scheme authority.</p>}
                      </div>
                      <div className="scan-detail-section">
                        <h4>Application</h4>
                        {scheme.application_process.length
                          ? <ol>{scheme.application_process.map((step) => <li key={step}>{step}</li>)}</ol>
                          : <p>Check the official source for current application instructions.</p>}
                      </div>
                    </div>
                    <div className="scan-card-links">
                      <Link className="scan-details-link" to={`/schemes/${scheme.scheme_id}`}>Full details →</Link>
                      <a className="scan-official-btn" href={scheme.official_url} target="_blank" rel="noreferrer">Apply / official source ↗</a>
                    </div>
                  </article>
                )
              })}
              </div>
              <Pagination
                page={pagination.page}
                pageCount={pagination.pageCount}
                pageSize={pagination.pageSize}
                totalItems={pagination.totalItems}
                onPageChange={pagination.setPage}
              />
            </>
          )}
          <div className="disclaimer">
            <span>!</span><p>{data.disclaimer} Unknown and unverified schemes are not presented as eligible.</p>
          </div>
        </>
      )}
    </div>
  )
}
