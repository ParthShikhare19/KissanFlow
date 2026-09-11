/** Mandi Officer Dashboard with stats, pending transactions, charts, and alerts. */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import {
  AlertTriangle, CheckCircle2, Clock, Users, TrendingUp,
  FileText, ArrowUpRight, ShieldCheck, Banknote, RefreshCw
} from 'lucide-react'
import { get, put } from '@/utils/api'
import { useAuthStore } from '@/stores/authStore'
import { useSocket } from '@/hooks/useSocket'
import { PageSkeleton } from '@/components/LoadingSkeleton'
import clsx from 'clsx'

interface MandiDashboard {
  centre_id: string; centre_name: string; date: string; daily_capacity: number
  total_bookings: number; arrived_count: number; completed_count: number
  current_queue_size: number; avg_processing_time_minutes: number
  quality_pending_count: number; payment_pending_count: number; active_grievances_count: number
  hourly_throughput: Array<{ hour: string; processed: number }>
}

interface Alert { id: string; type: string; message: string; severity: string; created_at: string; centre_name?: string }

interface Centre { id: string; name: string }

interface Transaction {
  id: string
  slot_booking_id: string
  farmer_name?: string
  crop_name?: string
  centre_name?: string
  gross_weight_q?: number
  tare_weight_q?: number
  net_weight_q?: number
  msp_per_q?: number
  total_amount?: number
  quality_status?: string
  procurement_status: string
  payment_status: string
  created_at: string
}

