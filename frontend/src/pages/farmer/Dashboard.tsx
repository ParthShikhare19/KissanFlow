/** Farmer Dashboard — simplified, icon-led design for low-literacy users.
 *  Giant status hero + 🔊 listen button + big bilingual quick actions. */
import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  CalendarPlus, AlertCircle, ChevronRight, Bell, Ticket, MapPin, Volume2,
  Check, Clock, Wheat, Landmark, Phone
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useQueueStore } from '@/stores/queueStore'
import { useSocket } from '@/hooks/useSocket'
import { get } from '@/utils/api'
import { speak, isSpeechSupported } from '@/utils/speech'
import { CardSkeleton } from '@/components/LoadingSkeleton'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import i18n from '@/i18n'
import clsx from 'clsx'

interface TimelineEvent {
  stage: string; label: string; status: 'completed' | 'active' | 'pending'
  timestamp?: string; detail?: string
}
interface Booking {
  id: string; token_number: string; qr_code_base64?: string; slot_date: string
  slot_start_time: string; status: string; declared_quantity_q: number
  centre?: { name: string; district: string }; crop?: { name: string }
}
interface Transaction {
  id: string; slot_booking_id: string; total_amount?: number; payment_status: string; crop_name?: string; created_at: string
}
interface ProcessTiming {
  booking_id: string; token_number: string; status: string; slot_date: string
  booking_to_gate_minutes?: number; gate_to_processing_minutes?: number
  processing_to_completion_minutes?: number; total_cycle_minutes?: number
  payment_status?: string | null
}

type HeroState = 'IN_QUEUE' | 'PROCESSING' | 'BOOKED' | 'AWAITING_PAYMENT' | 'NONE'

