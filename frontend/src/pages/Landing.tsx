/** Landing page — hero, features, role entry cards. */
import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CalendarCheck, Users, ShieldCheck, ArrowRight, Sprout } from 'lucide-react'

const ROLE_CARDS = [
  {
    role: 'farmer',
    labelKey: 'landing.roles.farmer',
    emoji: '🌾',
    color: 'from-green-500 to-emerald-600',
    to: '/login?role=FARMER',
    desc: 'Book slots, track queue, receive payments',
  },
  {
    role: 'staff',
    labelKey: 'landing.roles.staff',
    emoji: '🏢',
    color: 'from-blue-500 to-blue-600',
    to: '/login?role=MANDI_STAFF',
    desc: 'Gate entry, queue management, transactions',
  },
  {
    role: 'officer',
    labelKey: 'landing.roles.officer',
    emoji: '📋',
    color: 'from-violet-500 to-purple-600',
    to: '/login?role=MANDI_OFFICER',
    desc: 'Approve transactions, monitor alerts, resolve grievances',
  },
  {
    role: 'govt',
    labelKey: 'landing.roles.govt',
    emoji: '🏛️',
    color: 'from-orange-500 to-amber-600',
    to: '/login?role=GOVT_ADMIN',
    desc: 'National procurement analytics and oversight',
  },
]

const FEATURES = [
  {
    icon: CalendarCheck,
    titleKey: 'landing.feature.slot.title',
    descKey: 'landing.feature.slot.desc',
    color: 'text-primary',
    bg: 'bg-primary-50',
  },
  {
    icon: Users,
    titleKey: 'landing.feature.queue.title',
    descKey: 'landing.feature.queue.desc',
    color: 'text-blue-600',
    bg: 'bg-blue-50',
  },
  {
    icon: ShieldCheck,
    titleKey: 'landing.feature.audit.title',
    descKey: 'landing.feature.audit.desc',
    color: 'text-violet-600',
    bg: 'bg-violet-50',
  },
]

export default function Landing() {
  const { t, i18n } = useTranslation()

  const toggleLang = () => {
    const next = i18n.language === 'en' ? 'hi' : 'en'
    i18n.changeLanguage(next)
    localStorage.setItem('annsetu-lang', next)
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Language Toggle */}
      <div className="absolute top-4 right-4 z-10">
        <button
          onClick={toggleLang}
          className="px-4 py-2 rounded-lg bg-white/80 backdrop-blur border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-colors"
        >
          {i18n.language === 'en' ? 'हिंदी' : 'English'}
        </button>
      </div>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary via-primary-light to-emerald-400">
        {/* Background decoration */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-10 w-64 h-64 rounded-full bg-white" />
          <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-white" />
        </div>

        <div className="relative max-w-6xl mx-auto px-6 py-24 md:py-36 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/20 backdrop-blur text-white text-sm font-medium mb-8 animate-fade-in">
            <Sprout className="w-4 h-4" />
            <span>Smart India Hackathon 2024 — Ministry of Agriculture</span>
          </div>

          {/* Title */}
          <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-4 animate-fade-in tracking-tight">
            {t('app.name')}
          </h1>

          {/* Tagline in both languages */}
          <p className="text-xl md:text-2xl text-white/90 font-medium mb-2 animate-fade-in">
            {t('landing.hero.subtitle')}
          </p>
          <p className="text-2xl md:text-3xl text-white/80 font-semibold mb-10 animate-fade-in" style={{ fontFamily: 'sans-serif' }}>
            {t('landing.hero.subtitle_hi')}
          </p>

          <Link
            to="/login"
            className="inline-flex items-center gap-2 px-8 py-4 bg-accent text-white rounded-xl font-bold text-lg hover:bg-accent-dark transition-all hover:scale-105 shadow-lg hover:shadow-xl"
          >
            {t('landing.hero.cta')}
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-muted">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            Built for India's 140M Farmers
          </h2>
          <p className="text-center text-gray-500 mb-12 max-w-2xl mx-auto">
            AnnSetu digitizes the entire agricultural procurement workflow — from slot booking to payment disbursement.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {FEATURES.map((f) => {
              const Icon = f.icon
              return (
                <div key={f.titleKey} className="card p-8 hover:shadow-card-hover transition-shadow group">
                  <div className={`w-14 h-14 ${f.bg} rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
                    <Icon className={`w-7 h-7 ${f.color}`} />
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">{t(f.titleKey)}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{t(f.descKey)}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Stats Strip */}
      <section className="py-12 px-6 bg-primary">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { value: '5 States', label: 'Covered' },
            { value: '₹2275/Q', label: 'Wheat MSP 2025' },
            { value: '100%', label: 'Digital Payments' },
            { value: '< 5 min', label: 'Queue Updates' },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-2xl md:text-3xl font-extrabold text-white">{s.value}</div>
              <div className="text-white/70 text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Role Entry Cards */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-3">Who are you?</h2>
          <p className="text-center text-gray-500 mb-12">Select your role to get started</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {ROLE_CARDS.map((card) => (
              <Link
                key={card.role}
                to={card.to}
                className="group relative overflow-hidden rounded-2xl shadow-md hover:shadow-xl transition-all hover:-translate-y-1 cursor-pointer"
              >
                <div className={`bg-gradient-to-br ${card.color} p-8 text-white h-full`}>
                  <div className="text-4xl mb-4">{card.emoji}</div>
                  <h3 className="text-xl font-bold mb-2">{t(card.labelKey)}</h3>
                  <p className="text-white/80 text-sm leading-relaxed">{card.desc}</p>
                  <div className="mt-5 flex items-center gap-1 text-white/90 text-sm font-semibold">
                    Login <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8 px-6 text-center">
        <p className="text-gray-500 text-sm">
          <span className="font-semibold text-primary">AnnSetu — अन्नसेतु</span>
          {' '}| Smart India Hackathon 2024 | Ministry of Agriculture & Farmers Welfare, Government of India
        </p>
      </footer>
    </div>
  )
}
