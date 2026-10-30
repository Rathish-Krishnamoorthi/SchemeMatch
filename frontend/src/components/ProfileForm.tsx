import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { initialProfile, states, toProfileRequest } from '../data/profile'
import { useAppContext } from '../hooks/useAppContext'
import type { ProfileFormValues, RecommendationResponse } from '../types'

export function ProfileForm() {
  const navigate = useNavigate()
  const { setRecommendations, setDisclaimer, setExcludedCount } = useAppContext()
  const [form, setForm] = useState<ProfileFormValues>(initialProfile)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  function updateField(key: keyof ProfileFormValues, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
    setErrors((current) => ({ ...current, [key]: '' }))
  }

  function validateForm() {
    const nextErrors: Record<string, string> = {}
    if (!form.age) nextErrors.age = 'Add your age to continue.'
    else if (!Number.isInteger(Number(form.age)) || Number(form.age) < 0 || Number(form.age) > 120) {
      nextErrors.age = 'Enter an age from 0 to 120.'
    }
    if (!form.state) nextErrors.state = 'Choose your state or union territory.'
    if (form.annual_income && (!Number.isFinite(Number(form.annual_income)) || Number(form.annual_income) < 0)) {
      nextErrors.annual_income = 'Income must be zero or more.'
    }
    if (!form.need.trim()) nextErrors.need = 'Tell us what kind of support you need.'
    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!validateForm()) return

    setLoading(true)
    setErrorMessage('')
    try {
      const response = await fetch('/api/recommendations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: toProfileRequest(form), limit: 5 }),
      })
      if (!response.ok) {
        const detail = await response.text()
        throw new Error(detail || `Request failed (${response.status})`)
      }
      const result = await response.json() as RecommendationResponse
      setRecommendations(result.recommendations)
      setDisclaimer(result.disclaimer)
      setExcludedCount(result.excluded_count)
      navigate('/recommendations')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Unable to load recommendations.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="form-card" aria-labelledby="profile-title">
      <div className="card-heading">
        <div className="step-number">01</div>
        <div>
          <h2 id="profile-title">Your profile</h2>
          <p>A few details help us find a closer match.</p>
        </div>
      </div>
      <form onSubmit={submitProfile} noValidate>
        <div className="field-grid">
          <label className="field">
            <span>Age <b>*</b></span>
            <input type="number" min="0" max="120" placeholder="e.g. 24" value={form.age} onChange={(event) => updateField('age', event.target.value)} aria-invalid={Boolean(errors.age)} />
            {errors.age && <small className="field-error">{errors.age}</small>}
          </label>
          <label className="field">
            <span>State / UT <b>*</b></span>
            <select value={form.state} onChange={(event) => updateField('state', event.target.value)} aria-invalid={Boolean(errors.state)}>
              <option value="">Select your state</option>
              {states.map((state) => <option key={state}>{state}</option>)}
            </select>
            {errors.state && <small className="field-error">{errors.state}</small>}
          </label>
          <label className="field">
            <span>District</span>
            <input type="text" placeholder="Your district" value={form.district} onChange={(event) => updateField('district', event.target.value)} />
          </label>
          <label className="field">
            <span>Annual family income <i>₹</i></span>
            <input type="number" min="0" placeholder="Optional" value={form.annual_income} onChange={(event) => updateField('annual_income', event.target.value)} aria-invalid={Boolean(errors.annual_income)} />
            {errors.annual_income && <small className="field-error">{errors.annual_income}</small>}
          </label>
          <label className="field">
            <span>Occupation</span>
            <select value={form.occupation} onChange={(event) => updateField('occupation', event.target.value)}>
              <option value="">Choose an occupation</option>
              {['Student', 'Farmer', 'Self-employed', 'Salaried', 'Artisan / craftsperson', 'Homemaker', 'Unemployed', 'Other'].map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Education level</span>
            <select value={form.education_level} onChange={(event) => updateField('education_level', event.target.value)}>
              <option value="">Choose education level</option>
              {['School', 'Higher secondary', 'Undergraduate', 'Postgraduate', 'Vocational / ITI', 'Other'].map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
        </div>
        <div className="optional-divider"><span>Only if relevant to you</span></div>
        <div className="field-grid compact-grid">
          <label className="field">
            <span>Are you currently a student?</span>
            <select value={form.student_status} onChange={(event) => updateField('student_status', event.target.value)}>
              <option value="">Prefer not to say</option><option value="yes">Yes</option><option value="no">No</option>
            </select>
          </label>
          <label className="field">
            <span>Do you work in farming?</span>
            <select value={form.farmer_status} onChange={(event) => updateField('farmer_status', event.target.value)}>
              <option value="">Prefer not to say</option><option value="yes">Yes</option><option value="no">No</option>
            </select>
          </label>
        </div>
        <label className="field need-field">
          <span>What kind of support are you looking for? <b>*</b></span>
          <textarea rows={3} maxLength={1000} placeholder="For example: I’m a college student looking for help with education costs." value={form.need} onChange={(event) => updateField('need', event.target.value)} aria-invalid={Boolean(errors.need)} />
          <div className="textarea-meta">
            {errors.need ? <small className="field-error">{errors.need}</small> : <small>A sentence or two is plenty.</small>}
            <small>{form.need.length}/1000</small>
          </div>
        </label>
        <div className="privacy-note"><span>⌑</span> Your profile is only used to find relevant schemes in this session.</div>
        <button className="submit-button" type="submit" disabled={loading}>
          {loading ? 'Finding your matches…' : 'Find my schemes'} <span>→</span>
        </button>
        {errorMessage && (
          <div className="error-banner" role="alert">
            <strong>Couldn’t load recommendations.</strong>
            <span>{errorMessage.includes('Failed to fetch') ? 'Start the local API and try again.' : errorMessage}</span>
          </div>
        )}
      </form>
    </section>
  )
}
