import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAppContext } from '../hooks/useAppContext'
import type { Recommendation } from '../types'
import { PageFooter } from './PageFooter'
import { SchemeCard } from './SchemeCard'

type RecommendationResultsProps = {
  title: string
  items: Recommendation[]
  showFilters?: boolean
  showNotice?: boolean
}

export function RecommendationResults({
  title,
  items,
  showFilters = true,
  showNotice = false,
}: RecommendationResultsProps) {
  const { disclaimer, excludedCount, savedIds, toggleSaved } = useAppContext()
  const [activeCategory, setActiveCategory] = useState('All schemes')
  const categories = useMemo(
    () => ['All schemes', ...new Set(items.map(({ scheme }) => scheme.category))],
    [items],
  )
  const visibleItems = items.filter(({ scheme }) =>
    activeCategory === 'All schemes' || scheme.category === activeCategory)

  return (
    <div className="page-wrap">
      <section className="results-column results-page" aria-live="polite">
        <div className="results-topline">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> YOUR STARTING POINT</div>
            <h2>{title}</h2>
          </div>
          <span className="result-count">{items.length} {items.length === 1 ? 'scheme' : 'schemes'}</span>
        </div>

        {showNotice && items.length > 0 && (
          <div className="catalog-notice">
            <span className="notice-icon">i</span>
            <p>This starter catalogue is intentionally cautious. Scheme rules have not been independently verified here, so check the official source before acting.</p>
          </div>
        )}

        {showFilters && items.length > 0 && (
          <div className="filter-row">
            <div className="view-tabs">
              <Link className="selected" to="/recommendations">For you</Link>
              <Link to="/saved">Saved <span>{savedIds.length}</span></Link>
            </div>
            <select aria-label="Filter by category" value={activeCategory} onChange={(event) => setActiveCategory(event.target.value)}>
              {categories.map((category) => <option key={category}>{category}</option>)}
            </select>
          </div>
        )}

        {items.length === 0 ? (
          <div className="no-results">
            <span className="no-results-icon">{title.includes('Saved') ? '♡' : '⌕'}</span>
            <h3>{title.includes('Saved') ? 'Nothing saved just yet.' : 'No recommendations yet.'}</h3>
            <p>{title.includes('Saved')
              ? 'Save a scheme from your recommendations to keep it close.'
              : 'Tell us a little about yourself to explore schemes that may fit.'}</p>
            <Link className="details-link" to={title.includes('Saved') ? '/recommendations' : '/discover'}>
              {title.includes('Saved') ? 'View recommendations' : 'Complete your profile'} <span>→</span>
            </Link>
          </div>
        ) : visibleItems.length === 0 ? (
          <div className="no-results">
            <span className="no-results-icon">⌕</span>
            <h3>No schemes in this category.</h3>
            <p>Try another category to explore your options.</p>
          </div>
        ) : (
          <div className="recommendation-list">
            {visibleItems.map((item, index) => (
              <SchemeCard
                key={item.scheme.scheme_id}
                recommendation={item}
                index={index}
                isSaved={savedIds.includes(item.scheme.scheme_id)}
                onToggleSaved={toggleSaved}
              />
            ))}
          </div>
        )}

        {items.length > 0 && (
          <div className="disclaimer">
            <span>!</span>
            <p>{disclaimer} Match scores indicate text relevance only; they are not the probability of eligibility or approval.{excludedCount > 0 && ` ${excludedCount} scheme${excludedCount === 1 ? '' : 's'} did not match a known rule.`}</p>
          </div>
        )}
      </section>
      <PageFooter />
    </div>
  )
}
