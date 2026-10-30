import type { ProfileFormValues, ProfileRequest } from '../types'

export const initialProfile: ProfileFormValues = {
  age: '',
  state: '',
  district: '',
  annual_income: '',
  occupation: '',
  profession: '',
  education_level: '',
  employment_status: '',
  farmer_status: '',
  land_holding_acres: '',
  student_status: '',
  institution_type: '',
  category: '',
  disability_status: '',
  disability_type: '',
  gender: '',
  marital_status: '',
  dependants: '',
  need: '',
}

export const states = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry',
]

export const categoryMarks: Record<string, string> = {
  Agriculture: '✳',
  Education: '▤',
  Housing: '⌂',
  'Skills & Business': '↗',
}

export function toProfileRequest(form: ProfileFormValues): ProfileRequest {
  const toBoolean = (v: string) => v === '' ? null : v === 'yes'
  const toNum = (v: string) => v === '' ? null : Number(v)

  // Auto-derive booleans from occupation so the request is consistent
  const isStudent = form.occupation === 'Student'
  const isFarmer = form.occupation === 'Farmer'

  return {
    ...form,
    age: toNum(form.age),
    annual_income: toNum(form.annual_income),
    student_status: isStudent ? true : toBoolean(form.student_status),
    farmer_status: isFarmer ? true : toBoolean(form.farmer_status),
    disability_status: toBoolean(form.disability_status),
    // Clear sub-fields that don't apply
    institution_type: isStudent ? form.institution_type : '',
    land_holding_acres: isFarmer ? toNum(form.land_holding_acres) : null,
    profession: ['Salaried', 'Self-employed'].includes(form.occupation) ? form.profession : '',
    disability_type: form.disability_status === 'yes' ? form.disability_type : '',
    dependants: ['Married', 'Widowed', 'Divorced', 'Separated'].includes(form.marital_status)
      ? toNum(form.dependants)
      : null,
  }
}
