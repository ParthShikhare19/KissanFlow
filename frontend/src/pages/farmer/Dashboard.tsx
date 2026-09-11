/** Farmer Dashboard — stats row, active booking preview, timeline, queue position, recent transactions. */
import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  CalendarPlus, CheckCircle2, Clock, AlertCircle, ChevronRight,
  Bell, Ticket, Banknote, MapPin, ArrowRight, ShieldCheck, Check
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useQueueStore } from '@/stores/queueStore'
import { useSocket } from '@/hooks/useSocket'
import { get } from '@/utils/api'
import { CardSkeleton } from '@/components/LoadingSkeleton'
import { ErrorBoundary } from '@/components/ErrorBoundary'
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

export default function FarmerDashboard() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { myPosition, isYourTurn, clearQueue } = useQueueStore()
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
        const farmerTransactions = txns.items || []

        const latestBooking = await get<Booking | null>(`/farmers/${user.id}/bookings/latest`)
        const timings = await get<ProcessTiming[]>(`/farmers/${user.id}/process-summary`)
        setProcessTimings(timings)
        const paymentCompleted = Boolean(
          latestBooking?.status === 'COMPLETED' &&
          farmerTransactions.some(
            (transaction) =>
              transaction.slot_booking_id === latestBooking.id &&
              transaction.payment_status === 'PAID'
          )
        )

        setTransactions(farmerTransactions)
        if (paymentCompleted) {
          setTimeline([])
          setActiveBooking(null)
          clearQueue()
        } else {
          setTimeline(tl)
          setActiveBooking(latestBooking)
        }
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user, clearQueue])

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 17) return 'Good afternoon'
    return 'Good evening'
  }

  if (loading) return (
    <div className="space-y-6">
      <CardSkeleton />
      <div className="grid md:grid-cols-2 gap-6">
        <CardSkeleton /><CardSkeleton />
      </div>
    </div>
  )

  const latestPaid = activeBooking
    ? transactions.find(
        (transaction) =>
          transaction.slot_booking_id === activeBooking.id &&
          transaction.payment_status === 'PAID'
      )
    : undefined
  const formatDuration = (minutes?: number) => minutes == null ? '—' : `${minutes} min`

  return (
    <ErrorBoundary>
      <div className="space-y-8 animate-fade-in pb-12">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="page-title">{t('farmer.dashboard.title')}</h1>
            <p className="text-gray-500 text-sm mt-1">
              {getGreeting()}, <span className="font-semibold text-gray-800">{user?.name?.split(' ')[0] || 'Farmer'}</span>!
            </p>
          </div>
          <Link to="/farmer/book-slot" className="btn-primary">
            <CalendarPlus className="w-4 h-4" />
            {t('farmer.dashboard.bookNow')}
          </Link>
        </div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="card min-h-[124px] p-5 border-l-4 border-l-primary flex items-center justify-between hover:shadow-card-hover transition-shadow">
            <div>
              <p className="text-xs font-bold text-gray-600 uppercase tracking-wider">Active Token</p>
              <p className="text-2xl leading-tight font-bold font-mono text-gray-950 mt-2">
                {activeBooking?.token_number || 'No active slot'}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {activeBooking ? `${activeBooking.centre?.name || 'Mandi'}` : 'Book a slot to get token'}
              </p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-primary-100 flex items-center justify-center text-primary">
              <Ticket className="w-5 h-5" />
            </div>
          </div>

          <div className="card min-h-[124px] p-5 border-l-4 border-l-amber-500 flex items-center justify-between hover:shadow-card-hover transition-shadow">
            <div>
              <p className="text-xs font-bold text-gray-600 uppercase tracking-wider">Queue Position</p>
              <p className="text-2xl leading-tight font-bold text-gray-950 mt-2">
                {myPosition ? `#${myPosition.position}` : (activeBooking?.status || 'Not in queue')}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {myPosition ? `${myPosition.estimated_wait_minutes} min est. wait` : 'Arrive at mandi for gate entry'}
              </p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600">
              <Clock className="w-5 h-5" />
            </div>
          </div>

          <div className="card min-h-[124px] p-5 border-l-4 border-l-emerald-500 flex items-center justify-between hover:shadow-card-hover transition-shadow">
            <div>
              <p className="text-xs font-bold text-gray-600 uppercase tracking-wider">Recent Payout</p>
              <p className="text-2xl leading-tight font-bold text-gray-950 mt-2">
                {latestPaid?.total_amount ? `₹${latestPaid.total_amount.toLocaleString('en-IN')}` : '₹0'}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {latestPaid ? 'Credited via PFMS DBT' : 'No payout yet'}
              </p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
              <Banknote className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Your Turn Alert */}
        {isYourTurn && (
          <div className="card p-4 border-2 border-primary bg-primary/5 flex items-center gap-3 animate-fade-in shadow-sm">
            <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center flex-shrink-0 animate-bounce">
              <Bell className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <p className="font-bold text-primary text-base">{t('farmer.dashboard.yourTurn')}</p>
              <p className="text-gray-700 text-xs mt-0.5">Please proceed to the weighment & quality counter immediately with your tractor/vehicle.</p>
            </div>
          </div>
        )}

        {/* Active Booking Card Preview */}
        {activeBooking && (
          <div className="card p-5 bg-primary-50/40 border-primary-200">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                {activeBooking.qr_code_base64 && (
                  <div className="p-1.5 bg-white border border-gray-200 rounded-xl shadow-xs">
                    <img
                      src={activeBooking.qr_code_base64}
                      alt="Token QR"
                      className="w-16 h-16 object-contain"
                    />
                  </div>
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-lg text-gray-900">{activeBooking.token_number}</span>
                    <span className="badge badge-green text-xs font-semibold">{activeBooking.status}</span>
                  </div>
                  <div className="flex items-center gap-x-5 gap-y-2 text-sm text-gray-600 mt-2 flex-wrap">
                    <span className="flex items-center gap-1.5 font-medium text-gray-800">
                      <MapPin className="w-3.5 h-3.5 text-primary" />
                      {activeBooking.centre?.name}
                    </span>
                    <span>Crop: <strong className="text-gray-950">{activeBooking.crop?.name}</strong> ({activeBooking.declared_quantity_q} Q)</span>
                    <span>Slot: <strong className="text-gray-950">{activeBooking.slot_date} {activeBooking.slot_start_time?.slice(0, 5)}</strong></span>
                  </div>
                </div>
              </div>
              <Link
                to="/farmer/bookings"
                className="btn-secondary text-xs px-3 py-1.5 self-end sm:self-auto flex items-center gap-1.5"
              >
                View Pass <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-5">
          {/* Procurement Timeline */}
          <div className="card p-5 md:p-6 md:col-span-2">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="section-title">{t('farmer.dashboard.timeline')}</h2>
                <p className="text-sm text-gray-500 mt-1">Live status of your crop procurement cycle</p>
              </div>
            </div>

            {timeline.length === 0 ? (
              <div className="text-center py-10 border border-dashed border-gray-200 rounded-xl">
                <Clock className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-400 text-sm">{t('common.noData')}</p>
                <Link to="/farmer/book-slot" className="btn-primary mt-3 text-xs inline-flex items-center gap-1">
                  <CalendarPlus className="w-3.5 h-3.5" /> {t('farmer.dashboard.bookNow')}
                </Link>
              </div>
            ) : (
              <ol className="relative border-l-2 border-gray-200 space-y-7 pl-7 ml-2 my-2">
                {timeline.map((event) => (
                  <li key={event.stage} className="relative">
                    {/* Circle icon */}
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
                        {event.label}
                      </p>
                      {event.detail && (
                        <p className="text-sm text-gray-600 mt-1">{event.detail}</p>
                      )}
                      {event.timestamp && (
                        <p className="text-sm text-gray-500 mt-1">
                          {new Date(event.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-5">
            {/* Queue Position Widget */}
            {myPosition ? (
              <div className="card p-5 border-primary-200 bg-primary-50/40">
                <h3 className="font-bold text-gray-900 text-base mb-4">{t('farmer.dashboard.queuePosition')}</h3>
                <div className="text-center">
                  <div className="text-5xl font-extrabold text-primary">#{myPosition.position}</div>
                  <p className="text-gray-700 text-sm font-semibold mt-2">
                    {t('queue.eta', { minutes: myPosition.estimated_wait_minutes })}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    {t('queue.ahead', { count: myPosition.ahead_of_you })}
                  </p>
                </div>
              </div>
            ) : (
              <div className="card p-5 border-dashed border-gray-300 text-center">
                <Clock className="w-6 h-6 text-gray-300 mx-auto mb-1.5" />
                <p className="text-gray-700 text-sm font-semibold">{t('farmer.dashboard.noBooking')}</p>
                <p className="text-sm text-gray-500 mt-1">Token position updates when you arrive at mandi gate</p>
              </div>
            )}

            {/* Quick Actions */}
            <div className="card p-5">
              <h3 className="font-bold text-gray-900 text-base mb-3">Quick Support</h3>
              <div className="space-y-1">
                {[
                  { to: '/farmer/grievances', label: 'Raise Grievance', icon: AlertCircle, color: 'text-rose-500', bg: 'bg-rose-50' },
                  { to: '/farmer/ivr', label: 'Toll-Free Helpline', icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                  { to: '/notifications', label: 'SMS & Alerts', icon: Bell, color: 'text-blue-500', bg: 'bg-blue-50' },
                ].map((action) => {
                  const Icon = action.icon
                  return (
                    <Link
                      key={action.to}
                      to={action.to}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-primary-50 group transition-colors"
                    >
                      <span className="flex items-center gap-3 text-sm font-semibold text-gray-800">
                        <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', action.bg)}>
                          <Icon className={clsx('w-4 h-4', action.color)} />
                        </div>
                        {action.label}
                      </span>
                      <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
                    </Link>
                  )
                })}
              </div>
            </div>
          </div>
        </div>

        {processTimings.length > 0 && (
          <div className="card p-5 md:p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-5">
              <div>
                <h2 className="section-title">Process Timing</h2>
                <p className="text-sm text-gray-500 mt-1">Measured time across your recent procurement cycles</p>
              </div>
              <span className="badge badge-blue">Last {processTimings.length} bookings</span>
            </div>
            <div className="overflow-x-auto">
              <table className="table min-w-[680px]">
                <thead>
                  <tr>
                    <th>Token</th><th>Gate wait</th><th>Processing start</th><th>Processing</th><th>Total cycle</th>
                  </tr>
                </thead>
                <tbody>
                  {processTimings.slice(0, 5).map((timing) => (
                    <tr key={timing.booking_id}>
                      <td>
                        <span className="font-mono font-semibold text-gray-900">{timing.token_number}</span>
                        <span className="block text-xs text-gray-500 mt-0.5">{timing.status}</span>
                      </td>
                      <td className="text-gray-700">{formatDuration(timing.booking_to_gate_minutes)}</td>
                      <td className="text-gray-700">{formatDuration(timing.gate_to_processing_minutes)}</td>
                      <td className="text-gray-700">{formatDuration(timing.processing_to_completion_minutes)}</td>
                      <td className="font-semibold text-primary">{formatDuration(timing.total_cycle_minutes)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Recent Transactions */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="section-title">{t('farmer.dashboard.recentTransactions')}</h2>
              <p className="text-xs text-gray-400 mt-0.5">Procurement transactions credited directly into your bank account</p>
            </div>
          </div>
          {transactions.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">{t('common.noData')}</p>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Crop</th><th>Amount</th><th>Payment Status</th><th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((txn) => (
                    <tr key={txn.id} className="hover:bg-gray-50/70 transition-colors">
                      <td className="font-semibold text-gray-900">{txn.crop_name || 'Wheat'}</td>
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
