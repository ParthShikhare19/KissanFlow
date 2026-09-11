/** Mandi Staff — Gate Entry with QR scanner and manual token input. */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { ScanLine, Keyboard, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { post, get } from '@/utils/api'
import clsx from 'clsx'

interface BookingInfo {
  id: string; token_number: string; status: string; declared_quantity_q: number
  slot_date: string; slot_start_time: string
  farmer?: { name: string; mobile: string }
  crop?: { name: string }; centre?: { name: string }
}

type TabMode = 'qr' | 'manual'

export default function GateEntry() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<TabMode>('manual')
  const [token, setToken] = useState('')
  const [booking, setBooking] = useState<BookingInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [marking, setMarking] = useState(false)

  // Initialize QR scanner when tab is qr
  useEffect(() => {
    if (tab !== 'qr') return
    let scanner: { render: (onSuccess: (text: string) => void, onError?: (error: string) => void) => void; clear: () => Promise<void> } | null = null

    const initScanner = async () => {
      try {
        const { Html5QrcodeScanner } = await import('html5-qrcode')
        scanner = new Html5QrcodeScanner('qr-reader', { fps: 10, qrbox: 250 }, false)
        scanner.render(
          (decodedText: string) => {
            try {
              const data = JSON.parse(decodedText)
              if (data.token) {
                setToken(data.token)
                lookupToken(data.token)
              }
            } catch {
              toast.error('Invalid QR code')
            }
          },
          () => {}
        )
      } catch (e) {
        console.error('QR scanner init failed:', e)
      }
    }
    initScanner()
    return () => {
      void scanner?.clear()
    }
  }, [tab])

  const lookupToken = async (t: string) => {
    setLoading(true)
    setBooking(null)
    try {
      const res = await get<BookingInfo>(`/bookings/token/${encodeURIComponent(t)}`)
      setBooking(res)
    } catch {
      toast.error('Token not found')
    } finally {
      setLoading(false)
    }
  }

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!token.trim()) { toast.error('Enter a token number'); return }
    lookupToken(token.trim().toUpperCase())
  }

  const markGateEntry = async () => {
    if (!booking) return
    setMarking(true)
    try {
      await post('/queue/gate-entry', { token_number: booking.token_number })
      toast.success('Gate entry marked! Farmer added to queue.')
      setBooking(null)
      setToken('')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to mark entry'
      toast.error(msg)
    } finally {
      setMarking(false)
    }
  }

  const getStatusInfo = (status: string) => {
    if (['BOOKED', 'ARRIVED'].includes(status)) {
      return { label: t('staff.gateEntry.valid'), color: 'bg-green-50 border-green-200', textColor: 'text-green-700', icon: CheckCircle, iconColor: 'text-green-600' }
    }
    if (['IN_QUEUE', 'PROCESSING', 'COMPLETED'].includes(status)) {
      return { label: t('staff.gateEntry.alreadyArrived'), color: 'bg-yellow-50 border-yellow-200', textColor: 'text-yellow-700', icon: AlertTriangle, iconColor: 'text-yellow-600' }
    }
    return { label: t('staff.gateEntry.invalid'), color: 'bg-red-50 border-red-200', textColor: 'text-red-700', icon: XCircle, iconColor: 'text-red-600' }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="page-title">{t('staff.gateEntry.title')}</h1>

      {/* Tab selector */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
        {(['qr', 'manual'] as TabMode[]).map((t_) => (
          <button
            key={t_}
            onClick={() => setTab(t_)}
            className={clsx(
              'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all',
              tab === t_ ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
            )}
            id={`tab-${t_}`}
          >
            {t_ === 'qr' ? <><ScanLine className="w-4 h-4" /> {t('staff.gateEntry.scan')}</> :
              <><Keyboard className="w-4 h-4" /> {t('staff.gateEntry.manual')}</>}
          </button>
        ))}
      </div>

      {/* QR Scanner */}
      {tab === 'qr' && (
        <div className="card p-6">
          <p className="text-sm text-gray-500 mb-4 text-center">Position the QR code within the frame</p>
          <div id="qr-reader" className="w-full" />
        </div>
      )}

      {/* Manual Entry */}
      {tab === 'manual' && (
        <div className="card p-6">
          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div>
              <label className="label">{t('staff.gateEntry.token')}</label>
              <div className="flex gap-3">
                <input
                  className="input flex-1 font-mono text-lg font-bold uppercase"
                  value={token}
                  onChange={(e) => setToken(e.target.value.toUpperCase())}
                  placeholder="WHT-00001"
                  id="gate-entry-token"
                />
                <button type="submit" disabled={loading} className="btn-primary px-6" id="gate-entry-submit">
                  {loading ? 'Checking...' : t('staff.gateEntry.submit')}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Farmer Card */}
      {booking && (() => {
        const info = getStatusInfo(booking.status)
        const Icon = info.icon
        const canEntry = ['BOOKED'].includes(booking.status)
        return (
          <div className={`card p-6 border-2 ${info.color} animate-fade-in`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Icon className={`w-8 h-8 ${info.iconColor}`} />
                <div>
                  <p className={`font-bold text-lg ${info.textColor}`}>{info.label}</p>
                  <p className="text-xs text-gray-500">Status: {booking.status}</p>
                </div>
              </div>
              <span className="font-mono font-bold text-lg text-gray-900">{booking.token_number}</span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                ['Farmer', booking.farmer?.name || '—'],
                ['Mobile', booking.farmer?.mobile ? `+91 ${booking.farmer.mobile}` : '—'],
                ['Crop', booking.crop?.name || '—'],
                ['Declared Qty', `${booking.declared_quantity_q} Q`],
                ['Slot', `${booking.slot_date} ${booking.slot_start_time?.slice(0, 5)}`],
                ['Mandi', booking.centre?.name || '—'],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className="text-gray-400 text-xs">{label}</p>
                  <p className="font-semibold text-gray-900">{value}</p>
                </div>
              ))}
            </div>
            {canEntry && (
              <button
                onClick={markGateEntry}
                disabled={marking}
                className="btn-primary w-full mt-5"
                id="mark-gate-entry"
              >
                <CheckCircle className="w-4 h-4" />
                {marking ? 'Marking...' : t('staff.gateEntry.markEntry')}
              </button>
            )}
          </div>
        )
      })()}
    </div>
  )
}
