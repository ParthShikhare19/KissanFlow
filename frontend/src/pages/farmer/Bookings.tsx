/** My Pass — the farmer's digital QR gate pass (route: /farmer/bookings). */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, Download, MapPin, RefreshCw, Ticket, Wheat } from 'lucide-react'
import { get } from '@/utils/api'
import { useAuthStore } from '@/stores/authStore'
import { CardSkeleton } from '@/components/LoadingSkeleton'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { speak } from '@/utils/speech'
import i18n from '@/i18n'
import clsx from 'clsx'

interface Booking {
  id: string; token_number: string; qr_code_base64?: string; slot_date: string
  slot_start_time: string; status: string; declared_quantity_q: number
  centre?: { name: string; district: string }; crop?: { name: string }
}

export default function Bookings() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [booking, setBooking] = useState<Booking | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    if (!user) return
    try {
      const data = await get<Booking | null>(`/farmers/${user.id}/bookings/latest`)
      setBooking(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [user])

  const downloadQR = () => {
    if (!booking?.qr_code_base64) return
    const link = document.createElement('a')
    link.href = `data:image/png;base64,${booking.qr_code_base64}`
    link.download = `kissanflow-qr-${booking.token_number}.png`
    link.click()
  }

  const statusKey = `status.${booking?.status}`
  const readAloud = () => {
    if (!booking) return
    const lang = (i18n.language === 'hi' ? 'hi' : 'en') as 'hi' | 'en'
    const text = lang === 'hi'
      ? `आपका टोकन नंबर ${booking.token_number}. मंडी ${booking.centre?.name}. तारीख ${booking.slot_date}, समय ${booking.slot_start_time?.slice(0, 5)}.`
      : `Your token number is ${booking.token_number}. Mandi ${booking.centre?.name}. Date ${booking.slot_date}, time ${booking.slot_start_time?.slice(0, 5)}.`
    speak(text, lang)
  }

  if (loading) return <CardSkeleton />

  if (!booking) {
    return (
      <div className="max-w-md mx-auto">
        <div className="card p-10 text-center">
          <Ticket className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <h1 className="text-lg font-bold text-gray-900">{t('pass.none.title')}</h1>
          <p className="text-sm text-gray-500 mt-1">{t('pass.none.subtitle')}</p>
          <Link to="/farmer/book-slot" className="btn-primary w-full mt-6 justify-center text-base py-3">
            {t('farmer.dashboard.bookNow')}
          </Link>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="max-w-md mx-auto space-y-5 animate-fade-in pb-12">
        <h1 className="page-title text-center">{t('pass.title')}</h1>

        {/* The pass card — big, icon-led, bilingual */}
        <div className="card p-6 border-2 border-primary-200 bg-primary-50/50 text-center">
          <span className={clsx(
            'badge text-xs font-bold',
            booking.status === 'COMPLETED' ? 'badge-green' : 'badge-blue'
          )}>
            {t(statusKey)}
          </span>

          {booking.qr_code_base64 && (
            <img
              src={`data:image/png;base64,${booking.qr_code_base64}`}
              alt="QR Pass"
              className="w-56 h-56 mx-auto my-5 rounded-xl border-4 border-white shadow-md bg-white p-2"
            />
          )}

          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">{t('farmer.dashboard.token')}</p>
          <p className="text-3xl font-extrabold font-mono text-primary mt-1">{booking.token_number}</p>

          <div className="mt-5 space-y-2.5 text-left">
            <div className="flex items-center gap-2.5 bg-white rounded-xl px-4 py-3 border border-gray-100">
              <MapPin className="w-5 h-5 text-primary flex-shrink-0" />
              <div>
                <p className="text-[11px] text-gray-400 font-bold uppercase">{t('pass.mandi')}</p>
                <p className="text-sm font-bold text-gray-900">{booking.centre?.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5 bg-white rounded-xl px-4 py-3 border border-gray-100">
              <Wheat className="w-5 h-5 text-amber-500 flex-shrink-0" />
              <div>
                <p className="text-[11px] text-gray-400 font-bold uppercase">{t('pass.cropSlot')}</p>
                <p className="text-sm font-bold text-gray-900">
                  {booking.crop?.name} · {booking.declared_quantity_q} Q
                </p>
                <p className="text-xs text-gray-500">
                  {booking.slot_date} · {booking.slot_start_time?.slice(0, 5)}
                </p>
              </div>
            </div>
          </div>

          {/* Listen button — reads the pass aloud */}
          <button
            onClick={readAloud}
            className="btn-secondary w-full mt-5 justify-center text-base py-3"
            id="pass-listen"
          >
            🔊 {t('pass.listen')}
          </button>
          <button onClick={downloadQR} className="btn-primary w-full mt-3 justify-center text-base py-3">
            <Download className="w-5 h-5" /> {t('pass.download')}
          </button>
        </div>

        <div className="flex gap-3">
          <button onClick={load} className="btn-secondary flex-1 justify-center py-3">
            <RefreshCw className="w-4 h-4" /> {t('common.retry')}
          </button>
          <Link to="/farmer/dashboard" className="btn-primary flex-1 justify-center py-3">
            {t('pass.backHome')} <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </ErrorBoundary>
  )
}
