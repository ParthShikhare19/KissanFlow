/** Mandi Staff — Queue Manager with real-time Socket.IO updates. */
import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { Users, ChevronRight, Clock, Loader2 } from 'lucide-react'
import { get, post } from '@/utils/api'
import { useQueueStore, type QueueEntry } from '@/stores/queueStore'
import { useSocket } from '@/hooks/useSocket'
import { useAuthStore } from '@/stores/authStore'
import clsx from 'clsx'

// Demo centre ID — in production this would come from the logged-in officer's centre
const DEMO_CENTRE_ID = ''  // Will be populated from first available centre

export default function QueueManager() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { centreQueue, setCentreQueue } = useQueueStore()
  const [centreId, setCentreId] = useState('')
  const [centres, setCentres] = useState<{ id: string; name: string }[]>([])
  const [calling, setCalling] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useSocket(centreId)

  useEffect(() => {
    get<{ id: string; name: string }[]>('/centres/').then((data) => {
      setCentres(data)
      if (data.length > 0) setCentreId(data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!centreId) return
    get<QueueEntry[]>(`/queue/${centreId}`).then(setCentreQueue)
  }, [centreId])

  // Timer for currently processing farmer
  useEffect(() => {
    const processing = centreQueue.find((e) => e.status === 'CALLED' || e.status === 'PROCESSING')
    if (processing) {
      setElapsedSeconds(0)
      timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [centreQueue.length])

  const handleCallNext = async () => {
    if (!centreId) return
    setCalling(true)
    try {
      await post('/queue/call-next', { centre_id: centreId })
      toast.success('Next farmer called!')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to call next'
      toast.error(msg)
    } finally {
      setCalling(false)
    }
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}m ${s % 60}s`

  const currentlyProcessing = centreQueue.find((e) => ['CALLED', 'PROCESSING'].includes(e.status))
  const waitingQueue = centreQueue.filter((e) => e.status === 'WAITING')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="page-title">{t('staff.queue.title')}</h1>
        {centres.length > 1 && (
          <select className="select w-auto" value={centreId} onChange={(e) => setCentreId(e.target.value)}>
            {centres.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
      </div>

      {/* Currently Processing Card */}
      {currentlyProcessing ? (
        <div className="card p-6 border-2 border-primary bg-primary-50 animate-fade-in">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-primary uppercase tracking-wider">{t('staff.queue.currentlyProcessing')}</p>
              <p className="text-2xl font-extrabold text-gray-900 mt-1">{currentlyProcessing.farmer_name || '—'}</p>
              <p className="font-mono text-lg text-primary mt-0.5">{currentlyProcessing.token_number}</p>
              <p className="text-sm text-gray-600 mt-1">{currentlyProcessing.crop_name} · {currentlyProcessing.declared_quantity_q}Q</p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-accent">{formatTime(elapsedSeconds)}</div>
              <p className="text-xs text-gray-500 mt-1">Time elapsed</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-6 border border-dashed border-gray-200 text-center">
          <p className="text-gray-400">{t('staff.queue.currentlyProcessing')}: —</p>
        </div>
      )}

      {/* Call Next Button */}
      <button
        onClick={handleCallNext}
        disabled={calling || waitingQueue.length === 0}
        className="btn-accent w-full text-base py-4 text-lg font-bold"
        id="call-next-btn"
      >
        {calling ? (
          <span className="flex items-center gap-2 justify-center">
            <Loader2 className="w-5 h-5 animate-spin" /> Calling...
          </span>
        ) : (
          <span className="flex items-center gap-2 justify-center">
            <Users className="w-5 h-5" />
            {t('staff.queue.callNext')} {waitingQueue.length > 0 ? `(${waitingQueue.length} waiting)` : ''}
          </span>
        )}
      </button>

      {/* Queue List */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="section-title">Waiting Queue</h2>
          <span className="badge badge-blue">{waitingQueue.length} waiting</span>
        </div>

        {waitingQueue.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-gray-400 font-medium">{t('staff.queue.empty')}</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {waitingQueue.map((entry, idx) => (
              <div key={entry.id} className="flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors">
                {/* Position */}
                <div className={clsx(
                  'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0',
                  idx === 0 ? 'bg-accent text-white' : 'bg-gray-100 text-gray-600'
                )}>
                  #{entry.position}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900 truncate">{entry.farmer_name || '—'}</p>
                    <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-600">{entry.token_number}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{entry.crop_name} · {entry.declared_quantity_q}Q</p>
                </div>

                {/* ETA */}
                <div className="flex items-center gap-1 text-xs text-gray-400 flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  ~{entry.estimated_wait_minutes}min
                </div>

                {/* Open Transaction */}
                <Link
                  to={`/staff/transaction/${entry.slot_booking_id}`}
                  className="btn-secondary text-xs px-3 py-1.5 flex-shrink-0"
                >
                  {t('staff.queue.openTransaction')}
                  <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