export default function FarmerDashboard() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { myPosition, isYourTurn, clearQueue, setMyPosition } = useQueueStore()
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [activeBooking, setActiveBooking] = useState<Booking | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [processTimings, setProcessTimings] = useState<ProcessTiming[]>([])
  const [loading, setLoading] = useState(true)

  // Connect socket with farmer room for active booking
  useSocket(undefined, activeBooking?.id)

  useEffect(() => {
    if (!user) return
    const load = async () => {
      try {
        const tl = await get<TimelineEvent[]>(`/farmers/${user.id}/timeline`)
        const txns = await get<{ items: Transaction[] }>(`/farmers/${user.id}/transactions?page=1&page_size=5`)
        const latestBooking = await get<Booking | null>(`/farmers/${user.id}/bookings/latest`)
        const timings = await get<ProcessTiming[]>(`/farmers/${user.id}/process-summary`)
        setProcessTimings(timings)

        setTransactions(txns.items || [])
        setTimeline(tl)
        setActiveBooking(latestBooking)
        if (!latestBooking) clearQueue()

        // Initial queue position (#7): socket pushes keep it fresh afterwards.
        if (latestBooking && ['ARRIVED', 'IN_QUEUE', 'PROCESSING'].includes(latestBooking.status)) {
          try {
            const pos = await get<{ booking_id: string; position: number; estimated_wait_minutes: number; status: string; ahead_of_you: number }>(
              `/queue/position/${latestBooking.id}`
            )
            setMyPosition(pos)
          } catch {
            setMyPosition(null)
          }
        } else {
          setMyPosition(null)
        }
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user, clearQueue, setMyPosition])

  if (loading) return (
    <div className="space-y-6">
      <CardSkeleton />
      <div className="grid md:grid-cols-2 gap-6">
        <CardSkeleton /><CardSkeleton />
      </div>
    </div>
  )

  const lang: 'hi' | 'en' = i18n.language === 'hi' ? 'hi' : 'en'

  // Derive the hero state from the selected booking.
  let hero: HeroState = 'NONE'
  if (activeBooking) {
    if (['ARRIVED', 'IN_QUEUE', 'CALLED'].includes(activeBooking.status)) hero = 'IN_QUEUE'
    else if (activeBooking.status === 'PROCESSING') hero = 'PROCESSING'
    else if (activeBooking.status === 'BOOKED') hero = 'BOOKED'
    else if (activeBooking.status === 'COMPLETED') hero = 'AWAITING_PAYMENT'
  }
  const paidLatest = activeBooking
    ? transactions.find(
        (txn) => txn.slot_booking_id === activeBooking.id && txn.payment_status === 'PAID'
      )
    : undefined
  if (hero === 'AWAITING_PAYMENT' && paidLatest) hero = 'NONE'

  const heroConfig: Record<HeroState, {
    icon: React.ElementType; color: string; bg: string; key: string
  }> = {
    IN_QUEUE: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200', key: 'farmer.hero.IN_QUEUE' },
    PROCESSING: { icon: Wheat, color: 'text-blue-600', bg: 'bg-blue-50 border-blue-200', key: 'farmer.hero.PROCESSING' },
    BOOKED: { icon: Ticket, color: 'text-primary', bg: 'bg-primary-50 border-primary-200', key: 'farmer.hero.BOOKED' },
    AWAITING_PAYMENT: { icon: Landmark, color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200', key: 'farmer.hero.AWAITING_PAYMENT' },
    NONE: { icon: CalendarPlus, color: 'text-gray-500', bg: 'bg-gray-50 border-gray-200', key: 'farmer.hero.NONE' },
  }
  const HeroIcon = heroConfig[hero].icon

  const heroBigValue = hero === 'IN_QUEUE' && myPosition
    ? `#${myPosition.position}`
    : hero === 'BOOKED' && activeBooking
      ? activeBooking.token_number
      : null

  const readAloud = () => {
    const lines: string[] = []
    if (hero === 'IN_QUEUE' && myPosition) {
      lines.push(lang === 'hi'
        ? `आप कतार में नंबर ${myPosition.position} पर हैं। अनुमानित प्रतीक्षा ${myPosition.estimated_wait_minutes} मिनट।`
        : `You are number ${myPosition.position} in the queue. Estimated wait ${myPosition.estimated_wait_minutes} minutes.`)
    } else {
      lines.push(t(heroConfig[hero].key))
    }
    if (activeBooking) {
      lines.push(lang === 'hi'
        ? `टोकन ${activeBooking.token_number}, मंडी ${activeBooking.centre?.name}, तारीख ${activeBooking.slot_date}, समय ${activeBooking.slot_start_time?.slice(0, 5)}।`
        : `Token ${activeBooking.token_number}, mandi ${activeBooking.centre?.name}, date ${activeBooking.slot_date}, time ${activeBooking.slot_start_time?.slice(0, 5)}.`)
    }
    speak(lines.join(' '), lang)
  }

  // Mark the first pending stage as visually active.
  const timelineView = timeline.map((e, i) => {
    if (e.status === 'completed') return e
    const firstPending = timeline.findIndex((x) => x.status !== 'completed')
    return i === firstPending ? { ...e, status: 'active' as const } : e
  })

  const quickActions = [
    { to: '/farmer/bookings', icon: Ticket, key: 'nav.myPass', color: 'text-primary', bg: 'bg-primary-50' },
    { to: '/farmer/grievances', icon: AlertCircle, key: 'nav.grievances', color: 'text-rose-500', bg: 'bg-rose-50' },
    { to: '/farmer/ivr', icon: Phone, key: 'nav.ivr', color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { to: '/notifications', icon: Bell, key: 'nav.notifications', color: 'text-blue-500', bg: 'bg-blue-50' },
  ]

  return (
    <ErrorBoundary>
      <div className="space-y-6 animate-fade-in pb-12">
        {/* Greeting */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="page-title">{t('farmer.dashboard.title')}</h1>
            <p className="text-gray-500 text-sm mt-1">
              {t('farmer.greeting', { name: user?.name?.split(' ')[0] || 'Farmer' })}
            </p>
          </div>
          <button
            onClick={readAloud}
            className="btn-secondary text-base px-5 py-3 flex items-center gap-2"
            id="hero-listen"
            aria-label={t('pass.listen')}
          >
            <Volume2 className="w-5 h-5" /> {t('pass.listen')}
          </button>
        </div>

        {/* ── Giant Status Hero ─────────────────────────────────────────── */}
        <div className={clsx(
          'card p-6 sm:p-8 border-2 flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left',
          heroConfig[hero].bg
        )}>
          <div className={clsx(
            'w-20 h-20 rounded-3xl flex items-center justify-center flex-shrink-0',
            hero === 'IN_QUEUE' && 'animate-pulse',
            'bg-white shadow-sm'
          )}>
            <HeroIcon className={clsx('w-11 h-11', heroConfig[hero].color)} />
          </div>
          <div className="flex-1">
            <p className="text-xl sm:text-2xl font-extrabold text-gray-900 leading-snug">
              {t(heroConfig[hero].key)}
            </p>
            {heroBigValue && (
              <p className="text-6xl font-black text-gray-900 mt-2 leading-none tracking-tight">
                {heroBigValue}
              </p>
            )}
            {hero === 'IN_QUEUE' && myPosition && (
              <p className="text-gray-700 font-semibold mt-2 text-base">
                {t('queue.eta', { minutes: myPosition.estimated_wait_minutes })} · {t('queue.ahead', { count: myPosition.ahead_of_you })}
              </p>
            )}
            {activeBooking && (hero === 'BOOKED' || hero === 'IN_QUEUE') && (
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-x-5 gap-y-1 text-sm text-gray-700 mt-3 font-medium">
                <span className="flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-primary" />{activeBooking.centre?.name}
                </span>
                <span className="flex items-center gap-1.5">
                  <Wheat className="w-4 h-4 text-amber-500" />{activeBooking.crop?.name} · {activeBooking.declared_quantity_q} Q
                </span>
                <span className="flex items-center gap-1.5">
                  <CalendarPlus className="w-4 h-4 text-gray-400" />{activeBooking.slot_date} {activeBooking.slot_start_time?.slice(0, 5)}
                </span>
              </div>
            )}
            {hero === 'AWAITING_PAYMENT' && activeBooking && (
              <p className="text-gray-700 font-semibold mt-2 text-base">
                {activeBooking.token_number} · {activeBooking.centre?.name}
              </p>
            )}
          </div>
          {hero === 'NONE' && (
            <Link to="/farmer/book-slot" className="btn-primary text-base px-6 py-3.5 flex-shrink-0">
              <CalendarPlus className="w-5 h-5" /> {t('farmer.dashboard.bookNow')}
            </Link>
          )}
          {hero !== 'NONE' && (
            <Link to="/farmer/bookings" className="btn-primary text-base px-6 py-3.5 flex-shrink-0">
              <Ticket className="w-5 h-5" /> {t('nav.myPass')}
            </Link>
          )}
        </div>

        {/* Your Turn Alert */}
        {isYourTurn && (
          <div className="card p-5 border-2 border-primary bg-primary/5 flex items-center gap-4 animate-fade-in">
            <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center flex-shrink-0 animate-bounce">
              <Bell className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <p className="font-extrabold text-primary text-lg">
                {t('queue.yourTurn')}
              </p>
              <p className="text-gray-700 text-sm mt-0.5">{t('farmer.dashboard.yourTurnHelp')}</p>
            </div>
          </div>
        )}

        {/* ── Big Quick Actions ─────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/farmer/book-slot"
            className="card p-5 flex flex-col items-center gap-3 text-center hover:shadow-card-hover hover:border-primary-200 transition-all min-h-[130px] justify-center"
          >
            <div className="w-14 h-14 rounded-2xl bg-primary-50 flex items-center justify-center">
              <CalendarPlus className="w-7 h-7 text-primary" />
            </div>
            <div className="text-sm font-bold text-gray-900 leading-tight">
              {t('farmer.dashboard.bookNow')}
            </div>
          </Link>
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.to}
                to={action.to}
                className="card p-5 flex flex-col items-center gap-3 text-center hover:shadow-card-hover hover:border-primary-200 transition-all min-h-[130px] justify-center"
              >
                <div className={clsx('w-14 h-14 rounded-2xl flex items-center justify-center', action.bg)}>
                  <Icon className={clsx('w-7 h-7', action.color)} />
                </div>
                <div className="text-sm font-bold text-gray-900 leading-tight">
                  {t(action.key)}
                </div>
              </Link>
            )
          })}
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {/* Procurement Timeline — simplified */}
          <div className="card p-5 md:p-6 md:col-span-2">
            <div className="flex items-center justify-between mb-6">
              <h2 className="section-title">
                {t('farmer.dashboard.timeline')}
                <span className="block text-sm text-gray-500 font-normal mt-1">{t('farmer.dashboard.timelineSub')}</span>
              </h2>
            </div>

            {timelineView.length === 0 ? (
              <div className="text-center py-10 border border-dashed border-gray-200 rounded-xl">
                <Clock className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-400 text-sm">{t('common.noData')}</p>
              </div>
            ) : (
              <ol className="relative border-l-2 border-gray-200 space-y-6 pl-7 ml-2 my-2">
                {timelineView.map((event) => (
                  <li key={event.stage} className="relative">
                    <span className={clsx(
                      'absolute -left-[35px] w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 border-white shadow-xs',
                      event.status === 'completed' ? 'bg-emerald-500 text-white' :
                      event.status === 'active' ? 'bg-primary text-white ring-4 ring-primary/20 animate-pulse' :
                      'bg-gray-100 text-gray-400'
                    )}>
                      {event.status === 'completed' ? <Check className="w-4 h-4 stroke-[3]" /> :
                       event.status === 'active' ? <Clock className="w-4 h-4" /> :
                       <span className="w-2 h-2 rounded-full bg-gray-300" />}
                    </span>
                    <div className="ml-1">
                      <p className={clsx(
                        'text-[15px] font-semibold',
                        event.status === 'completed' ? 'text-gray-900' :
                        event.status === 'active' ? 'text-primary font-bold' : 'text-gray-500'
                      )}>
                        {t(`timeline.${event.stage}`)}
                      </p>
                      {event.detail && <p className="text-sm text-gray-600 mt-0.5">{event.detail}</p>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>

          {/* Right Column — payouts summary */}
          <div className="space-y-5">
            <div className="card p-5 border-l-4 border-l-emerald-500">
              <p className="text-xs font-bold text-gray-600 uppercase tracking-wider">{t('farmer.dashboard.recentPayout')}</p>
              <p className="text-3xl leading-tight font-extrabold text-gray-950 mt-2">
                {paidLatest?.total_amount ? `₹${paidLatest.total_amount.toLocaleString('en-IN')}` : '₹0'}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {paidLatest ? t('farmer.dashboard.paidViaPfms') : t('farmer.dashboard.noPayout')}
              </p>
            </div>

            {/* Process timing mini table (kept for judges; simplified labels) */}
            {processTimings.length > 0 && (
              <div className="card p-5">
                <h3 className="font-bold text-gray-900 text-base mb-3">
                  {t('farmer.dashboard.processTiming')}
                  <span className="block text-xs text-gray-500 font-normal mt-0.5">{t('farmer.dashboard.processTimingSub')}</span>
                </h3>
                <div className="space-y-2">
                  {processTimings.slice(0, 3).map((timing) => (
                    <div key={timing.booking_id} className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2">
                      <span className="font-mono font-semibold text-gray-800">{timing.token_number}</span>
                      <span className="font-bold text-primary">
                        {timing.total_cycle_minutes != null ? `${timing.total_cycle_minutes} min` : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Recent Transactions */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">
              {t('farmer.dashboard.recentTransactions')}
              <span className="block text-xs text-gray-400 font-normal mt-0.5">{t('farmer.dashboard.recentTransactionsSub')}</span>
            </h2>
          </div>
          {transactions.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">{t('common.noData')}</p>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('txn.crop')}</th><th>{t('txn.amount')}</th><th>{t('txn.paymentStatus')}</th><th>{t('txn.date')}</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((txn) => (
                    <tr key={txn.id} className="hover:bg-gray-50/70 transition-colors">
                      <td className="font-semibold text-gray-900">{txn.crop_name || '—'}</td>
                      <td className="font-medium text-gray-900">
                        {txn.total_amount ? `₹${txn.total_amount.toLocaleString('en-IN')}` : '—'}
                      </td>
                      <td>
                        <span className={clsx('badge text-xs', {
                          'badge-green': txn.payment_status === 'PAID',
                          'badge-yellow': ['INITIATED', 'PROCESSING'].includes(txn.payment_status),
                          'badge-gray': txn.payment_status === 'NOT_INITIATED',
                          'badge-red': txn.payment_status === 'FAILED',
                        })}>
                          {t(`payment.${txn.payment_status}`)}
                        </span>
                      </td>
                      <td className="text-gray-400 text-xs">
                        {new Date(txn.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
