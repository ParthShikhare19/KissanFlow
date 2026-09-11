/** Farmer grievances page — list and raise grievances. */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { Plus, X, AlertCircle } from 'lucide-react'
import { get, post } from '@/utils/api'
import { useAuthStore } from '@/stores/authStore'
import { CardSkeleton } from '@/components/LoadingSkeleton'
import clsx from 'clsx'

interface Grievance {
  id: string; category: string; description: string; status: string
  created_at: string; resolved_at?: string; resolution?: string; farmer_name?: string
}

const CATEGORIES = [
  'SLOT_ISSUE', 'EXCESSIVE_WAIT', 'QUALITY_DISPUTE', 'WEIGHMENT_DISPUTE', 'PAYMENT_ISSUE', 'OTHER'
]

const STATUS_BADGES: Record<string, string> = {
  OPEN: 'badge-red', UNDER_REVIEW: 'badge-yellow', RESOLVED: 'badge-green', CLOSED: 'badge-gray'
}

export default function Grievances() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [grievances, setGrievances] = useState<Grievance[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [selected, setSelected] = useState<Grievance | null>(null)
  const [form, setForm] = useState({ category: 'SLOT_ISSUE', description: '' })
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    if (!user) return
    try {
      const res = await get<{ items: Grievance[] }>(`/farmers/${user.id}/grievances`)
      setGrievances(res.items)
    } catch { toast.error('Failed to load grievances') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [user])

  const handleSubmit = async () => {
    if (!form.description.trim()) { toast.error('Please describe your grievance'); return }
    setSubmitting(true)
    try {
      await post('/grievances/', { category: form.category, description: form.description })
      toast.success('Grievance raised successfully!')
      setShowModal(false)
      setForm({ category: 'SLOT_ISSUE', description: '' })
      load()
    } catch { toast.error('Failed to raise grievance') }
    finally { setSubmitting(false) }
  }

  if (loading) return <div className="space-y-4"><CardSkeleton /><CardSkeleton /></div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="page-title">{t('grievance.title')}</h1>
        <button onClick={() => setShowModal(true)} className="btn-primary" id="raise-grievance-btn">
          <Plus className="w-4 h-4" /> {t('grievance.raise')}
        </button>
      </div>

      {/* Grievance List */}
      {grievances.length === 0 ? (
        <div className="card p-12 text-center">
          <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No grievances raised yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {grievances.map((g) => (
            <div
              key={g.id}
              onClick={() => setSelected(g)}
              className="card p-5 cursor-pointer hover:shadow-card-hover transition-shadow"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-xs font-mono text-gray-400">GRV-{g.id.slice(0, 8).toUpperCase()}</span>
                    <span className="badge badge-blue">{t(`grievance.category.${g.category}`)}</span>
                    <span className={`badge ${STATUS_BADGES[g.status]}`}>{t(`grievance.status.${g.status}`)}</span>
                  </div>
                  <p className="text-sm text-gray-700 mt-2 line-clamp-2">{g.description}</p>
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {new Date(g.created_at).toLocaleDateString('en-IN')}
                </span>
              </div>
              {g.resolution && (
                <div className="mt-3 p-2 bg-green-50 rounded text-xs text-green-700">
                  ✓ {g.resolution}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Raise Grievance Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl animate-fade-in">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="font-bold text-gray-900">{t('grievance.raise')}</h2>
              <button onClick={() => setShowModal(false)} className="p-1 rounded hover:bg-gray-100">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="label">{t('grievance.category')}</label>
                <select className="select" value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))} id="grievance-category">
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{t(`grievance.category.${c}`)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">{t('grievance.description')}</label>
                <textarea
                  className="input min-h-[120px] resize-none"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Describe your issue in detail..."
                  id="grievance-description"
                />
              </div>
            </div>
            <div className="flex gap-3 p-6 border-t">
              <button onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={handleSubmit} disabled={submitting} className="btn-primary flex-1" id="grievance-submit">
                {submitting ? 'Submitting...' : 'Submit Grievance'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl animate-fade-in">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="font-bold text-gray-900">Grievance Detail</h2>
              <button onClick={() => setSelected(null)} className="p-1 rounded hover:bg-gray-100">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex gap-2 flex-wrap">
                <span className="badge badge-blue">{t(`grievance.category.${selected.category}`)}</span>
                <span className={`badge ${STATUS_BADGES[selected.status]}`}>{t(`grievance.status.${selected.status}`)}</span>
              </div>
              <p className="text-sm text-gray-700">{selected.description}</p>
              {selected.resolution && (
                <div className="p-3 bg-green-50 rounded-lg border border-green-100">
                  <p className="text-xs font-semibold text-green-800 mb-1">Resolution</p>
                  <p className="text-sm text-green-700">{selected.resolution}</p>
                  {selected.resolved_at && (
                    <p className="text-xs text-green-500 mt-1">
                      Resolved on {new Date(selected.resolved_at).toLocaleDateString('en-IN')}
                    </p>
                  )}
                </div>
              )}
              <p className="text-xs text-gray-400">
                Raised on {new Date(selected.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
