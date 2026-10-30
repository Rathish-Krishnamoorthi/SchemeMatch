import { Link } from 'react-router-dom'
import { categoryMarks } from '../data/profile'
import type { Recommendation } from '../types'

type SchemeCardProps = {
  recommendation: Recommendation
  index: number
  isSaved: boolean
  onToggleSaved: (schemeId: string) => void
}

export function SchemeCard({ recommendation, index, isSaved, onToggleSaved }: SchemeCardProps) {
  const { scheme, eligibility } = recommendation
  const likelyEligible = eligibility.status === 'LIKELY_ELIGIBLE'

  return (
    <article className="scheme-card">
      <div className="scheme-card-top">
        <span className="scheme-index">{String(index + 1).padStart(2, '0')}</span>
        <span className="category-chip"><span>{categoryMarks[scheme.category] ?? '✳'}</span>{scheme.category}</span>
        <button className={`save-button ${isSaved ? 'is-saved' : ''}`} onClick={() => onToggleSaved(scheme.scheme_id)} aria-label={isSaved ? 'Remove saved scheme' : 'Save scheme'}>
          {isSaved ? '♥' : '♡'}
        </button>
      </div>
      <h3>{scheme.name}</h3>
      <p className="scheme-description">{scheme.description}</p>
      <div className="scheme-status-row">
        <span className={`eligibility-pill ${eligibility.status.toLowerCase()}`}>
          <span className="pill-dot" />{likelyEligible ? 'Likely eligible' : 'Needs verification'}
        </span>
        <span className="match-label">Match score <strong>{recommendation.match_score}</strong></span>
      </div>
      {eligibility.reasons[0] && <p className="eligibility-reason">{eligibility.reasons[0]}</p>}
      <div className="scheme-card-footer">
        <Link className="details-link" to={`/schemes/${scheme.scheme_id}`}>Explore scheme <span>→</span></Link>
        <a className="official-link" href={scheme.official_url} target="_blank" rel="noreferrer">Official source ↗</a>
      </div>
    </article>
  )
}
