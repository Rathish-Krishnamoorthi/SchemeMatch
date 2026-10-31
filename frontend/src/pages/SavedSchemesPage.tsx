import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Pagination } from '../components/Pagination'
import { useAppContext } from '../hooks/useAppContext'
import { usePagination } from '../hooks/usePagination'
import type { Scheme } from '../types'

export function SavedSchemesPage() {
  const { savedIds, toggleSaved } = useAppContext()
  const [schemes, setSchemes] = useState<Scheme[]>([])
  const [error, setError] = useState('')
  const savedSchemes = useMemo(
    () => schemes.filter((scheme) => savedIds.includes(scheme.scheme_id)),
    [schemes, savedIds],
  )
  const pagination = usePagination(savedSchemes)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/schemes', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Could not load the scheme catalogue (${response.status}).`)
        return response.json() as Promise<Scheme[]>
      })
      .then(setSchemes)
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== 'AbortError') setError(reason.message)
      })
    return () => controller.abort()
  }, [])

  return (
    <div className="page-wrap">
      <header className="scan-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> YOUR SHORTLIST</div>
          <h1 className="scan-title">Saved schemes</h1>
          <p className="scan-subtitle">Schemes you saved from Discover or the Required Scheme Finder.</p>
        </div>
      </header>
      {error && <div className="error-banner" role="alert"><strong>Could not load saved schemes.</strong><span>{error}</span></div>}
      {!error && savedSchemes.length === 0 && (
        <div className="no-results">
          <span className="no-results-icon">♡</span>
          <h3>Nothing saved just yet.</h3>
          <p>Save a scheme from Discover or the Scheme Finder to keep it close.</p>
          <Link className="details-link" to="/discover">Explore eligible schemes →</Link>
        </div>
      )}
      <div className="scan-list">
        {pagination.items.map((scheme) => (
          <article className="scan-card" key={scheme.scheme_id}>
            <div className="scan-card-top">
              <span className="dc-category">{scheme.category}</span>
              <button
                className="dc-save saved"
                type="button"
                aria-label="Remove from saved"
                onClick={() => toggleSaved(scheme.scheme_id)}
              >
                ♥
              </button>
            </div>
            <h2 className="scan-card-name">{scheme.name}</h2>
            <p className="scan-card-desc">{scheme.description}</p>
            <div className="scan-card-links">
              <Link className="scan-details-link" to={`/schemes/${scheme.scheme_id}`}>Full details →</Link>
              <a className="scan-official-btn" href={scheme.official_url} target="_blank" rel="noreferrer">Official source ↗</a>
            </div>
          </article>
        ))}
      </div>
      <Pagination
        page={pagination.page}
        pageCount={pagination.pageCount}
        pageSize={pagination.pageSize}
        totalItems={pagination.totalItems}
        onPageChange={pagination.setPage}
      />
    </div>
  )
}
