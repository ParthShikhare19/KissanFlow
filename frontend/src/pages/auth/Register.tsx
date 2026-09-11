/** Multi-step farmer registration with Aadhaar verification. */
import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { CheckCircle, Loader2, AlertCircle } from 'lucide-react'
import { api } from '@/utils/api'
import { useAuthStore } from '@/stores/authStore'

const STEPS = ['auth.register.step1', 'auth.register.step2', 'auth.register.step3', 'auth.register.step4']
const INDIAN_STATES = [
  'Andhra Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana',
  'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra',
  'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan',
  'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand',
  'West Bengal', 'Delhi', 'Puducherry'
]

interface FormData {
  name: string; mobile: string; aadhaar: string; password: string; confirmPassword: string
  village: string; district: string; state: string; landHolding: string
  bankAccount: string; ifsc: string
  cscMode: boolean; aadhaarVerified: boolean
}

export default function Register() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { setTokens } = useAuthStore()
  const [step, setStep] = useState(0)
  const [verifying, setVerifying] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState<FormData>({
    name: '', mobile: '', aadhaar: '', password: '', confirmPassword: '',
    village: '', district: '', state: '', landHolding: '',
    bankAccount: '', ifsc: '',
    cscMode: false, aadhaarVerified: false,
  })
  const [errors, setErrors] = useState<Partial<FormData>>({})

  const update = (field: keyof FormData, value: string | boolean) =>
    setForm((f) => ({ ...f, [field]: value }))

  const validateStep = (s: number): boolean => {
    const errs: Partial<FormData> = {}
    if (s === 0) {
      if (!form.name.trim()) errs.name = 'Name is required'
      if (form.mobile.length !== 10) errs.mobile = 'Enter valid 10-digit mobile'
      if (!form.aadhaarVerified) errs.aadhaar = 'Please verify Aadhaar'
      if (form.password.length < 6) errs.password = 'Minimum 6 characters'
      if (form.password !== form.confirmPassword) errs.confirmPassword = 'Passwords do not match'
    }
    if (s === 1) {
      if (!form.village.trim()) errs.village = 'Village is required'
      if (!form.district.trim()) errs.district = 'District is required'
      if (!form.state) errs.state = 'State is required'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const verifyAadhaar = async () => {
    if (form.aadhaar.replace(/\s/g, '').length !== 12) {
      toast.error('Enter valid 12-digit Aadhaar number')
      return
    }
    setVerifying(true)
    try {
      const res = await api.post('/mock/aadhaar/verify', {
        aadhaar_number: form.aadhaar.replace(/\s/g, ''),
      })
      if (res.data.data?.verified) {
        update('aadhaarVerified', true)
        toast.success('Aadhaar verified successfully!')
      } else {
        toast.error(res.data.data?.error || 'Verification failed')
      }
    } catch {
      toast.error('Verification service unavailable')
    } finally {
      setVerifying(false)
    }
  }

  const handleNext = () => {
    if (validateStep(step)) setStep((s) => s + 1)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const payload = {
        name: form.name,
        mobile: form.mobile,
        aadhaar_number: form.aadhaar.replace(/\s/g, ''),
        role: 'FARMER',
        password: form.password,
        farmer_profile: {
          village: form.village,
          district: form.district,
          state: form.state,
          land_holding: parseFloat(form.landHolding) || 0,
          bank_account_number: form.bankAccount || undefined,
          bank_ifsc_code: form.ifsc || undefined,
        },
      }
      const res = await api.post('/auth/register', payload)
      if (res.data.success) {
        // Auto-login
        const loginRes = await api.post('/auth/login', {
          mobile: form.mobile,
          password: form.password,
        })
        const { access_token, refresh_token, user } = loginRes.data.data
        setTokens(access_token, refresh_token, user)
        toast.success('Registration successful! Welcome to AnnSetu 🌾')
        navigate('/farmer/dashboard')
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Registration failed'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* CSC Mode Banner */}
        {form.cscMode && (
          <div className="mb-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <p className="text-sm text-amber-800 font-medium">{t('auth.register.cscMode')}</p>
          </div>
        )}

        <div className="card p-8 shadow-card-lg">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-2xl font-bold text-gray-900">{t('auth.register.title')}</h1>
              <button
                onClick={() => update('cscMode', !form.cscMode)}
                className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                  form.cscMode ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'
                }`}
              >
                CSC Mode
              </button>
            </div>

            {/* Step indicators */}
            <div className="flex items-center gap-2">
              {STEPS.map((s, i) => (
                <React.Fragment key={i}>
                  <div
                    className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-all ${
                      i < step ? 'bg-primary text-white' :
                      i === step ? 'bg-primary text-white ring-4 ring-primary-100' :
                      'bg-gray-100 text-gray-400'
                    }`}
                  >
                    {i < step ? <CheckCircle className="w-4 h-4" /> : i + 1}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`flex-1 h-1 rounded ${i < step ? 'bg-primary' : 'bg-gray-100'}`} />
                  )}
                </React.Fragment>
              ))}
            </div>
            <p className="text-sm text-gray-500 mt-3 font-medium">{t(STEPS[step])}</p>
          </div>

          {/* Step 1 — Personal */}
          {step === 0 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <label className="label">{t('auth.register.name')}</label>
                <input className={`input ${errors.name ? 'input-error' : ''}`} value={form.name}
                  onChange={(e) => update('name', e.target.value)} placeholder="Ranjit Singh" id="reg-name" />
                {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
              </div>
              <div>
                <label className="label">{t('auth.register.mobile')}</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">+91</span>
                  <input className={`input pl-12 ${errors.mobile ? 'input-error' : ''}`} type="tel"
                    value={form.mobile} onChange={(e) => update('mobile', e.target.value.replace(/\D/g, '').slice(0, 10))}
                    placeholder="9876543210" id="reg-mobile" />
                </div>
                {errors.mobile && <p className="text-red-500 text-xs mt-1">{errors.mobile}</p>}
              </div>
              <div>
                <label className="label">{t('auth.register.aadhaar')}</label>
                <div className="flex gap-2">
                  <input
                    className={`input flex-1 ${errors.aadhaar && !form.aadhaarVerified ? 'input-error' : ''}`}
                    value={form.aadhaar}
                    onChange={(e) => {
                      update('aadhaar', e.target.value)
                      update('aadhaarVerified', false)
                    }}
                    placeholder="1234 5678 9012"
                    maxLength={14}
                    id="reg-aadhaar"
                  />
                  <button
                    type="button"
                    onClick={verifyAadhaar}
                    disabled={verifying || form.aadhaarVerified}
                    className={form.aadhaarVerified ? 'btn-secondary' : 'btn-primary'}
                    id="reg-aadhaar-verify"
                  >
                    {verifying ? <Loader2 className="w-4 h-4 animate-spin" /> :
                     form.aadhaarVerified ? <><CheckCircle className="w-4 h-4 text-green-500" /> {t('auth.register.verified')}</> :
                     t('auth.register.verify')}
                  </button>
                </div>
                {errors.aadhaar && <p className="text-red-500 text-xs mt-1">{errors.aadhaar}</p>}
              </div>
              <div>
                <label className="label">{t('auth.register.password')}</label>
                <input className={`input ${errors.password ? 'input-error' : ''}`} type="password"
                  value={form.password} onChange={(e) => update('password', e.target.value)}
                  placeholder="••••••••" id="reg-password" />
                {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
              </div>
              <div>
                <label className="label">Confirm Password</label>
                <input className={`input ${errors.confirmPassword ? 'input-error' : ''}`} type="password"
                  value={form.confirmPassword} onChange={(e) => update('confirmPassword', e.target.value)}
                  placeholder="••••••••" id="reg-confirm-password" />
                {errors.confirmPassword && <p className="text-red-500 text-xs mt-1">{errors.confirmPassword}</p>}
              </div>
            </div>
          )}

          {/* Step 2 — Location */}
          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <label className="label">{t('auth.register.village')}</label>
                <input className={`input ${errors.village ? 'input-error' : ''}`} value={form.village}
                  onChange={(e) => update('village', e.target.value)} placeholder="Fatehgarh" id="reg-village" />
              </div>
              <div>
                <label className="label">{t('auth.register.district')}</label>
                <input className={`input ${errors.district ? 'input-error' : ''}`} value={form.district}
                  onChange={(e) => update('district', e.target.value)} placeholder="Ludhiana" id="reg-district" />
              </div>
              <div>
                <label className="label">{t('auth.register.state')}</label>
                <select className={`select ${errors.state ? 'input-error' : ''}`} value={form.state}
                  onChange={(e) => update('state', e.target.value)} id="reg-state">
                  <option value="">Select State</option>
                  {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="label">{t('auth.register.landHolding')}</label>
                <input className="input" type="number" step="0.1" min="0" value={form.landHolding}
                  onChange={(e) => update('landHolding', e.target.value)} placeholder="5.0" id="reg-land" />
              </div>
            </div>
          )}

          {/* Step 3 — Bank */}
          {step === 2 && (
            <div className="space-y-4 animate-fade-in">
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-700">
                💡 Bank details are used for direct payment after crop procurement.
              </div>
              <div>
                <label className="label">{t('auth.register.bankAccount')}</label>
                <input className="input" type="text" value={form.bankAccount}
                  onChange={(e) => update('bankAccount', e.target.value)}
                  placeholder="Account Number" id="reg-bank-account" />
              </div>
              <div>
                <label className="label">{t('auth.register.ifsc')}</label>
                <input className="input" type="text" value={form.ifsc}
                  onChange={(e) => update('ifsc', e.target.value.toUpperCase())}
                  placeholder="PUNB0001234" id="reg-ifsc" />
              </div>
            </div>
          )}

          {/* Step 4 — Confirm */}
          {step === 3 && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="text-base font-semibold text-gray-900">Review Your Details</h3>
              <div className="bg-gray-50 rounded-xl p-4 space-y-2 text-sm">
                {[
                  ['Name', form.name],
                  ['Mobile', `+91 ${form.mobile}`],
                  ['Aadhaar', form.aadhaar.slice(0, 4) + ' XXXX XXXX'],
                  ['Village', form.village],
                  ['District', form.district],
                  ['State', form.state],
                  ['Land Holding', form.landHolding ? `${form.landHolding} acres` : 'Not specified'],
                  ['Bank A/C', form.bankAccount ? 'XXXXXXXXXX' + form.bankAccount.slice(-4) : 'Not provided'],
                  ['IFSC', form.ifsc || 'Not provided'],
                ].map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-gray-500 font-medium">{key}</span>
                    <span className="text-gray-900 font-semibold">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex gap-3 mt-6">
            {step > 0 && (
              <button onClick={() => setStep((s) => s - 1)} className="btn-secondary flex-1">
                {t('auth.register.back')}
              </button>
            )}
            {step < 3 ? (
              <button onClick={handleNext} className="btn-primary flex-1" id={`reg-next-${step}`}>
                {t('auth.register.next')}
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="btn-primary flex-1"
                id="reg-submit"
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Registering...
                  </span>
                ) : t('auth.register.submit')}
              </button>
            )}
          </div>

          <div className="mt-4 text-center">
            <Link to="/login" className="text-gray-500 text-sm hover:text-primary">
              Already registered? Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
