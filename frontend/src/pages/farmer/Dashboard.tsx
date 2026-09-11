/** Farmer Dashboard — timeline, active booking, queue position, recent transactions. */
import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CalendarPlus, CheckCircle, Clock, AlertCircle, ChevronRight } from 'lucide-react'
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
  id: string; total_amount?: number; payment_status: string; crop_name?: string; created_at: string
}


export default function FarmerDashboard() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { myPosition, isYourTurn } = useQueueStore()
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [activeBooking, setActiveBooking] = useState<Booking | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  // Connect socket with farmer room for active booking
  useSocket(undefined, activeBooking?.id)

  useEffect(() => {
    if (!user) return
    const load = async () => {
      try {
        // Load timeline
        const tl = await get<TimelineEvent[]>(`/farmers/${user.id}/timeline`)
        setTimeline(tl)

        const txns = await get<{ items: Transaction[] }>(`/farmers/${user.id}/transactions?page=1&page_size=3`)
        setTransactions(txns.items)

        const latestBooking = await get<Booking | null>(`/farmers/${user.id}/bookings/latest`)
        setActiveBooking(latestBooking)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user])

  if (loading) return (
    <div className="space-y-6">
      <CardSkeleton />
      <div className="grid md:grid-cols-2 gap-6">
        <CardSkeleton /><CardSkeleton />
      </div>
    </div>
  )

  const statusColors: Record<string, string> = {
    BOOKED: 'badge-blue', ARRIVED: 'badge-yellow', IN_QUEUE: 'badge-yellow',
    PROCESSING: 'badge-orange', COMPLETED: 'badge-green', CANCELLED: 'badge-red',
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">{t('farmer.dashboard.title')}</h1>
            <p className="text-gray-500 mt-1">ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ, {user?.name?.split(' ')[0]}!</p>
          </div>
          <Link to="/farmer/book-slot" className="btn-primary">
            <CalendarPlus className="w-4 h-4" />
            {t('farmer.dashboard.bookNow')}
          </Link>
        </div>

        {/* Your Turn Alert */}
        {isYourTurn && (
          <div className="card p-4 border-2 border-primary bg-primary-50 flex items-center gap-3 animate-fade-in">
            <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center animate-ping-slow">
              <span className="text-white text-lg">🔔</span>
            </div>
            <div>
              <p className="font-bold text-primary text-lg">{t('farmer.dashboard.yourTurn')}</p>
              <p className="text-primary-dark text-sm">Please proceed to the processing counter immediately.</p>
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-6">
          {/* Procurement Timeline */}
          <div className="card p-6 md:col-span-2">
            <h2 className="section-title mb-5">{t('farmer.dashboard.timeline')}</h2>
            {timeline.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-400">{t('common.noData')}</p>
                <Link to="/farmer/book-slot" className="btn-primary mt-3 text-sm">
                  {t('farmer.dashboard.bookNow')}
                </Link>
              </div>
            ) : (
              <ol className="relative border-l border-gray-200 space-y-5 pl-6">
                {timeline.map((event) => (
                  <li key={event.stage} className="relative">
                    {/* Dot */}
                    <span className={clsx(
                      'absolute -left-3.5 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 border-white',
                      event.status === 'completed' ? 'bg-primary text-white' :
                      event.status === 'active' ? 'bg-accent text-white animate-pulse' :
                      'bg-gray-100 text-gray-400'
                    )}>
                      {event.status === 'completed' ? '✓' :
                       event.status === 'active' ? '●' : '○'}
                    </span>
                    <div className="ml-2">
                      <p className={clsx(
                        'text-sm font-semibold',
                        event.status === 'completed' ? 'text-gray-900' :
                        event.status === 'active' ? 'text-accent-dark' : 'text-gray-400'
                      )}>
                        {event.label}
                      </p>
                      {event.detail && (
                        <p className="text-xs text-gray-500 mt-0.5">{event.detail}</p>
                      )}
                      {event.timestamp && (
                        <p className="text-xs text-gray-400">
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
              <div className="card p-5 border-2 border-primary-100">
                <h3 className="font-bold text-gray-800 text-sm mb-3">{t('farmer.dashboard.queuePosition')}</h3>
                <div className="text-center">
                  <div className="text-5xl font-extrabold text-primary">#{myPosition.position}</div>
                  <p className="text-gray-500 text-sm mt-1">
                    {t('queue.eta', { minutes: myPosition.estimated_wait_minutes })}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {t('queue.ahead', { count: myPosition.ahead_of_you })}
                  </p>
                </div>
              </div>
            ) : (
              <div className="card p-5 border border-dashed border-gray-200">
                <p className="text-gray-400 text-sm text-center">{t('farmer.dashboard.noBooking')}</p>
              </div>
            )}

            {/* Quick Actions */}
            <div className="card p-4">
              <h3 className="font-bold text-gray-800 text-sm mb-3">Quick Actions</h3>
              <div className="space-y-2">
                {[
                  { to: '/farmer/grievances', label: 'Raise Grievance', icon: AlertCircle, color: 'text-red-500' },
                  { to: '/notifications', label: 'Notifications', icon: Clock, color: 'text-blue-500' },
                ].map((action) => {
                  const Icon = action.icon
                  return (
                    <Link
                      key={action.to}
                      to={action.to}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 group transition-colors"
                    >
                      <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
                        <Icon className={`w-4 h-4 ${action.color}`} />
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

        {/* Recent Transactions */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">{t('farmer.dashboard.recentTransactions')}</h2>
          </div>
          {transactions.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-4">{t('common.noData')}</p>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Crop</th><th>Amount</th><th>Payment</th><th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((txn) => (
                    <tr key={txn.id}>
                      <td className="font-medium">{txn.crop_name || '—'}</td>
                      <td>{txn.total_amount ? `₹${txn.total_amount.toLocaleString('en-IN')}` : '—'}</td>
                      <td>
                        <span className={clsx('badge', {
                          'badge-green': txn.payment_status === 'PAID',
                          'badge-yellow': ['INITIATED', 'PROCESSING'].includes(txn.payment_status),
                          'badge-gray': txn.payment_status === 'NOT_INITIATED',
                          'badge-red': txn.payment_status === 'FAILED',
                        })}>
                          {t(`payment.${txn.payment_status}`)}
                        </span>
                      </td>
                      <td className="text-gray-400">
                        {new Date(txn.created_at).toLocaleDateString('en-IN')}
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
