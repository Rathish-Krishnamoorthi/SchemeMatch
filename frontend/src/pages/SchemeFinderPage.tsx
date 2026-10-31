import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Pagination } from '../components/Pagination'
import { categoryMarks } from '../data/profile'
import { useAppContext } from '../hooks/useAppContext'
import { usePagination } from '../hooks/usePagination'
import type { FinderResponse, FinderResult, QuestionnaireAnswers, ScanSchemeResult } from '../types'

// ── Category-specific questions ───────────────────────────────────────────────

const CATEGORIES = [
  { value: 'Education', label: '▤ Education', desc: 'Scholarships, fellowships, tuition support' },
  { value: 'Agriculture', label: '✳ Agriculture', desc: 'Crop insurance, loans, subsidies' },
  { value: 'Skills & Business', label: '↗ Skills & Business', desc: 'Training, loans, entrepreneurship' },
  { value: 'Employment', label: '◎ Employment', desc: 'Job placement, apprenticeships, work training' },
  { value: 'Housing', label: '⌂ Housing', desc: 'Affordable housing, construction loans' },
  { value: 'Health', label: '⚕ Health', desc: 'Medical insurance, disability support' },
  { value: 'Social Welfare', label: '✦ Social Welfare', desc: 'Pensions, food security, women\'s welfare' },
  { value: 'All', label: '⊙ All categories', desc: 'Search across everything' },
]

const CATEGORY_QUESTIONS: Record<string, Array<{ id: string; label: string; type: 'text' | 'select'; options?: string[] }>> = {
  Education: [
    { id: 'level', label: 'What level of education are you seeking support for?', type: 'select', options: ['School (Classes 1–8)', 'Secondary (Classes 9–10)', 'Higher secondary (Classes 11–12)', 'Undergraduate', 'Postgraduate', 'PhD / Research', 'Vocational / ITI'] },
    { id: 'institution', label: 'Type of institution', type: 'select', options: ['Government', 'Private', 'Any'] },
    { id: 'benefit_type', label: 'What type of support do you need?', type: 'select', options: ['Scholarship / stipend', 'Tuition fee waiver', 'Hostel / accommodation', 'Book / material allowance', 'Coaching support', 'Research fellowship', 'Any'] },
  ],
  Agriculture: [
    { id: 'farm_type', label: 'What type of farming do you practise?', type: 'select', options: ['Crop farming', 'Horticulture', 'Dairy / Animal husbandry', 'Fisheries / Aquaculture', 'Organic farming', 'Sericulture', 'Other'] },
    { id: 'need_type', label: 'What do you need support for?', type: 'select', options: ['Crop insurance', 'Input subsidy (seeds, fertiliser)', 'Credit / loans', 'Equipment / machinery', 'Irrigation', 'Storage / market linkage', 'Pension / income support'] },
  ],
  'Skills & Business': [
    { id: 'stage', label: 'Which stage is your business or career at?', type: 'select', options: ['Starting a new venture', 'Expanding an existing business', 'Upskilling for employment', 'Looking for employment after training', 'Exporting / scaling up'] },
    { id: 'sector', label: 'Which sector?', type: 'select', options: ['Manufacturing / Craft', 'Services', 'Technology / IT', 'Agriculture-related', 'Textile / Handloom', 'Food processing', 'Other'] },
    { id: 'funding', label: 'What type of support do you need?', type: 'select', options: ['Loan / credit', 'Grant / subsidy', 'Skill training', 'Certification', 'Market access', 'Any'] },
  ],
  Employment: [
    { id: 'employment_goal', label: 'What kind of employment support do you need?', type: 'select', options: ['Job placement', 'Apprenticeship', 'Skill training', 'Wage support', 'Self-employment support', 'Any'] },
    { id: 'employment_sector', label: 'Which work area interests you?', type: 'select', options: ['Agriculture', 'Manufacturing / Craft', 'Services', 'Technology / IT', 'Healthcare', 'Any'] },
  ],
  Housing: [
    { id: 'area_type', label: 'Where are you located?', type: 'select', options: ['Urban', 'Rural', 'Semi-urban'] },
    { id: 'housing_need', label: 'What is your housing need?', type: 'select', options: ['Build a new house', 'Purchase a house', 'Repair / renovation', 'Rental support', 'Hostel / shelter'] },
    { id: 'ownership', label: 'Do you currently own any property?', type: 'select', options: ['No', 'Yes, but it needs repair', 'Yes'] },
  ],
  Health: [
    { id: 'health_need', label: 'What health support do you need?', type: 'select', options: ['Health insurance', 'Disability benefits', 'Mental health support', 'Maternal / child health', 'Senior citizen care', 'Nutrition support', 'Any'] },
  ],
  'Social Welfare': [
    { id: 'welfare_need', label: 'What type of welfare support do you need?', type: 'select', options: ['Old-age pension', 'Widow / survivor benefit', 'Food security / ration', 'Financial assistance', 'Women\'s empowerment', 'Child welfare', 'Any'] },
  ],
}

