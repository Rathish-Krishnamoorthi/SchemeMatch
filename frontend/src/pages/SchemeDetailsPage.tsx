import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { categoryMarks } from '../data/profile'
import { useAppContext } from '../hooks/useAppContext'
import type { Scheme } from '../types'

export function SchemeDetailsPage() {
  const { schemeId } = useParams()
  const { recommendations } = useAppContext()
  const recommended = recommendations.find((item) => item.scheme.scheme_id === schemeId)
  return (
    <SchemeDetailsContent
      key={schemeId}
      schemeId={schemeId}
      recommended={recommended}
    />
  )
}

type SchemeDetailsContentProps = {
  schemeId: string | undefined
  recommended: ReturnType<typeof useAppContext>['recommendations'][number] | undefined
}

function SchemeDetailsContent({ schemeId, recommended }: SchemeDetailsContentProps) {
  const [scheme, setScheme] = useState<Scheme | null>(recommended?.scheme ?? null)
  const [loading, setLoading] = useState(!recommended)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!schemeId || recommended) return
    const controller = new AbortController()
    fetch(`/api/schemes/${encodeURIComponent(schemeId)}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 404 ? 'Scheme not found.' : 'Unable to load scheme details.')
        return response.json() as Promise<Scheme>
      })
      .then(setScheme)
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== 'AbortError') setError(reason.message)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [schemeId, recommended])

  if (loading) {
    return <div className="page-wrap"><div className="no-results results-empty-page"><h3>Loading scheme details…</h3></div></div>
  }
  if (!scheme || error) {
    return (
      <div className="page-wrap">
        <div className="no-results results-empty-page">
          <span className="no-results-icon">!</span>
          <h3>{error || 'Scheme not found.'}</h3>
          <p>Return to your recommendations to explore available schemes.</p>
          <Link className="details-link" to="/recommendations">Back to recommendations <span>→</span></Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page-wrap">
      <div className="scheme-detail-page">
        <Link className="back-link" to={recommended ? '/recommendations' : '/discover'}>← Back to {recommended ? 'recommendations' : 'discover'}</Link>
        <section className="scheme-detail-card">
          <span className="category-chip"><span>{categoryMarks[scheme.category] ?? '✳'}</span>{scheme.category}</span>
          <h1>{scheme.name}</h1>
          <p className="modal-description">{scheme.description}</p>
          {recommended && (
            <div className="modal-status">
              <span className={`eligibility-pill ${recommended.eligibility.status.toLowerCase()}`}>
                <span className="pill-dot" />{recommended.eligibility.status === 'LIKELY_ELIGIBLE' ? 'Likely eligible' : 'Needs verification'}
              </span>
              <span>Match score <strong>{recommended.match_score}</strong></span>
              <span>{recommended.eligibility.reasons[0]}</span>
            </div>
          )}
          <div className="detail-sections">
            <section className="modal-section"><h3>About this support</h3><p>{scheme.benefits}</p></section>
            <section className="modal-section">
              <h3>Before you apply</h3>
              {scheme.application_process.length
                ? <ol>{scheme.application_process.map((step) => <li key={step}>{step}</li>)}</ol>
                : <p>Check the official source for current application instructions.</p>}
            </section>
            <section className="modal-section">
              <h3>Documents to check</h3>
              {scheme.documents.length
                ? <ul>{scheme.documents.map((document) => <li key={document}>{document}</li>)}</ul>
                : <p>Document requirements are not listed in this catalogue. Verify them with the scheme authority.</p>}
            </section>
          </div>
          <div className="detail-verification">
            <strong>Eligibility needs official verification</strong>
            <p>{scheme.verification_note || 'This information is indicative and is not an official eligibility decision.'}</p>
          </div>
          <div className="source-note">
            <span>Source: {scheme.source}</span>
            <span>{scheme.last_verified ? `Last verified ${scheme.last_verified}` : 'Verification date not available'}</span>
          </div>
          <a className="submit-button modal-official" href={scheme.official_url} target="_blank" rel="noreferrer">Visit official source <span>↗</span></a>
        </section>
      </div>
    </div>
  )
}
