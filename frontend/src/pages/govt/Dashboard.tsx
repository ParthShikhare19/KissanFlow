/** Government Admin Dashboard with drilldown map and anomaly flags. */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line
} from 'recharts'
import { TrendingUp, Users, Building, AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react'
import { get } from '@/utils/api'
import { PageSkeleton } from '@/components/LoadingSkeleton'

interface GovtDashboard {
  total_farmers: number; total_procurement_q: number; completed_q: number; pending_q: number
  active_mandis: number; high_congestion_count: number; quality_delay_count: number
  payment_delay_count: number; open_grievances: number
}

interface DrilldownRow {
  id?: string; name: string; total_farmers: number; procurement_q: number
  completed_pct: number; congestion_status: string
}

interface AnomalyFlag {
  centre_id: string; centre_name: string; district: string
  today_rejection_rate: number; rolling_avg_rate: number; severity: string; created_at: string
}

const PIE_COLORS = ['#22c55e', '#f59e0b', '#ef4444']

export default function GovtDashboard() {
  const { t } = useTranslation()
  const [dashboard, setDashboard] = useState<GovtDashboard | null>(null)
  const [drilldown, setDrilldown] = useState<DrilldownRow[]>([])
  const [anomalies, setAnomalies] = useState<AnomalyFlag[]>([])
  const [loading, setLoading] = useState(true)
  const [level, setLevel] = useState<'state' | 'district' | 'centre'>('state')
  const [parent, setParent] = useState<string | null>(null)
  const [breadcrumbs, setBreadcrumbs] = useState<string[]>([])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [dash, anomalyData] = await Promise.all([
          get<GovtDashboard>('/dashboard/govt/'),
          get<AnomalyFlag[]>('/dashboard/govt/anomalies'),
        ])
        setDashboard(dash)
        setAnomalies(anomalyData)
        await loadDrilldown('state', null)
      } catch { toast.error('Failed to load dashboard') }
      finally { setLoading(false) }
    }
    load()
  }, [])

  const loadDrilldown = async (lvl: string, par: string | null) => {
    try {
      const url = `/dashboard/govt/drilldown?level=${lvl}${par ? `&parent=${encodeURIComponent(par)}` : ''}`
      const data = await get<DrilldownRow[]>(url)
      setDrilldown(data)
    } catch { toast.error('Failed to load drilldown') }
  }

  const drillDown = (row: DrilldownRow) => {
    if (level === 'state') {
      setLevel('district')
      setParent(row.name)
      setBreadcrumbs([row.name])
      loadDrilldown('district', row.name)
    } else if (level === 'district') {
      setLevel('centre')
      setParent(row.name)
      setBreadcrumbs((b) => [...b, row.name])
      loadDrilldown('centre', row.name)
    }
  }

  const drillUp = (idx: number) => {
    if (idx === -1) {
      setLevel('state'); setParent(null); setBreadcrumbs([])
      loadDrilldown('state', null)
    } else {
      const newBreadcrumbs = breadcrumbs.slice(0, idx + 1)
      setParent(newBreadcrumbs[newBreadcrumbs.length - 1] || null)
      const newLevel = idx === 0 ? 'district' : 'centre'
      setLevel(newLevel as typeof level)
      setBreadcrumbs(newBreadcrumbs)
      loadDrilldown(newLevel, newBreadcrumbs[newBreadcrumbs.length - 1])
    }
  }

  if (loading) return <PageSkeleton />

  const procurementPieData = dashboard ? [
    { name: 'Completed', value: dashboard.completed_q },
    { name: 'Pending', value: dashboard.pending_q },
  ] : []

  const STAT_CARDS = [
    { label: 'Total Farmers', value: dashboard?.total_farmers.toLocaleString(), icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Total Procurement', value: `${dashboard?.total_procurement_q.toLocaleString()}Q`, icon: TrendingUp, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Active Mandis', value: dashboard?.active_mandis, icon: Building, color: 'text-violet-600', bg: 'bg-violet-50' },
    { label: 'Payment Delays', value: dashboard?.payment_delay_count, icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-50' },
    { label: 'Open Grievances', value: dashboard?.open_grievances, icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
    { label: 'Congestion Alerts', value: dashboard?.high_congestion_count, icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-50' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="page-title">{t('govt.dashboard.title')}</h1>

      {/* Stat Cards */}
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
            </div>
          )
        })}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Procurement Progress Pie */}
        <div className="card p-6">
          <h2 className="section-title mb-4">Procurement Completion</h2>
          {procurementPieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={procurementPieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>
                  {procurementPieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                </Pie>
                <Legend />
                <Tooltip formatter={(v: number) => `${v.toLocaleString()}Q`} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-center py-8">{t('common.noData')}</p>}
        </div>

        {/* Drilldown Table */}
        <div className="card overflow-hidden">
          <div className="p-4 border-b flex items-center gap-2 flex-wrap">
            <h2 className="section-title">{t('govt.dashboard.drilldown')}</h2>
            {/* Breadcrumbs */}
            <div className="flex items-center gap-1 text-sm">
              <button onClick={() => drillUp(-1)} className="text-primary hover:underline">India</button>
              {breadcrumbs.map((b, i) => (
                <React.Fragment key={i}>
                  <span className="text-gray-300">/</span>
                  <button onClick={() => drillUp(i)} className="text-primary hover:underline">{b}</button>
                </React.Fragment>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{level === 'state' ? 'State' : level === 'district' ? 'District' : 'Centre'}</th>
                  <th>Procurement (Q)</th>
                  <th>Completed %</th>
                </tr>
              </thead>
              <tbody>
                {drilldown.map((row) => (
                  <tr
                    key={row.name}
                    onClick={() => level !== 'centre' ? drillDown(row) : undefined}
                    className={level !== 'centre' ? 'cursor-pointer hover:bg-blue-50' : ''}
                  >
                    <td className="font-medium text-primary">{row.name}</td>
                    <td>{row.procurement_q.toLocaleString()}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-100 rounded-full h-2">
                          <div
                            className="h-2 rounded-full bg-primary"
                            style={{ width: `${Math.min(row.completed_pct, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600 w-12 text-right">{row.completed_pct}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Anomaly Flags */}
      {anomalies.length > 0 && (
        <div className="card overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="section-title">{t('govt.dashboard.anomalies')}</h2>
          </div>
          <div className="divide-y divide-gray-50">
            {anomalies.map((flag) => (
              <div key={flag.centre_id} className="p-4 flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">{flag.centre_name}</span>
                    <span className={`badge ${flag.severity === 'HIGH' ? 'badge-red' : 'badge-yellow'}`}>
                      {flag.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{flag.district}</p>
                </div>
                <button className="text-xs text-primary font-medium hover:underline">
                  Investigate
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