// ── Result card ───────────────────────────────────────────────────────────────

function FinderCard({ item, rank, isSaved, onToggle }: {
  item: FinderResult
  rank: number
  isSaved: boolean
  onToggle: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const { scheme, eligibility } = item
  const eligible = eligibility.status === 'LIKELY_ELIGIBLE'
  const verify = eligibility.status === 'NEEDS_VERIFICATION'

  return (
    <article className="finder-card">
      <div className="finder-card-top">
        <span className="finder-rank">#{rank}</span>
        <span className="dc-category">{categoryMarks[scheme.category] ?? '✳'} {scheme.category}</span>
        <span className={`trust-score-chip ${item.trust.level}`}>Trust {item.trust.score}/100</span>
        <span className={`dc-status ${eligible ? 'eligible' : verify ? 'verify' : 'ineligible'}`}>
          <span className="dc-status-dot" />
          {eligible ? 'Likely eligible' : verify ? 'Verify eligibility' : 'Not eligible'}
        </span>
        <button
          className={`dc-save ${isSaved ? 'saved' : ''}`}
          type="button"
          aria-label={isSaved ? 'Remove' : 'Save'}
          onClick={() => onToggle(scheme.scheme_id)}
        >
          {isSaved ? '♥' : '♡'}
        </button>
      </div>

      <h3 className="finder-card-name">{scheme.name}</h3>
      <p className="finder-card-desc">{scheme.description}</p>

      <div className="finder-key-details">
        <div>
          <h4>Benefits</h4>
          <p>{scheme.benefits || 'Check the official source for benefit details.'}</p>
        </div>
        <div>
          <h4>Documents</h4>
          <p>
            {scheme.documents.length
              ? `${scheme.documents.slice(0, 2).join(', ')}${scheme.documents.length > 2 ? `, +${scheme.documents.length - 2} more` : ''}`
              : 'Not listed; confirm with the official authority.'}
          </p>
        </div>
        <div>
          <h4>How to apply</h4>
          <p>{scheme.application_process[0] ?? 'Check the official source for application instructions.'}</p>
        </div>
      </div>

      {/* Score bars */}
      <div className="finder-scores">
        <div className="finder-score-row">
          <span>Relevance</span>
          <div className="finder-score-bar">
            <div className="finder-score-fill" style={{ width: `${item.weighted_score}%` }} />
          </div>
          <span className="finder-score-num">{item.weighted_score}</span>
        </div>
        <div className="finder-score-row finder-score-sub">
          <span>Semantic</span>
          <div className="finder-score-bar small">
            <div className="finder-score-fill semantic" style={{ width: `${item.semantic_score}%` }} />
          </div>
          <span className="finder-score-num small">{item.semantic_score}</span>
        </div>
        <div className="finder-score-row finder-score-sub">
          <span>Category</span>
          <div className="finder-score-bar small">
            <div className="finder-score-fill" style={{ width: `${item.category_score}%` }} />
          </div>
          <span className="finder-score-num small">{item.category_score}</span>
        </div>
        <div className="finder-score-row finder-score-sub">
          <span>Benefits</span>
          <div className="finder-score-bar small">
            <div className="finder-score-fill" style={{ width: `${item.benefit_score}%` }} />
          </div>
          <span className="finder-score-num small">{item.benefit_score}</span>
        </div>
      </div>

      <section className="finder-reasoning" aria-label="Grounded scheme reasoning">
        <h4>LLM-generated reason · verified scheme evidence</h4>
        <p className="finder-explanation">{item.explanation}</p>
        <ul className="finder-evidence">
          {item.evidence.map((evidence, index) => (
            <li key={`${evidence.field}-${index}`}>
              <strong>{evidence.field.replaceAll('_', ' ')}</strong>
              <q>{evidence.quote}</q>
            </li>
          ))}
        </ul>
      </section>

      <button
        className="scan-card-toggle"
        type="button"
        onClick={() => setExpanded(e => !e)}
      >
        {expanded ? 'Hide full details ↑' : 'Show full details ↓'}
      </button>

      {expanded && (
        <div className="scan-card-details">
          {scheme.documents.length > 0 && (
            <div className="scan-detail-section">
              <h4>All documents required</h4>
              <ul>{scheme.documents.map(d => <li key={d}>{d}</li>)}</ul>
            </div>
          )}
          {scheme.application_process.length > 0 && (
            <div className="scan-detail-section">
              <h4>Full application process</h4>
              <ol>{scheme.application_process.map(s => <li key={s}>{s}</li>)}</ol>
            </div>
          )}
          {eligibility.reasons.length > 0 && (
            <div className="scan-detail-section">
              <h4>Eligibility notes</h4>
              <ul>{eligibility.reasons.map(r => <li key={r}>{r}</li>)}</ul>
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

function UnknownFinderCard({ item }: { item: ScanSchemeResult }) {
  const [expanded, setExpanded] = useState(false)
  const { scheme, eligibility } = item
  return (
    <article className="scan-card">
      <div className="scan-card-top">
        <span className="dc-category">{categoryMarks[scheme.category] ?? '✳'} {scheme.category}</span>
        <span className="dc-status verify"><span className="dc-status-dot" />UNKNOWN — verify eligibility</span>
        {item.trust && <span className={`trust-score-chip ${item.trust.level}`}>Trust {item.trust.score}/100</span>}
      </div>
      <h3 className="scan-card-name">{scheme.name}</h3>
      <p className="scan-card-desc">{scheme.description}</p>
      <ul className="unknown-reasons">{eligibility.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
      <button className="scan-card-toggle" type="button" onClick={() => setExpanded((open) => !open)}>
        {expanded ? 'Hide details ↑' : 'Show details ↓'}
      </button>
      {expanded && (
        <div className="scan-card-details">
          <div className="scan-detail-section"><h4>Benefits</h4><p>{scheme.benefits}</p></div>
          <div className="scan-detail-section">
            <h4>Required documents</h4>
            {scheme.documents.length ? <ul>{scheme.documents.map((document) => <li key={document}>{document}</li>)}</ul> : <p>Not listed; confirm with the official authority.</p>}
          </div>
          <div className="scan-card-links">
            <a className="scan-official-btn" href={scheme.official_url} target="_blank" rel="noreferrer">Official source ↗</a>
            <Link className="scan-details-link" to={`/schemes/${scheme.scheme_id}`}>Full details →</Link>
          </div>
        </div>
      )}
    </article>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Step = 'category' | 'specifics' | 'objective' | 'results'

const INITIAL_ANSWERS: QuestionnaireAnswers = {
  category: '',
  objective: '',
  benefit_needs: '',
  location_preference: '',
  additional: {},
}

const INITIAL_WEIGHTS = { semantic: 60, category: 25, benefit: 15 }

export function SchemeFinderPage() {
  const { pathname } = useLocation()
  const { token, currentUser, userProfile, savedIds, toggleSaved } = useAppContext()
  const [step, setStep] = useState<Step>('category')
  const [answers, setAnswers] = useState<QuestionnaireAnswers>(INITIAL_ANSWERS)
  const [response, setResponse] = useState<FinderResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [weights, setWeights] = useState(INITIAL_WEIGHTS)
  const resultPagination = usePagination(response?.results ?? [])
  const unknownPagination = usePagination(response?.unknown ?? [])

  function updateAdditional(id: string, value: string) {
    setAnswers(a => ({ ...a, additional: { ...a.additional, [id]: value } }))
  }

  function updateWeight(key: keyof typeof INITIAL_WEIGHTS, value: number) {
    const otherKeys = (Object.keys(INITIAL_WEIGHTS) as Array<keyof typeof INITIAL_WEIGHTS>)
      .filter((weightKey) => weightKey !== key)
    setWeights((current) => {
      const previousOtherTotal = otherKeys.reduce((total, otherKey) => total + current[otherKey], 0)
      const remaining = 100 - value
      const next = { ...current, [key]: value }
      for (const otherKey of otherKeys) {
        next[otherKey] = previousOtherTotal
          ? remaining * current[otherKey] / previousOtherTotal
          : remaining / otherKeys.length
      }
      return next
    })
  }

  async function submit() {
    if (!token) return
    resultPagination.setPage(1)
    unknownPagination.setPage(1)
    setLoading(true)
    setError('')
    setStep('results')
    try {
      const res = await fetch('/api/users/me/scheme-finder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          questionnaire: answers,
          weights: {
            semantic: weights.semantic / 100,
            category: weights.category / 100,
            benefit: weights.benefit / 100,
          },
        }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({})) as { detail?: string }
        throw new Error(d.detail ?? `Error ${res.status}`)
      }
      setResponse(await res.json() as FinderResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setStep('objective')
    } finally {
      setLoading(false)
    }
  }

  function restart() {
    resultPagination.setPage(1)
    unknownPagination.setPage(1)
    setAnswers(INITIAL_ANSWERS)
    setWeights(INITIAL_WEIGHTS)
    setResponse(null)
    setError('')
    setStep('category')
  }

  // ── Auth gate ────────────────────────────────────────────────────────────
  if (!currentUser || !token) {
    return (
      <div className="page-wrap">
        <div className="no-results">
          <span className="no-results-icon">↗</span>
          <h3>Sign in to use the Scheme Finder</h3>
          <p>The finder combines your profile with your search to surface the most relevant schemes.</p>
          <Link className="details-link" to="/login">Sign in →</Link>
        </div>
      </div>
    )
  }

  const catQuestions = CATEGORY_QUESTIONS[answers.category] ?? []
  const isReasoningRoute = pathname === '/llm-reasoning'
  const progressSteps: Step[] = ['category', 'specifics', 'objective', 'results']
  const progressPct = ((progressSteps.indexOf(step) + 1) / progressSteps.length) * 100

  return (
    <div className="page-wrap finder-page">
      {/* Header */}
      <div className="scan-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> {isReasoningRoute ? 'LLM SCHEME REASONING' : 'REQUIRED SCHEME FINDER'}</div>
          <h1 className="scan-title">{isReasoningRoute ? 'Scheme reasoning, grounded in evidence' : 'Find the right scheme'}</h1>
          <p className="scan-subtitle">
            Eligibility rules are applied first. BGE-M3 ranks only eligible schemes; the configured LLM then explains each displayed result using quotes verified against scheme records.
          </p>
        </div>
        <a className="discover-refine-btn finder-provider-settings" href="/admin">
          Provider settings (admin) ↗
        </a>
        {step !== 'category' && step !== 'results' && (
          <button className="discover-refine-btn" type="button" onClick={restart}>Start over</button>
        )}
        {step === 'results' && (
          <button className="discover-refine-btn" type="button" onClick={restart}>New search</button>
        )}
      </div>

      {/* Progress */}
      {step !== 'results' && (
        <div className="finder-progress">
          <div className="onboarding-progress-track">
            <div className="onboarding-progress-bar" style={{ width: `${progressPct}%` }} />
          </div>
          <p className="finder-progress-label">
            {step === 'category' && 'Step 1 — Choose a category'}
            {step === 'specifics' && `Step 2 — Tell us more about ${answers.category || 'your need'}`}
            {step === 'objective' && 'Step 3 — Describe your goal'}
          </p>
        </div>
      )}

      {/* ── Step 1: Category ── */}
      {step === 'category' && (
        <div className="finder-step">
          <h2 className="finder-step-title">What type of scheme are you looking for?</h2>
          <div className="finder-category-grid">
            {CATEGORIES.map(cat => (
              <button
                key={cat.value}
                className={`finder-cat-card ${answers.category === cat.value ? 'active' : ''}`}
                type="button"
                onClick={() => {
                  setAnswers(a => ({ ...a, category: cat.value, additional: {} }))
                  setStep('specifics')
                }}
              >
                <span className="finder-cat-label">{cat.label}</span>
                <span className="finder-cat-desc">{cat.desc}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Step 2: Category-specific questions ── */}
      {step === 'specifics' && (
        <div className="finder-step">
          <h2 className="finder-step-title">
            A few more questions about {answers.category === 'All' ? 'your need' : answers.category.toLowerCase()}
          </h2>
          {catQuestions.length === 0 ? (
            <p className="scan-subtitle" style={{ marginBottom: 24 }}>No specific questions for this category. Continue to describe your goal.</p>
          ) : (
            <div className="finder-questions">
              {catQuestions.map(q => (
                <label key={q.id} className="finder-question">
                  <span>{q.label}</span>
                  {q.type === 'select' ? (
                    <select
                      value={answers.additional[q.id] ?? ''}
                      onChange={e => updateAdditional(q.id, e.target.value)}
                    >
                      <option value="">Choose one…</option>
                      {q.options!.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={answers.additional[q.id] ?? ''}
                      onChange={e => updateAdditional(q.id, e.target.value)}
                    />
                  )}
                </label>
              ))}
            </div>
          )}
          <div className="finder-nav">
            <button className="onboarding-back" type="button" onClick={() => setStep('category')}>← Back</button>
            <button className="submit-button finder-next" type="button" onClick={() => setStep('objective')}>
              Next →
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Objective + benefit needs ── */}
      {step === 'objective' && (
        <div className="finder-step">
          <h2 className="finder-step-title">Describe what you need</h2>
          <p className="finder-step-hint">
            The more specific you are, the better the match.
            {userProfile?.need && <> Your saved profile need: <em>"{userProfile.need}"</em></>}
          </p>

          <div className="finder-questions">
            <label className="finder-question">
              <span>What is your main goal or objective? <b>*</b></span>
              <textarea
                rows={3}
                maxLength={500}
                placeholder="e.g. I want to fund my undergraduate engineering degree at a government college."
                value={answers.objective}
                onChange={e => setAnswers(a => ({ ...a, objective: e.target.value }))}
              />
            </label>
            <label className="finder-question">
              <span>What type of benefit or support do you need?</span>
              <input
                type="text"
                placeholder="e.g. scholarship, stipend, loan waiver, free training"
                value={answers.benefit_needs}
                onChange={e => setAnswers(a => ({ ...a, benefit_needs: e.target.value }))}
              />
            </label>
            <label className="finder-question">
              <span>Any state or location preference?</span>
              <input
                type="text"
                placeholder="e.g. Tamil Nadu, or leave blank to search all states"
                value={answers.location_preference}
                onChange={e => setAnswers(a => ({ ...a, location_preference: e.target.value }))}
              />
            </label>
            <fieldset className="finder-weight-settings">
              <legend>Relevance scoring weights</legend>
              <p>Eligibility rules are applied first. These weights only rank schemes that pass every recorded rule.</p>
              {([
                ['semantic', 'Semantic similarity'],
                ['category', 'Category and objective'],
                ['benefit', 'Benefit relevance'],
              ] as const).map(([key, label]) => (
                <label className="finder-weight-control" key={key}>
                  <span>{label}<strong>{weights[key].toFixed(0)}%</strong></span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={weights[key]}
                    onChange={(event) => updateWeight(key, Number(event.target.value))}
                    aria-label={`${label} weight`}
                  />
                </label>
              ))}
            </fieldset>
          </div>

          {error && <div className="error-banner" role="alert"><strong>Error.</strong><span>{error}</span></div>}

          <div className="finder-nav">
            <button className="onboarding-back" type="button" onClick={() => setStep('specifics')}>← Back</button>
            <button
              className="submit-button finder-next"
              type="button"
              disabled={!answers.objective.trim() || loading}
              onClick={submit}
            >
              {loading ? 'Searching…' : 'Find schemes →'}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 4: Results ── */}
      {step === 'results' && (
        <div className="finder-results">
          {loading && (
            <div className="discover-skeleton">
              {[1, 2, 3, 4, 5].map(n => <div key={n} className="skeleton-card" />)}
            </div>
          )}

          {!loading && response && (
            <>
              <section className="finder-final-results" aria-labelledby="finder-final-results-title">
                <div>
                  <div className="eyebrow"><span className="eyebrow-line" /> FINAL SCHEME RESULTS</div>
                  <h2 id="finder-final-results-title">
                    {response.results.length
                      ? `Top scheme matches${answers.category && answers.category !== 'All' ? ` · ${answers.category}` : ''}`
                      : `No eligible matches${answers.category && answers.category !== 'All' ? ` · ${answers.category}` : ''}`}
                  </h2>
                </div>
                <p>Up to five schemes are filtered to your selected category, checked against your profile, and ranked by content relevance. Unknown eligibility stays separate.</p>
              </section>
              <div className="finder-results-meta">
                <div>
                  <span className="result-count">Top {response.results.length} scheme matches</span>
                  <span style={{ color: '#9aa09a', fontSize: 10, marginLeft: 10 }}>
                    from {response.total_candidates} candidates · {response.excluded_count} ruled out
                  </span>
                </div>
                <div className="finder-weights-note">
                  Scored: {Math.round(response.weights.semantic * 100)}% semantic · {Math.round(response.weights.category * 100)}% category/objective · {Math.round(response.weights.benefit * 100)}% benefits
                </div>
              </div>

              {response.results.length === 0 && response.unknown.length === 0 ? (
                <div className="no-results">
                  <span className="no-results-icon">⌕</span>
                  <h3>No matching schemes found.</h3>
                  <p>Try broadening your objective or choosing "All categories".</p>
                  <button className="details-link" type="button" onClick={restart}>Try again →</button>
                </div>
              ) : (
                <>
                  {response.results.length === 0 && (
                    <div className="scan-notice">
                      <span>i</span><p>No schemes with complete matching eligibility rules were found. Schemes with unknown eligibility are shown separately below.</p>
                    </div>
                  )}
                  {response.results.length > 0 && (
                  <div className="finder-list">
                    {resultPagination.items.map((item, i) => (
                      <FinderCard
                        key={item.scheme.scheme_id}
                        item={item}
                        rank={(resultPagination.page - 1) * resultPagination.pageSize + i + 1}
                        isSaved={savedIds.includes(item.scheme.scheme_id)}
                        onToggle={toggleSaved}
                      />
                    ))}
                  </div>
                  )}
                  <Pagination
                    page={resultPagination.page}
                    pageCount={resultPagination.pageCount}
                    pageSize={resultPagination.pageSize}
                    totalItems={resultPagination.totalItems}
                    onPageChange={resultPagination.setPage}
                  />
                  {response.unknown.length > 0 && (
                    <section className="finder-unknown-section">
                      <h2>Unknown eligibility <span>{response.unknown.length}</span></h2>
                      <p>These schemes are not ranked as eligible: at least one profile detail or authoritative rule is missing.</p>
                      <div className="finder-list">
                        {unknownPagination.items.map((item) => <UnknownFinderCard key={item.scheme.scheme_id} item={item} />)}
                      </div>
                      <Pagination
                        page={unknownPagination.page}
                        pageCount={unknownPagination.pageCount}
                        pageSize={unknownPagination.pageSize}
                        totalItems={unknownPagination.totalItems}
                        onPageChange={unknownPagination.setPage}
                      />
                    </section>
                  )}
                  <div className="disclaimer"><span>!</span><p>{response.disclaimer}</p></div>
                </>
              )}
            </>
          )}

          {!loading && error && (
            <div className="error-banner" role="alert">
              <strong>Search failed.</strong>
              <span>{error}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
