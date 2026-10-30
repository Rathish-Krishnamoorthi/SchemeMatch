import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { initialProfile, states } from '../data/profile'
import { useAppContext } from '../hooks/useAppContext'
import type { UserDemographicProfile } from '../types'

// ── Progressive helpers ───────────────────────────────────────────────────────

const isStudent = (f: UserDemographicProfile) => f.occupation === 'Student'
const isFarmer = (f: UserDemographicProfile) => f.occupation === 'Farmer'
const isEmployed = (f: UserDemographicProfile) =>
  f.occupation === 'Salaried' || f.occupation === 'Self-employed'
const hasFamily = (f: UserDemographicProfile) =>
  ['Married', 'Widowed', 'Divorced', 'Separated'].includes(f.marital_status)
const hasDisability = (f: UserDemographicProfile) => f.disability_status === 'yes'

// ── Steps ─────────────────────────────────────────────────────────────────────

const STEPS = ['who', 'work', 'family', 'need'] as const
type Step = typeof STEPS[number]

const STEP_META: Record<Step, { label: string; hint: string }> = {
  who:    { label: 'About you',       hint: 'Age, location, and how you identify.' },
  work:   { label: 'Education & work', hint: 'What you do and your financial situation.' },
  family: { label: 'Family & health', hint: 'Household size and any additional context.' },
  need:   { label: 'Your need',       hint: 'What kind of support are you looking for?' },
}

// ── Component ─────────────────────────────────────────────────────────────────

