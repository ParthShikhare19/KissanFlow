/** Login page with mobile, password, and role selector. */
import React, { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { useAuthStore } from '@/stores/authStore'
import { Sprout, Eye, EyeOff } from 'lucide-react'

const ROLES = [
  { value: 'FARMER', label: '🌾 Farmer (किसान)' },
  { value: 'MANDI_STAFF', label: '🏢 Mandi Staff' },
  { value: 'MANDI_OFFICER', label: '📋 Mandi Officer' },
  { value: 'GOVT_ADMIN', label: '🏛️ Govt Admin' },
  { value: 'CSC_OPERATOR', label: '💻 CSC Operator' },
]

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, isLoading } = useAuthStore()

  const [mobile, setMobile] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState(searchParams.get('role') || '')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const errs: Record<string, string> = {}
    if (!mobile || mobile.length !== 10) errs.mobile = 'Enter valid 10-digit mobile'
    if (!password || password.length < 6) errs.password = 'Password must be at least 6 characters'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    try {
      await login(mobile, password, role || undefined)
      toast.success('Welcome back!')
      // Redirect based on role
      const user = useAuthStore.getState().user
      const roleRoutes: Record<string, string> = {
        FARMER: '/farmer/dashboard',
        MANDI_STAFF: '/staff/gate-entry',
        MANDI_OFFICER: '/officer/dashboard',
        GOVT_ADMIN: '/govt/dashboard',
        CSC_OPERATOR: '/farmer/book-slot',
      }
      navigate(roleRoutes[user?.role || ''] || '/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed'
      toast.error(msg)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary shadow-lg mb-4">
            <Sprout className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900">{t('auth.login.title')}</h1>
          <p className="text-gray-500 text-sm mt-1">अन्नसेतु — Digital Procurement Platform</p>
        </div>

        <div className="card p-8 shadow-card-lg">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Mobile */}
            <div>
              <label className="label">{t('auth.login.mobile')}</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium">+91</span>
                <input
                  type="tel"
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value.replace(/\D/g, '').slice(0, 10))}
                  placeholder="9876543210"
                  className={`input pl-12 ${errors.mobile ? 'input-error' : ''}`}
                  autoComplete="tel"
                  id="login-mobile"
                />
              </div>
              {errors.mobile && <p className="text-red-500 text-xs mt-1">{errors.mobile}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="label">{t('auth.login.password')}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={`input pr-10 ${errors.password ? 'input-error' : ''}`}
                  autoComplete="current-password"
                  id="login-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
            </div>

            {/* Role selector */}
            <div>
              <label className="label">{t('auth.login.role')}</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="select"
                id="login-role"
              >
                <option value="">Any Role</option>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full text-base py-3"
              id="login-submit"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Logging in...
                </span>
              ) : t('auth.login.submit')}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-100 text-center">
            <Link to="/register" className="text-primary font-semibold text-sm hover:underline">
              {t('auth.login.register')}
            </Link>
          </div>

          {/* Demo credentials hint */}
          <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-100">
            <p className="text-xs text-amber-800 font-medium text-center">Demo Credentials</p>
            <p className="text-xs text-amber-700 text-center mt-1">Farmer: 9876543210 / farmer123</p>
          </div>
        </div>

        <p className="text-center mt-6 text-xs text-gray-400">
          Ministry of Agriculture & Farmers Welfare, Government of India
        </p>
      </div>
    </div>
  )
}
