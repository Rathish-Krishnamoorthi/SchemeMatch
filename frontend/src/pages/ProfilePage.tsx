import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { initialProfile, states } from '../data/profile'
import { useAppContext } from '../hooks/useAppContext'
import type { UserDemographicProfile } from '../types'

// ── Progressive helpers (same logic as OnboardingPage) ───────────────────────
const isStudent = (f: UserDemographicProfile) => f.occupation === 'Student'
const isFarmer = (f: UserDemographicProfile) => f.occupation === 'Farmer'
const isEmployed = (f: UserDemographicProfile) =>
  f.occupation === 'Salaried' || f.occupation === 'Self-employed'
const hasFamily = (f: UserDemographicProfile) =>
  ['Married', 'Widowed', 'Divorced', 'Separated'].includes(f.marital_status)
const hasDisability = (f: UserDemographicProfile) => f.disability_status === 'yes'

const animalAvatars = [
  { emoji: '🦊', label: 'Fox' },
  { emoji: '🐼', label: 'Panda' },
  { emoji: '🐱', label: 'Cat' },
  { emoji: '🐻', label: 'Bear' },
  { emoji: '🐰', label: 'Rabbit' },
  { emoji: '🦁', label: 'Lion' },
  { emoji: '🐸', label: 'Frog' },
  { emoji: '🐨', label: 'Koala' },
]

