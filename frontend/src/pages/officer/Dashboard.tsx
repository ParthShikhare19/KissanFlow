/** Mandi Officer Dashboard with stats, charts, alerts, and grievance management. */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertTriangle, CheckCircle, Clock, Users, TrendingUp, Bell } from 'lucide-react'
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

export default function OfficerDashboard() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [centreId, setCentreId] = useState('')
  const [centres, setCentres] = useState<Centre[]>([])
  const [dashboard, setDashboard] = useState<MandiDashboard | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useSocket(centreId)

  useEffect(() => {
    get<Centre[]>('/centres/').then((data) => {
      setCentres(data)
      if (data.length > 0) setCentreId(data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!centreId) return
    const load = async () => {
      setLoading(true)
      try {
        const [dash, alertsData] = await Promise.all([
          get<MandiDashboard>(`/dashboard/mandi/${centreId}`),
          get<Alert[]>(`/dashboard/mandi/${centreId}/alerts`),
        ])
        setDashboard(dash)
        setAlerts(alertsData)
      } catch { toast.error('Failed to load dashboard') }
      finally { setLoading(false) }
    }
    load()
  }, [centreId])

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await put(`/dashboard/mandi/${centreId}/alerts/${alertId}/acknowledge`)
      setAlerts((a) => a.filter((al) => al.id !== alertId))
      toast.success('Alert acknowledged')
    } catch { toast.error('Failed to acknowledge') }
  }

  if (loading) return <PageSkeleton />

  const STAT_CARDS = [
    { label: "Today's Bookings", value: dashboard?.total_bookings, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50', sub: `${dashboard?.daily_capacity} capacity` },
    { label: 'Queue Size', value: dashboard?.current_queue_size, icon: Clock, color: 'text-orange-600', bg: 'bg-orange-50', sub: `~${dashboard?.avg_processing_time_minutes}min/farmer` },
    { label: 'Completed', value: dashboard?.completed_count, icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50', sub: `of ${dashboard?.total_bookings}` },
    { label: 'Active Grievances', value: dashboard?.active_grievances_count, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50', sub: 'Needs attention' },
    { label: 'Payment Pending', value: dashboard?.payment_pending_count, icon: TrendingUp, color: 'text-violet-600', bg: 'bg-violet-50', sub: 'Ready to pay' },
    { label: 'Quality Pending', value: dashboard?.quality_pending_count, icon: Bell, color: 'text-yellow-600', bg: 'bg-yellow-50', sub: 'Awaiting check' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">{t('officer.dashboard.title')}</h1>
          <p className="text-gray-500 mt-1">{dashboard?.centre_name} · {dashboard?.date}</p>
        </div>
        {centres.length > 1 && (
          <select className="select w-auto" value={centreId} onChange={(e) => setCentreId(e.target.value)}>
            {centres.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
      </div>

      {/* Alerts Banner */}
      {alerts.length > 0 && (
        <div className="card p-4 border-l-4 border-red-500 bg-red-50">
          <p className="text-sm font-bold text-red-700 mb-2">⚠️ {alerts.length} Active Alert(s)</p>
          <div className="space-y-2">
            {alerts.slice(0, 3).map((alert) => (
              <div key={alert.id} className="flex items-start justify-between gap-3 text-sm">
                <p className="text-red-700 flex-1">{alert.message}</p>
                <button
                  onClick={() => acknowledgeAlert(alert.id)}
                  className="text-xs bg-white border border-red-200 text-red-600 px-3 py-1 rounded-lg hover:bg-red-50 flex-shrink-0"
                >
                  Dismiss
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {STAT_CARDS.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="stat-card">
              <div className="flex items-center justify-between mb-2">
                <p className="stat-label">{card.label}</p>
                <div className={`w-9 h-9 rounded-lg ${card.bg} flex items-center justify-center`}>
                  <Icon className={`w-4 h-4 ${card.color}`} />
                </div>
              </div>
              <p className="stat-value">{card.value ?? '—'}</p>
              <p className="text-xs text-gray-400 mt-1">{card.sub}</p>
            </div>
          )
        })}
      </div>

      {/* Hourly Throughput Chart */}
      <div className="card p-6">
        <h2 className="section-title mb-5">Hourly Processing Throughput</h2>
        {dashboard?.hourly_throughput?.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={dashboard.hourly_throughput} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
              />
              <Bar dataKey="processed" fill="#22c55e" radius={[4, 4, 0, 0]} name="Processed" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">{t('common.noData')}</p>
        )}
      </div>
    </div>
  )
}
