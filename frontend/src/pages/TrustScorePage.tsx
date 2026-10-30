import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { TrustScoresResponse } from '../types'

export function TrustScorePage() {
  const [data, setData] = useState<TrustScoresResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/trust-scores', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => ({})) as { detail?: string }
          throw new Error(body.detail ?? `Could not load trust scores (${response.status}).`)
        }
        return response.json() as Promise<TrustScoresResponse>
      })
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== 'AbortError') setError(reason.message)
      })
    return () => controller.abort()
  }, [])

  return (
    <div className="page-wrap trust-page">
      <header className="scan-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> SOURCE & CONTENT EVIDENCE</div>
          <h1 className="scan-title">Scheme trust scores</h1>
          <p className="scan-subtitle">
            Scores reflect evidence recorded in the catalogue, not scheme eligibility or a guarantee of official accuracy.
          </p>
        </div>
        <Link className="discover-edit-link" to="/discover">Back to Discover →</Link>
      </header>

      {error && <div className="error-banner" role="alert"><strong>Could not load trust scores.</strong><span>{error}</span></div>}
      {!data && !error && (
        <div className="discover-skeleton">{[1, 2, 3].map((n) => <div key={n} className="skeleton-card" />)}</div>
      )}
      {data && (
        <>
          <div className="trust-intro">
            <strong>{data.total} schemes assessed</strong>
            <p>
              Up to 100 points are awarded for an Indian government domain, HTTPS, source attribution,
              recent verification, and completeness of the stored scheme record.
            </p>
          </div>
          <div className="trust-list">
            {data.schemes.map(({ scheme, trust }) => (
              <article className="trust-card" key={scheme.scheme_id}>
                <div className="trust-card-heading">
                  <div>
                    <span className="dc-category">{scheme.category}</span>
                    <h2>{scheme.name}</h2>
                  </div>
                  <div className={`trust-score ${trust.level}`}>
                    <strong>{trust.score}</strong><span>/100</span>
                  </div>
                </div>
                <div className="trust-meter" role="meter" aria-label="Trust evidence score" aria-valuemin={0} aria-valuemax={100} aria-valuenow={trust.score}>
                  <span className={trust.level} style={{ width: `${trust.score}%` }} />
                </div>
                <p className="trust-level-label">{trust.level} evidence completeness</p>
                <ul className="trust-evidence">
                  {trust.evidence.map((factor) => (
                    <li key={factor.factor}>
                      <span className="trust-evidence-points">{factor.points} pts</span>
                      <span><strong>{factor.factor}</strong><small>{factor.detail}</small></span>
                    </li>
                  ))}
                </ul>
                <div className="trust-card-footer">
                  <span>Source: {scheme.source || 'Not recorded'}</span>
                  <a href={scheme.official_url} target="_blank" rel="noreferrer">Official source ↗</a>
                </div>
              </article>
            ))}
          </div>
          <p className="disclaimer"><span>!</span>{data.disclaimer}</p>
        </>
      )}
    </div>
  )
}