export function ProfilePage() {
  const { profileSettings, saveProfileSettings, currentUser, userProfile, saveUserProfile, loadUserProfile, token } = useAppContext()
  const [avatarMessage, setAvatarMessage] = useState('')

  const [form, setForm] = useState<UserDemographicProfile>(userProfile ?? initialProfile)
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof UserDemographicProfile, string>>>({})
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  useEffect(() => {
    if (currentUser && token && !userProfile) {
      void loadUserProfile(token).then((loaded) => { if (loaded) setForm(loaded) })
    }
  }, [currentUser, token, userProfile, loadUserProfile])

  useEffect(() => {
    if (userProfile) setForm(userProfile)
  }, [userProfile])

  function updateAvatar(name: string, animal: string, image: string) {
    const saved = saveProfileSettings({ name, animal, image })
    setAvatarMessage(saved ? '' : 'Your changes are shown here, but could not be saved on this device.')
  }

  function handleAvatarUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0]
    event.currentTarget.value = ''
    if (!file) return
    if (!file.type.startsWith('image/')) { setAvatarMessage('Choose an image file.'); return }
    if (file.size > 2 * 1024 * 1024) { setAvatarMessage('Choose an image smaller than 2 MB.'); return }
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result !== 'string') { setAvatarMessage('Could not load that picture.'); return }
      updateAvatar(profileSettings.name, profileSettings.animal, reader.result)
    }
    reader.onerror = () => setAvatarMessage('Could not read that picture.')
    reader.readAsDataURL(file)
  }

  function updateField(key: keyof UserDemographicProfile, value: string) {
    setForm((f) => {
      const next = { ...f, [key]: value }
      if (key === 'occupation') {
        next.student_status = ''
        next.institution_type = ''
        next.farmer_status = ''
        next.land_holding_acres = ''
        next.profession = ''
        next.employment_status = ''
      }
      if (key === 'disability_status' && value !== 'yes') next.disability_type = ''
      if (key === 'marital_status' && !hasFamily({ ...f, marital_status: value })) next.dependants = ''
      return next
    })
    setFormErrors((e) => ({ ...e, [key]: '' }))
  }

  function validate(): boolean {
    const next: Partial<Record<keyof UserDemographicProfile, string>> = {}
    if (form.age && (!Number.isInteger(Number(form.age)) || Number(form.age) < 0 || Number(form.age) > 120))
      next.age = 'Enter an age from 0 to 120.'
    if (form.annual_income && (!Number.isFinite(Number(form.annual_income)) || Number(form.annual_income) < 0))
      next.annual_income = 'Income must be zero or more.'
    setFormErrors(next)
    return Object.keys(next).length === 0
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!validate()) return
    setSaving(true)
    setSaveMessage('')
    try {
      await saveUserProfile(form, token ?? undefined)
      setSaveMessage('Saved.')
      setTimeout(() => setSaveMessage(''), 3000)
    } catch {
      setSaveMessage('Could not save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-wrap">
      <section className="profile-page" aria-labelledby="account-title">
        <Link className="profile-back" to="/discover">← Back to schemes</Link>
        <div className="profile-page-heading">
          <div className="eyebrow"><span className="eyebrow-line" /> YOUR SPACE</div>
          <h1 id="account-title">Your profile.</h1>
          <p>Keep your details up to date so your recommendations stay relevant.</p>
        </div>

        <div className="profile-settings-grid">
          {/* Avatar */}
          <section className="profile-card" aria-labelledby="picture-title">
            <div className="profile-card-heading">
              <span className="profile-card-icon">✿</span>
              <div><h2 id="picture-title">Your picture</h2><p>Upload a photo or pick an avatar.</p></div>
            </div>
            <div className="profile-avatar-preview">
              {profileSettings.image
                ? <img src={profileSettings.image} alt="Your profile picture" />
                : <span aria-label={`${animalAvatars.find(({ emoji }) => emoji === profileSettings.animal)?.label ?? 'Animal'} cartoon`} role="img">{profileSettings.animal}</span>}
            </div>
            <label className="upload-picture">
              <span>↑</span> Upload a picture
              <input type="file" accept="image/*" onChange={handleAvatarUpload} />
            </label>
            <p className="upload-hint">Image files · up to 2 MB</p>
            <div className="animal-picker">
              <h3>Or choose an animal</h3>
              <div className="animal-options">
                {animalAvatars.map(({ emoji, label }) => (
                  <button key={emoji}
                    className={`animal-option ${!profileSettings.image && profileSettings.animal === emoji ? 'chosen' : ''}`}
                    type="button" aria-label={`Choose ${label} cartoon`}
                    aria-pressed={!profileSettings.image && profileSettings.animal === emoji}
                    onClick={() => updateAvatar(profileSettings.name, emoji, '')}
                  >{emoji}</button>
                ))}
              </div>
            </div>
            {avatarMessage && <p className="profile-message" role="status">{avatarMessage}</p>}
          </section>

          {/* Account name */}
          <section className="profile-card profile-details-card" aria-labelledby="details-title">
            <div className="profile-card-heading">
              <span className="profile-card-icon">✎</span>
              <div><h2 id="details-title">Account</h2><p>Your display name.</p></div>
            </div>
            <label className="profile-name-field">
              <span>Display name</span>
              <input type="text" maxLength={40} placeholder="Enter your name"
                value={profileSettings.name}
                onChange={(e) => updateAvatar(e.target.value, profileSettings.animal, profileSettings.image)} />
            </label>
            {currentUser && <p className="profile-account-info">Signed in as <strong>{currentUser.email}</strong></p>}
            <div className="profile-privacy-note"><span>⌑</span><p>Picture and name are stored in this browser only.</p></div>
          </section>
        </div>

        {/* ── Eligibility details ───────────────────────────────────── */}
        {currentUser ? (
          <section className="profile-card profile-demographic-card" aria-labelledby="demo-title">
            <div className="profile-card-heading">
              <span className="profile-card-icon">⊙</span>
              <div>
                <h2 id="demo-title">Eligibility details</h2>
                <p>All fields are optional — fill in what applies to you.</p>
              </div>
            </div>

            <form onSubmit={handleSave} noValidate>

              {/* Personal */}
              <div className="optional-divider"><span>Personal</span></div>
              <div className="field-grid">
                <label className="field">
                  <span>Age</span>
                  <input type="number" min="0" max="120" placeholder="e.g. 21"
                    value={form.age} onChange={(e) => updateField('age', e.target.value)}
                    aria-invalid={Boolean(formErrors.age)} />
                  {formErrors.age && <small className="field-error">{formErrors.age}</small>}
                </label>
                <label className="field">
                  <span>Gender</span>
                  <select value={form.gender} onChange={(e) => updateField('gender', e.target.value)}>
                    <option value="">Prefer not to say</option>
                    <option>Male</option><option>Female</option><option>Other</option>
                  </select>
                </label>
                <label className="field">
                  <span>Social category</span>
                  <select value={form.category} onChange={(e) => updateField('category', e.target.value)}>
                    <option value="">Prefer not to say</option>
                    {['General', 'OBC', 'SC', 'ST', 'EWS', 'Other'].map((o) => <option key={o}>{o}</option>)}
                  </select>
                </label>
              </div>

              {/* Location */}
              <div className="optional-divider"><span>Location</span></div>
              <div className="field-grid">
                <label className="field">
                  <span>State / UT</span>
                  <select value={form.state} onChange={(e) => updateField('state', e.target.value)}>
                    <option value="">Select your state</option>
                    {states.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </label>
                <label className="field">
                  <span>District</span>
                  <input type="text" placeholder="Your district"
                    value={form.district} onChange={(e) => updateField('district', e.target.value)} />
                </label>
              </div>

              {/* Education & Work */}
              <div className="optional-divider"><span>Education &amp; work</span></div>
              <div className="field-grid">
                <label className="field">
                  <span>Occupation</span>
                  <select value={form.occupation} onChange={(e) => updateField('occupation', e.target.value)}>
                    <option value="">Choose an occupation</option>
                    {['Student', 'Farmer', 'Salaried', 'Self-employed', 'Artisan / craftsperson', 'Homemaker', 'Unemployed', 'Retired', 'Other'].map((o) => <option key={o}>{o}</option>)}
                  </select>
                </label>

                {isEmployed(form) && (
                  <label className="field field-reveal">
                    <span>{form.occupation === 'Salaried' ? 'Sector' : 'Business type'}</span>
                    <select value={form.profession} onChange={(e) => updateField('profession', e.target.value)}>
                      <option value="">Choose one</option>
                      {form.occupation === 'Salaried'
                        ? ['Government / PSU', 'Private sector', 'Defence / Paramilitary', 'Teaching / Academia', 'Healthcare', 'IT / Technology', 'Other'].map((o) => <option key={o}>{o}</option>)
                        : ['Retail / Trade', 'Services', 'Manufacturing / Craft', 'Agriculture-related', 'Transport', 'Construction', 'Other'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>
                )}

                {isStudent(form) && (
                  <label className="field field-reveal">
                    <span>Institution type</span>
                    <select value={form.institution_type} onChange={(e) => updateField('institution_type', e.target.value)}>
                      <option value="">Choose one</option>
                      {['Government school', 'Private school', 'Government college / university', 'Private college / university', 'ITI / Polytechnic', 'Other'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>
                )}

                {isFarmer(form) && (
                  <label className="field field-reveal">
                    <span>Land holding <span className="field-unit">acres</span></span>
                    <input type="number" min="0" step="0.1" placeholder="e.g. 2.5"
                      value={form.land_holding_acres} onChange={(e) => updateField('land_holding_acres', e.target.value)} />
                  </label>
                )}

                {!isStudent(form) && !isFarmer(form) && form.occupation !== 'Homemaker' && form.occupation !== 'Unemployed' && form.occupation !== 'Retired' && form.occupation !== '' && (
                  <label className="field field-reveal">
                    <span>Employment type</span>
                    <select value={form.employment_status} onChange={(e) => updateField('employment_status', e.target.value)}>
                      <option value="">Choose type</option>
                      {['Full-time', 'Part-time', 'Contract / Temporary', 'Casual / Daily wage', 'Self-employed'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>
                )}

                <label className="field">
                  <span>Education level</span>
                  <select value={form.education_level} onChange={(e) => updateField('education_level', e.target.value)}>
                    <option value="">Choose level</option>
                    {['No formal education', 'Primary school', 'Secondary school', 'Higher secondary', 'Undergraduate', 'Postgraduate', 'Vocational / ITI', 'Other'].map((o) => <option key={o}>{o}</option>)}
                  </select>
                </label>
              </div>

              {/* Financial */}
              <div className="optional-divider"><span>Financial</span></div>
              <div className="field-grid">
                <label className="field">
                  <span>Annual family income <span className="field-unit">₹</span></span>
                  <input type="number" min="0" placeholder="e.g. 200000"
                    value={form.annual_income} onChange={(e) => updateField('annual_income', e.target.value)}
                    aria-invalid={Boolean(formErrors.annual_income)} />
                  {formErrors.annual_income && <small className="field-error">{formErrors.annual_income}</small>}
                  <small className="field-hint">Household total — used in income-based scheme checks.</small>
                </label>
              </div>

              {/* Family & Health */}
              <div className="optional-divider"><span>Family &amp; health</span></div>
              <div className="field-grid">
                <label className="field">
                  <span>Marital status</span>
                  <select value={form.marital_status} onChange={(e) => updateField('marital_status', e.target.value)}>
                    <option value="">Prefer not to say</option>
                    {['Single', 'Married', 'Widowed', 'Divorced', 'Separated'].map((o) => <option key={o}>{o}</option>)}
                  </select>
                </label>

                {hasFamily(form) && (
                  <label className="field field-reveal">
                    <span>Number of dependants <span className="field-optional">(children + elderly)</span></span>
                    <input type="number" min="0" max="20" placeholder="e.g. 2"
                      value={form.dependants} onChange={(e) => updateField('dependants', e.target.value)} />
                    <small className="field-hint">Family members who depend on you financially.</small>
                  </label>
                )}

                <label className="field">
                  <span>Do you have a disability?</span>
                  <select value={form.disability_status} onChange={(e) => updateField('disability_status', e.target.value)}>
                    <option value="">Prefer not to say</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </label>

                {hasDisability(form) && (
                  <label className="field field-reveal">
                    <span>Type of disability</span>
                    <select value={form.disability_type} onChange={(e) => updateField('disability_type', e.target.value)}>
                      <option value="">Prefer not to say</option>
                      {['Locomotor', 'Visual', 'Hearing / Speech', 'Intellectual', 'Mental illness', 'Multiple disabilities', 'Other'].map((o) => <option key={o}>{o}</option>)}
                    </select>
                  </label>
                )}
              </div>

              {/* Need */}
              <div className="optional-divider"><span>What you&rsquo;re looking for</span></div>
              <label className="field need-field">
                <span>Your need</span>
                <textarea rows={3} maxLength={1000}
                  placeholder="e.g. Looking for schemes to help fund my daughter's college fees."
                  value={form.need} onChange={(e) => updateField('need', e.target.value)} />
                <div className="textarea-meta">
                  <small>Used for text matching — be specific.</small>
                  <small>{form.need.length}/1000</small>
                </div>
              </label>

              <div className="profile-form-actions">
                <button className="submit-button" type="submit" disabled={saving}>
                  {saving ? 'Saving\u2026' : 'Save details'}{!saving && <span aria-hidden="true"> →</span>}
                </button>
                {saveMessage && (
                  <p className={`profile-save-msg ${saveMessage.startsWith('Could') ? 'error' : 'success'}`} role="status">
                    {saveMessage}
                  </p>
                )}
              </div>
            </form>
          </section>
        ) : (
          <section className="profile-card profile-signin-nudge" aria-label="Sign in prompt">
            <span className="profile-card-icon">↗</span>
            <h2>Save your details</h2>
            <p>Sign in to save your eligibility details and get personalised recommendations every time.</p>
            <Link className="submit-button" to="/login">Sign in or create an account →</Link>
          </section>
        )}
      </section>
    </div>
  )
}