export function OnboardingPage() {
  const navigate = useNavigate()
  const { currentUser, token, saveUserProfile } = useAppContext()
  const [step, setStep] = useState<Step>('who')
  const [form, setForm] = useState<UserDemographicProfile>(initialProfile)
  const [errors, setErrors] = useState<Partial<Record<keyof UserDemographicProfile, string>>>({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  const stepIndex = STEPS.indexOf(step)

  function update(key: keyof UserDemographicProfile, value: string) {
    setForm((f) => {
      const next = { ...f, [key]: value }
      // When occupation changes, clear derived sub-fields
      if (key === 'occupation') {
        next.student_status = ''
        next.institution_type = ''
        next.farmer_status = ''
        next.land_holding_acres = ''
        next.profession = ''
        next.employment_status = ''
      }
      // Clear disability sub-field when toggled off
      if (key === 'disability_status' && value !== 'yes') next.disability_type = ''
      // Clear dependants when marital status is single
      if (key === 'marital_status' && !hasFamily({ ...f, marital_status: value }))
        next.dependants = ''
      return next
    })
    setErrors((e) => ({ ...e, [key]: '' }))
  }

  function validateStep(s: Step): boolean {
    const next: Partial<Record<keyof UserDemographicProfile, string>> = {}
    if (s === 'who') {
      if (!form.age) next.age = 'Please enter your age.'
      else if (!Number.isInteger(Number(form.age)) || Number(form.age) < 0 || Number(form.age) > 120)
        next.age = 'Enter an age from 0 to 120.'
      if (!form.state) next.state = 'Please choose your state.'
    }
    if (s === 'need') {
      if (!form.need.trim()) next.need = 'Tell us what kind of support you need.'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  function next() {
    if (!validateStep(step)) return
    const idx = STEPS.indexOf(step)
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1])
  }

  function back() {
    const idx = STEPS.indexOf(step)
    if (idx > 0) setStep(STEPS[idx - 1])
  }

  async function finish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!validateStep(step)) return
    setSaving(true)
    setSaveError('')
    try {
      await saveUserProfile(form, token ?? undefined)
      navigate('/discover')
    } catch {
      setSaveError('Something went wrong saving your profile. You can update it later in Profile.')
    } finally {
      setSaving(false)
    }
  }

  const isLastStep = step === STEPS[STEPS.length - 1]
  const nextStepLabel = !isLastStep ? STEP_META[STEPS[stepIndex + 1]].label : ''

  return (
    <div className="onboarding-page">
      <div className="onboarding-shell">

        {/* Header */}
        <header className="onboarding-header">
          <div className="onboarding-brand">
            <span className="brand-mark">s</span>
            <span>scheme<span className="brand-light">match</span></span>
          </div>
          <button className="onboarding-skip" type="button" onClick={() => navigate('/discover')}>
            Skip for now
          </button>
        </header>

        {/* Step indicators */}
        <nav className="onboarding-steps-nav" aria-label="Onboarding progress">
          {STEPS.map((s, i) => (
            <div
              key={s}
              className={`onboarding-step-pill ${i < stepIndex ? 'done' : i === stepIndex ? 'active' : ''}`}
            >
              <span className="step-pill-dot" aria-hidden="true" />
              <span className="step-pill-label">{STEP_META[s].label}</span>
            </div>
          ))}
        </nav>

        {/* Card */}
        <div className="onboarding-card">
          <div className="onboarding-card-intro">
            <p className="onboarding-card-eyebrow">Step {stepIndex + 1} of {STEPS.length}</p>
            <h1 className="onboarding-card-title">
              {step === 'who' && (
                <>Welcome{currentUser?.name ? `, ${currentUser.name.split(' ')[0]}` : ''}! ✳</>
              )}
              {step === 'work' && 'Education & work'}
              {step === 'family' && 'Family & health'}
              {step === 'need' && 'What are you looking for?'}
            </h1>
            <p className="onboarding-card-hint">{STEP_META[step].hint}</p>
          </div>

          <form
            className="onboarding-form"
            onSubmit={isLastStep ? finish : (e) => { e.preventDefault(); next() }}
            noValidate
          >

            {/* ── STEP 1: Who ─────────────────────────────────────────── */}
            {step === 'who' && (
              <>
                <div className="field-grid">
                  <label className="field">
                    <span>Age <b aria-hidden="true">*</b></span>
                    <input type="number" min="0" max="120" placeholder="e.g. 21"
                      value={form.age} onChange={(e) => update('age', e.target.value)}
                      aria-invalid={Boolean(errors.age)} aria-required="true" />
                    {errors.age && <small className="field-error" role="alert">{errors.age}</small>}
                  </label>
                  <label className="field">
                    <span>Gender</span>
                    <select value={form.gender} onChange={(e) => update('gender', e.target.value)}>
                      <option value="">Prefer not to say</option>
                      <option>Male</option><option>Female</option><option>Other</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>Social category</span>
                    <select value={form.category} onChange={(e) => update('category', e.target.value)}>
                      <option value="">Prefer not to say</option>
                      {['General', 'OBC', 'SC', 'ST', 'EWS', 'Other'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>
                </div>
                <div className="onboarding-divider"><span>Location</span></div>
                <div className="field-grid">
                  <label className="field">
                    <span>State / UT <b aria-hidden="true">*</b></span>
                    <select value={form.state} onChange={(e) => update('state', e.target.value)}
                      aria-invalid={Boolean(errors.state)} aria-required="true">
                      <option value="">Select your state</option>
                      {states.map((s) => <option key={s}>{s}</option>)}
                    </select>
                    {errors.state && <small className="field-error" role="alert">{errors.state}</small>}
                  </label>
                  <label className="field">
                    <span>District <span className="field-optional">(optional)</span></span>
                    <input type="text" placeholder="e.g. Coimbatore"
                      value={form.district} onChange={(e) => update('district', e.target.value)} />
                  </label>
                </div>
              </>
            )}

            {/* ── STEP 2: Work ─────────────────────────────────────────── */}
            {step === 'work' && (
              <>
                <div className="field-grid">
                  <label className="field">
                    <span>Occupation</span>
                    <select value={form.occupation} onChange={(e) => update('occupation', e.target.value)}>
                      <option value="">Choose an occupation</option>
                      {['Student', 'Farmer', 'Salaried', 'Self-employed', 'Artisan / craftsperson', 'Homemaker', 'Unemployed', 'Retired', 'Other'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>

                  {/* Salaried / Self-employed → profession sub-field */}
                  {isEmployed(form) && (
                    <label className="field field-reveal">
                      <span>{form.occupation === 'Salaried' ? 'What sector do you work in?' : 'What type of business?'}</span>
                      <select value={form.profession} onChange={(e) => update('profession', e.target.value)}>
                        <option value="">Choose one</option>
                        {form.occupation === 'Salaried'
                          ? ['Government / PSU', 'Private sector', 'Defence / Paramilitary', 'Teaching / Academia', 'Healthcare', 'IT / Technology', 'Other'].map((o) => <option key={o}>{o}</option>)
                          : ['Retail / Trade', 'Services', 'Manufacturing / Craft', 'Agriculture-related', 'Transport', 'Construction', 'Other'].map((o) => <option key={o}>{o}</option>)}
                      </select>
                    </label>
                  )}

                  {/* Student → institution type */}
                  {isStudent(form) && (
                    <label className="field field-reveal">
                      <span>Type of institution</span>
                      <select value={form.institution_type} onChange={(e) => update('institution_type', e.target.value)}>
                        <option value="">Choose one</option>
                        {['Government school', 'Private school', 'Government college / university', 'Private college / university', 'ITI / Polytechnic', 'Other'].map((o) => <option key={o}>{o}</option>)}
                      </select>
                    </label>
                  )}

                  {/* Farmer → land holding */}
                  {isFarmer(form) && (
                    <label className="field field-reveal">
                      <span>Land holding <span className="field-unit">acres</span></span>
                      <input type="number" min="0" step="0.1" placeholder="e.g. 2.5"
                        value={form.land_holding_acres} onChange={(e) => update('land_holding_acres', e.target.value)} />
                    </label>
                  )}

                  {/* Show employment status only for non-obvious occupations */}
                  {!isStudent(form) && !isFarmer(form) && form.occupation !== 'Homemaker' && form.occupation !== 'Unemployed' && form.occupation !== 'Retired' && form.occupation !== '' && (
                    <label className="field field-reveal">
                      <span>Employment type</span>
                      <select value={form.employment_status} onChange={(e) => update('employment_status', e.target.value)}>
                        <option value="">Choose type</option>
                        {['Full-time', 'Part-time', 'Contract / Temporary', 'Casual / Daily wage', 'Self-employed'].map((o) => <option key={o}>{o}</option>)}
                      </select>
                    </label>
                  )}

                  <label className="field">
                    <span>Education level</span>
                    <select value={form.education_level} onChange={(e) => update('education_level', e.target.value)}>
                      <option value="">Choose level</option>
                      {['No formal education', 'Primary school', 'Secondary school', 'Higher secondary', 'Undergraduate', 'Postgraduate', 'Vocational / ITI', 'Other'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>
                </div>

                <div className="onboarding-divider"><span>Financial</span></div>
                <div className="field-grid">
                  <label className="field">
                    <span>Annual family income <span className="field-unit">₹</span> <span className="field-optional">(optional)</span></span>
                    <input type="number" min="0" placeholder="e.g. 200000"
                      value={form.annual_income} onChange={(e) => update('annual_income', e.target.value)} />
                    <small className="field-hint">Household total — used in income-based scheme eligibility.</small>
                  </label>
                </div>
              </>
            )}

            {/* ── STEP 3: Family & health ──────────────────────────────── */}
            {step === 'family' && (
              <>
                <div className="field-grid">
                  <label className="field">
                    <span>Marital status</span>
                    <select value={form.marital_status} onChange={(e) => update('marital_status', e.target.value)}>
                      <option value="">Prefer not to say</option>
                      {['Single', 'Married', 'Widowed', 'Divorced', 'Separated'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>

                  {/* Married / Widowed / Divorced / Separated → dependants */}
                  {hasFamily(form) && (
                    <label className="field field-reveal">
                      <span>Number of dependants <span className="field-optional">(children + elderly)</span></span>
                      <input type="number" min="0" max="20" placeholder="e.g. 2"
                        value={form.dependants} onChange={(e) => update('dependants', e.target.value)} />
                      <small className="field-hint">Counts children and other family members who depend on you financially.</small>
                    </label>
                  )}

                  <label className="field">
                    <span>Do you have a disability?</span>
                    <select value={form.disability_status} onChange={(e) => update('disability_status', e.target.value)}>
                      <option value="">Prefer not to say</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </label>

                  {/* Disability → type */}
                  {hasDisability(form) && (
                    <label className="field field-reveal">
                      <span>Type of disability <span className="field-optional">(optional)</span></span>
                      <select value={form.disability_type} onChange={(e) => update('disability_type', e.target.value)}>
                        <option value="">Prefer not to say</option>
                        {['Locomotor', 'Visual', 'Hearing / Speech', 'Intellectual', 'Mental illness', 'Multiple disabilities', 'Other'].map((o) => <option key={o}>{o}</option>)}
                      </select>
                    </label>
                  )}
                </div>
              </>
            )}

            {/* ── STEP 4: Need ─────────────────────────────────────────── */}
            {step === 'need' && (
              <label className="field need-field">
                <span>What kind of support are you looking for? <b aria-hidden="true">*</b></span>
                <textarea
                  rows={4} maxLength={1000}
                  placeholder="For example: I&#39;m a college student looking for help with education costs and a scholarship for my second year."
                  value={form.need} onChange={(e) => update('need', e.target.value)}
                  aria-invalid={Boolean(errors.need)} aria-required="true"
                />
                <div className="textarea-meta">
                  {errors.need
                    ? <small className="field-error" role="alert">{errors.need}</small>
                    : <small>A sentence or two is enough — be specific about your goal.</small>}
                  <small>{form.need.length}/1000</small>
                </div>
              </label>
            )}

            {saveError && <p className="auth-message" role="alert">{saveError}</p>}

            {/* Navigation */}
            <div className="onboarding-nav">
              {stepIndex > 0 && (
                <button type="button" className="onboarding-back" onClick={back}>
                  ← Back
                </button>
              )}
              <button type="submit" className="submit-button onboarding-next" disabled={saving}>
                {isLastStep
                  ? (saving ? 'Saving\u2026' : 'Find my schemes \u2192')
                  : `Next: ${nextStepLabel} \u2192`}
              </button>
            </div>

            <p className="onboarding-privacy">
              <span aria-hidden="true">⌑</span> Your details are only used to find relevant schemes.
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}