export default function OfficerDashboard() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [centreId, setCentreId] = useState('')
  const [centres, setCentres] = useState<Centre[]>([])
  const [dashboard, setDashboard] = useState<MandiDashboard | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useSocket(centreId)

  useEffect(() => {
    get<Centre[]>('/centres/').then((data) => {
      setCentres(data)
      if (data.length > 0) {
        const savedCentre = localStorage.getItem('kissanflow_officer_centre_id')
        const found = savedCentre && data.some((c) => c.id === savedCentre)
        if (found) {
          setCentreId(savedCentre!)
        } else {
          // Default to Ludhiana if present, or first centre
          const ludhiana = data.find((c) => c.name.toLowerCase().includes('ludhiana'))
          const chosen = ludhiana ? ludhiana.id : data[0].id
          setCentreId(chosen)
          localStorage.setItem('kissanflow_officer_centre_id', chosen)
        }
      }
    })
  }, [])

  const loadData = async (cId: string) => {
    if (!cId) return
    try {
      const [dash, alertsData, txnsData] = await Promise.all([
        get<MandiDashboard>(`/dashboard/mandi/${cId}`),
        get<Alert[]>(`/dashboard/mandi/${cId}/alerts`),
        get<Transaction[]>(`/transactions/centre/${cId}`).catch(() => [] as Transaction[]),
      ])
      setDashboard(dash)
      setAlerts(alertsData)
      setTransactions(txnsData || [])
    } catch {
      toast.error('Failed to load dashboard')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (centreId) {
      setLoading(true)
      loadData(centreId)
    }
  }, [centreId])

  const handleCentreChange = (newId: string) => {
    setCentreId(newId)
    localStorage.setItem('kissanflow_officer_centre_id', newId)
  }

  const handleRefresh = () => {
    setRefreshing(true)
    loadData(centreId)
  }

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await put(`/dashboard/mandi/${centreId}/alerts/${alertId}/acknowledge`)
      setAlerts((a) => a.filter((al) => al.id !== alertId))
      toast.success('Alert acknowledged')
    } catch {
      toast.error('Failed to acknowledge')
    }
  }

  if (loading) return <PageSkeleton />

  const STAT_CARDS = [
    {
      label: "Today's Bookings",
      value: dashboard?.total_bookings,
      icon: Users,
      color: 'text-blue-600',
      border: 'border-l-blue-500',
      bg: 'bg-blue-50',
      sub: `${dashboard?.daily_capacity} capacity`
    },
    {
      label: 'Queue Size',
      value: dashboard?.current_queue_size,
      icon: Clock,
      color: 'text-amber-600',
      border: 'border-l-amber-500',
      bg: 'bg-amber-50',
      sub: `~${dashboard?.avg_processing_time_minutes} min/farmer`
    },
    {
      label: 'Procurement Done',
      value: dashboard?.completed_count,
      icon: CheckCircle2,
      color: 'text-emerald-600',
      border: 'border-l-emerald-500',
      bg: 'bg-emerald-50',
      sub: `of ${dashboard?.total_bookings} arrived`
    },
    {
      label: 'Active Grievances',
      value: dashboard?.active_grievances_count,
      icon: AlertTriangle,
      color: 'text-rose-600',
      border: 'border-l-rose-500',
      bg: 'bg-rose-50',
      sub: 'Pending resolution'
    },
    {
      label: 'Payment Pending',
      value: dashboard?.payment_pending_count,
      icon: Banknote,
      color: 'text-indigo-600',
      border: 'border-l-indigo-500',
      bg: 'bg-indigo-50',
      sub: 'Ready for PFMS payout'
    },
    {
      label: 'Quality Checks Pending',
      value: dashboard?.quality_pending_count,
      icon: ShieldCheck,
      color: 'text-orange-600',
      border: 'border-l-orange-500',
      bg: 'bg-orange-50',
      sub: 'Awaiting lab grading'
    },
  ]

  // Filter transactions that need officer action
  const pendingTxns = transactions.filter(
    (t) => t.procurement_status !== 'CONFIRMED' || t.payment_status !== 'PAID'
  )

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title">{t('officer.dashboard.title')}</h1>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors"
              title="Refresh Dashboard"
            >
              <RefreshCw className={clsx('w-4 h-4', refreshing && 'animate-spin text-primary')} />
            </button>
          </div>
          <p className="text-gray-500 text-sm mt-1">
            {dashboard?.centre_name} &bull; {dashboard?.date}
          </p>
        </div>

        {centres.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Mandi:</span>
            <select
              className="select w-auto font-medium"
              value={centreId}
              onChange={(e) => handleCentreChange(e.target.value)}
            >
              {centres.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Alerts Banner */}
      {alerts.length > 0 && (
        <div className="card p-4 border-l-4 border-rose-500 bg-rose-50/70 shadow-xs">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            <p className="text-sm font-bold text-rose-800">
              {alerts.length} Active Mandi Alert{alerts.length > 1 ? 's' : ''}
            </p>
          </div>
          <div className="space-y-2">
            {alerts.slice(0, 3).map((alert) => (
              <div key={alert.id} className="flex items-start justify-between gap-3 text-sm bg-white/80 p-2.5 rounded-lg border border-rose-200">
                <p className="text-rose-900 flex-1 font-medium">{alert.message}</p>
                <button
                  onClick={() => acknowledgeAlert(alert.id)}
                  className="text-xs bg-white border border-rose-300 text-rose-700 px-2.5 py-1 rounded font-semibold hover:bg-rose-100 transition-colors flex-shrink-0"
                >
                  Dismiss
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats Grid with left-color borders */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {STAT_CARDS.map((card) => {
          const Icon = card.icon
          return (
            <div
              key={card.label}
              className={clsx(
                'card p-4.5 border-l-[4px] hover:shadow-md transition-shadow',
                card.border
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <p className="stat-label">{card.label}</p>
                <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center', card.bg)}>
                  <Icon className={clsx('w-4 h-4', card.color)} />
                </div>
              </div>
              <p className="stat-value">{card.value ?? '—'}</p>
              <p className="text-xs text-gray-400 mt-1">{card.sub}</p>
            </div>
          )
        })}
      </div>

      {/* Pending Transactions Section */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="section-title">Procurement Transactions</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Farmers currently at counters needing weighter, quality check, or payment release
            </p>
          </div>
          <Link
            to="/staff/queue"
            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
          >
            Live Queue View <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {transactions.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-gray-200 rounded-xl">
            <FileText className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-gray-500 font-medium text-sm">No transactions recorded for this centre yet.</p>
            <p className="text-xs text-gray-400 mt-1">Transactions will appear when staff begins processing arrivals.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Farmer</th>
                  <th>Crop</th>
                  <th>Net Weight</th>
                  <th>Amount</th>
                  <th>Quality</th>
                  <th>Status</th>
                  <th>Payment</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => {
                  const isReadyToConfirm = txn.net_weight_q && txn.quality_status && txn.procurement_status !== 'CONFIRMED'
                  const isReadyToPay = txn.procurement_status === 'CONFIRMED' && txn.payment_status !== 'PAID'

                  return (
                    <tr key={txn.id} className="hover:bg-gray-50/70 transition-colors">
                      <td className="font-semibold text-gray-900">
                        {txn.farmer_name || 'Farmer'}
                      </td>
                      <td className="text-gray-600">{txn.crop_name || 'Wheat'}</td>
                      <td>
                        {txn.net_weight_q ? `${txn.net_weight_q} Q` : (
                          <span className="text-xs text-gray-400 italic">Pending weighment</span>
                        )}
                      </td>
                      <td className="font-medium text-gray-900">
                        {txn.total_amount ? `₹${txn.total_amount.toLocaleString('en-IN')}` : '—'}
                      </td>
                      <td>
                        <span className={clsx('badge text-xs', {
                          'badge-green': txn.quality_status === 'ACCEPTED',
                          'badge-red': txn.quality_status === 'REJECTED',
                          'badge-yellow': txn.quality_status === 'CONDITIONAL',
                          'badge-gray': !txn.quality_status,
                        })}>
                          {txn.quality_status || 'Pending'}
                        </span>
                      </td>
                      <td>
                        <span className={clsx('badge text-xs', {
                          'badge-green': txn.procurement_status === 'CONFIRMED',
                          'badge-orange': txn.procurement_status === 'PENDING_CONFIRMATION',
                          'badge-blue': txn.procurement_status === 'DRAFT',
                          'badge-red': txn.procurement_status === 'CANCELLED',
                        })}>
                          {txn.procurement_status}
                        </span>
                      </td>
                      <td>
                        <span className={clsx('badge text-xs', {
                          'badge-green': txn.payment_status === 'PAID',
                          'badge-yellow': ['INITIATED', 'PROCESSING'].includes(txn.payment_status),
                          'badge-gray': txn.payment_status === 'NOT_INITIATED',
                          'badge-red': txn.payment_status === 'FAILED',
                        })}>
                          {txn.payment_status}
                        </span>
                      </td>
                      <td className="text-right">
                        <Link
                          to={`/staff/transaction/${txn.slot_booking_id}`}
                          className={clsx(
                            'inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all',
                            isReadyToConfirm
                              ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs'
                              : isReadyToPay
                              ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          )}
                        >
                          {isReadyToConfirm ? 'Confirm' : isReadyToPay ? 'Pay PFMS' : 'Open'}
                          <ArrowUpRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Hourly Throughput Area Chart */}
      <div className="card p-6">
        <h2 className="section-title mb-1">Hourly Processing Throughput</h2>
        <p className="text-xs text-gray-500 mb-5">Number of farmer trucks weighed and processed by hour</p>
        {dashboard?.hourly_throughput?.length ? (
          <ResponsiveContainer width="100%" height={230}>
            <AreaChart data={dashboard.hourly_throughput} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorProcessed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
              />
              <Area type="monotone" dataKey="processed" stroke="#16a34a" strokeWidth={2} fillOpacity={1} fill="url(#colorProcessed)" name="Processed" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">{t('common.noData')}</p>
        )}
      </div>
    </div>
  )
}
