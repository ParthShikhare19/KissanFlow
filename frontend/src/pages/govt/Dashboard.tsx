/** Government Admin Dashboard with drilldown map and anomaly flags. */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import {
  PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer
} from 'recharts'
import {
  TrendingUp, Users, Building, AlertTriangle, CheckCircle,
  AlertCircle, ChevronRight, ShieldAlert, FileText, ArrowRight
} from 'lucide-react'
import { get } from '@/utils/api'
import { PageSkeleton } from '@/components/LoadingSkeleton'
import clsx from 'clsx'

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
    {
      label: 'Registered Farmers',
      value: dashboard?.total_farmers.toLocaleString(),
      icon: Users,
      color: 'text-blue-600',
      border: 'border-l-blue-500',
      bg: 'bg-blue-50',
      sub: 'Verified Aadhaar & land'
    },
    {
      label: 'Total Procurement',
      value: `${dashboard?.total_procurement_q.toLocaleString()} Q`,
      icon: TrendingUp,
      color: 'text-emerald-600',
      border: 'border-l-emerald-500',
      bg: 'bg-emerald-50',
      sub: `${dashboard?.completed_q.toLocaleString()} Q cleared`
    },
    {
      label: 'Active Mandis',
      value: dashboard?.active_mandis,
      icon: Building,
      color: 'text-violet-600',
      border: 'border-l-violet-500',
      bg: 'bg-violet-50',
      sub: 'Procurement centers'
    },
    {
      label: 'Payment Delays',
      value: dashboard?.payment_delay_count,
      icon: AlertTriangle,
      color: dashboard?.payment_delay_count ? 'text-amber-600' : 'text-gray-500',
      border: dashboard?.payment_delay_count ? 'border-l-amber-500' : 'border-l-gray-300',
      bg: dashboard?.payment_delay_count ? 'bg-amber-50' : 'bg-gray-50',
      sub: '> 48h PFMS pending'
    },
    {
      label: 'Open Grievances',
      value: dashboard?.open_grievances,
      icon: AlertCircle,
      color: dashboard?.open_grievances ? 'text-rose-600' : 'text-gray-500',
      border: dashboard?.open_grievances ? 'border-l-rose-500' : 'border-l-gray-300',
      bg: dashboard?.open_grievances ? 'bg-rose-50' : 'bg-gray-50',
      sub: 'Awaiting officer action'
    },
    {
      label: 'Congestion Alerts',
      value: dashboard?.high_congestion_count,
      icon: ShieldAlert,
      color: dashboard?.high_congestion_count ? 'text-yellow-600' : 'text-gray-500',
      border: dashboard?.high_congestion_count ? 'border-l-yellow-500' : 'border-l-gray-300',
      bg: dashboard?.high_congestion_count ? 'bg-yellow-50' : 'bg-gray-50',
      sub: '> 85% centre capacity'
    },
  ]

  const todayStr = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  })

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="page-title">{t('govt.dashboard.title')}</h1>
          <p className="text-gray-500 text-sm mt-0.5">
            National Agricultural Procurement Oversight &bull; {todayStr}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Live Monitoring
          </span>
        </div>
      </div>

      {/* Stat Cards */}
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

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Procurement Progress Pie */}
        <div className="card p-6">
          <h2 className="section-title mb-1">Procurement Target Clearance</h2>
          <p className="text-xs text-gray-400 mb-4">Completed weighment & DBT disbursement vs pending pipeline</p>
          {procurementPieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={230}>
              <PieChart>
                <Pie
                  data={procurementPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                >
                  {procurementPieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip formatter={(v: number) => `${v.toLocaleString()} Q`} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-8">{t('common.noData')}</p>
          )}
        </div>

        {/* Drilldown Table */}
        <div className="card overflow-hidden">
          <div className="p-4 border-b flex items-center justify-between gap-2 flex-wrap bg-gray-50/50">
            <h2 className="section-title">{t('govt.dashboard.drilldown')}</h2>
            {/* Breadcrumbs */}
            <div className="flex items-center gap-1.5 text-xs font-semibold">
              <button
                onClick={() => drillUp(-1)}
                className={clsx(level === 'state' ? 'text-gray-900' : 'text-primary hover:underline')}
              >
                India
              </button>
              {breadcrumbs.map((b, i) => (
                <React.Fragment key={i}>
                  <span className="text-gray-300">/</span>
                  <button
                    onClick={() => drillUp(i)}
                    className={clsx(i === breadcrumbs.length - 1 ? 'text-gray-900' : 'text-primary hover:underline')}
                  >
                    {b}
                  </button>
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
                  {level !== 'centre' && <th className="text-right">View</th>}
                </tr>
              </thead>
              <tbody>
                {drilldown.map((row) => (
                  <tr
                    key={row.name}
                    onClick={() => (level !== 'centre' ? drillDown(row) : undefined)}
                    className={clsx(
                      'group transition-colors',
                      level !== 'centre' ? 'cursor-pointer hover:bg-emerald-50/60' : ''
                    )}
                  >
                    <td className="font-semibold text-gray-900 group-hover:text-primary transition-colors">
                      {row.name}
                    </td>
                    <td className="font-medium">{row.procurement_q.toLocaleString()} Q</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-100 rounded-full h-2 min-w-[60px]">
                          <div
                            className="h-2 rounded-full bg-primary transition-all duration-500"
                            style={{ width: `${Math.min(row.completed_pct, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-gray-600 w-10 text-right">
                          {row.completed_pct}%
                        </span>
                      </div>
                    </td>
                    {level !== 'centre' && (
                      <td className="text-right">
                        <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-primary group-hover:translate-x-0.5 transition-all inline" />
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Anomaly Flags */}
      {anomalies.length > 0 && (
        <div className="card overflow-hidden border-rose-200">
          <div className="p-4 border-b bg-rose-50/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-600" />
              <div>
                <h2 className="section-title text-rose-950">{t('govt.dashboard.anomalies')}</h2>
                <p className="text-xs text-rose-700 mt-0.5">
                  Centres where today's rejection rate exceeds 2x the 7-day rolling baseline
                </p>
              </div>
            </div>
            <span className="badge badge-red text-xs">{anomalies.length} Flagged</span>
          </div>
          <div className="divide-y divide-gray-100">
            {anomalies.map((flag) => (
              <div key={flag.centre_id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-rose-50/20 transition-colors">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900">{flag.centre_name}</span>
                    <span className={clsx('badge text-xs', flag.severity === 'HIGH' ? 'badge-red' : 'badge-yellow')}>
                      {flag.severity} RISK
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{flag.district}</p>

                  {/* Rejection comparison bar */}
                  <div className="flex items-center gap-3 text-xs text-gray-600 mt-2">
                    <span>
                      Today's Rejection: <strong className="text-rose-600 font-bold">{Math.round(flag.today_rejection_rate * 100)}%</strong>
                    </span>
                    <span className="text-gray-300">&bull;</span>
                    <span>
                      7-day Avg: <strong className="text-gray-700">{Math.round(flag.rolling_avg_rate * 100)}%</strong>
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toast(`Inspection report requested for ${flag.centre_name}`)}
                    className="btn-secondary text-xs px-3 py-1.5"
                  >
                    Request Audit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
