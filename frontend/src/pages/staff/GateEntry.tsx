/** Mandi Staff — Gate Entry with QR scanner and manual token input. */
import React, { useState, useEffect, useRef } from 'react'
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
  const { t: translator } = useTranslation()
  const t = translator as (key: string) => string
  const [tab, setTab] = useState<TabMode>('manual')
  const [token, setToken] = useState('')
  const [booking, setBooking] = useState<BookingInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [marking, setMarking] = useState(false)
  const [scannedCount, setScannedCount] = useState(() => {
    return parseInt(sessionStorage.getItem('kissanflow_scanned_today') || '0', 10)
  })
  const [justMarked, setJustMarked] = useState(false)
  const [scannerError, setScannerError] = useState<string | null>(null)
  const scannerRef = useRef<{ render: (onSuccess: (text: string) => void, onError?: (error: string) => void) => void; clear: () => Promise<void> } | null>(null)
  const lastDecodedTokenRef = useRef<string | null>(null)

  // Initialize QR scanner when tab is qr
  useEffect(() => {
    if (tab !== 'qr') return
    let disposed = false
    setScannerError(null)
    lastDecodedTokenRef.current = null

    const initScanner = async () => {
      try {
        const { Html5QrcodeScanner } = await import('html5-qrcode')
        if (disposed || scannerRef.current) return

        const scanner = new Html5QrcodeScanner(
          'qr-reader',
          {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            aspectRatio: 1,
            rememberLastUsedCamera: true,
          },
          false
        )
        scannerRef.current = scanner
        scanner.render(
          (decodedText: string) => {
            let decodedToken = decodedText.trim()
            try {
              const data = JSON.parse(decodedText) as { token?: string }
              decodedToken = data.token?.trim() || ''
            } catch {
              // Accept a plain token as well as the platform's JSON payload.
            }

            if (!decodedToken || lastDecodedTokenRef.current === decodedToken) return
            lastDecodedTokenRef.current = decodedToken
            setToken(decodedToken.toUpperCase())
            lookupToken(decodedToken)
          },
          (errorMessage: string) => {
            if (!disposed && !errorMessage.toLowerCase().includes('no qr code')) {
              setScannerError(translator('staff.gateEntry.cameraError'))
            }
          }
        )
      } catch (e) {
        console.error('QR scanner init failed:', e)
        if (!disposed) {
          setScannerError(translator('staff.gateEntry.cameraUnavailable'))
        }
      }
    }
    initScanner()
    return () => {
      disposed = true
      const scanner = scannerRef.current
      scannerRef.current = null
      if (scanner) {
        void scanner.clear().catch((error) => {
          console.warn('QR scanner cleanup failed:', error)
        })
      }
    }
  }, [tab])

  const lookupToken = async (tokenStr: string) => {
    setLoading(true)
    setBooking(null)
    try {
      const res = await get<BookingInfo>(`/bookings/token/${encodeURIComponent(tokenStr)}`)
      setBooking(res)
    } catch {
      toast.error(t('staff.gateEntry.notFound'))
    } finally {
      setLoading(false)
    }
  }

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!token.trim()) { toast.error(t('staff.gateEntry.enterToken')); return }
    lookupToken(token.trim().toUpperCase())
  }

  const markGateEntry = async () => {
    if (!booking) return
    setMarking(true)
    try {
      await post('/queue/gate-entry', { token_number: booking.token_number })
      toast.success(t('staff.gateEntry.marked'))
      setScannedCount((c) => {
        const next = c + 1
        sessionStorage.setItem('kissanflow_scanned_today', String(next))
        return next
      })
      setJustMarked(true)
      setTimeout(() => {
        setJustMarked(false)
        setBooking(null)
        setToken('')
      }, 1200)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t('staff.gateEntry.markFailed')
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">{t('staff.gateEntry.title')}</h1>
          <p className="text-xs text-gray-500 mt-0.5">{t('staff.gateEntry.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 px-3.5 py-1.5 rounded-xl shadow-xs">
          <CheckCircle className="w-4 h-4 text-emerald-600" />
          <span className="text-xs font-semibold text-emerald-800">
            {t('staff.gateEntry.admittedToday')}: <strong className="font-bold text-sm text-emerald-900">{scannedCount}</strong>
          </span>
        </div>
      </div>

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
          <p className="text-sm text-gray-500 mb-4 text-center">{t('staff.gateEntry.positionQr')}</p>
          <div id="qr-reader" className="w-full" />
          {scannerError && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {scannerError}
            </div>
          )}
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
                  {loading ? t('staff.gateEntry.checking') : t('staff.gateEntry.submit')}
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
        const canEntry = ['BOOKED', 'ARRIVED'].includes(booking.status)
        return (
          <div className={clsx(
            'card p-6 border-2 transition-all duration-300 animate-fade-in',
            justMarked ? 'bg-emerald-100 border-emerald-500 scale-[1.01]' : info.color
          )}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Icon className={`w-8 h-8 ${info.iconColor}`} />
                <div>
                  <p className={`font-bold text-lg ${info.textColor}`}>{info.label}</p>
                  <p className="text-xs text-gray-500">{t('staff.gateEntry.statusLabel')}: {booking.status}</p>
                </div>
              </div>
              <span className="font-mono font-bold text-lg text-gray-900">{booking.token_number}</span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                [t('staff.gateEntry.fieldFarmer'), booking.farmer?.name || '—'],
                [t('auth.login.mobile'), booking.farmer?.mobile ? `+91 ${booking.farmer.mobile}` : '—'],
                [t('booking.summary.crop'), booking.crop?.name || '—'],
                [t('booking.summary.quantity'), `${booking.declared_quantity_q} Q`],
                [t('booking.summary.slot'), `${booking.slot_date} ${booking.slot_start_time?.slice(0, 5)}`],
                [t('booking.summary.mandi'), booking.centre?.name || '—'],
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
                disabled={marking || justMarked}
                className="btn-primary w-full mt-5"
                id="mark-gate-entry"
              >
                <CheckCircle className="w-4 h-4" />
                {justMarked ? t('staff.gateEntry.admitted') : marking ? t('staff.gateEntry.marking') : t('staff.gateEntry.markEntry')}
              </button>
            )}
          </div>
        )
      })()}
    </div>
  )
}
