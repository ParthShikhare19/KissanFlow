/** 6-step slot booking wizard — simplified for low-literacy users:
 *  emoji crop cards with bilingual names, tap-to-pick quantities. */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { CheckCircle, ChevronLeft, ChevronRight, Loader2, Download, Smartphone } from 'lucide-react'
import { get, post } from '@/utils/api'
import { speak } from '@/utils/speech'
import i18n from '@/i18n'
import clsx from 'clsx'

interface Crop { id: string; name: string; season: string; msp_per_quintal: number; crop_code: string }
interface Centre { id: string; name: string; district: string; state: string; daily_capacity: number }
interface SlotInfo { start_time: string; end_time: string; booked: number; capacity: number; available: number; availability_pct: number }
interface BookingResult { id: string; token_number: string; slot_date: string; slot_start_time: string; qr_code_base64?: string; centre?: { name: string }; crop?: { name: string } }

const STEP_LABELS = [
  'booking.step1.title', 'booking.step2.title', 'booking.step3.title',
  'booking.step4.title', 'booking.step5.title', 'booking.step6.title',
]

// crop_code → emoji + translated name key
const CROP_META: Record<string, { emoji: string }> = {
  WHT: { emoji: '🌾' }, RIC: { emoji: '🌾' }, MAZ: { emoji: '🌽' },
  MST: { emoji: '🌱' }, SOY: { emoji: '🫘' }, COT: { emoji: '☁️' },
}

const QUICK_QUANTITIES = [5, 10, 25, 50, 100]

export default function BookSlot() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [crops, setCrops] = useState<Crop[]>([])
  const [centres, setCentres] = useState<Centre[]>([])
  const [slots, setSlots] = useState<SlotInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [booking, setBooking] = useState<BookingResult | null>(null)

  const [selectedCrop, setSelectedCrop] = useState<Crop | null>(null)
  const [quantity, setQuantity] = useState('')
  const [selectedCentre, setSelectedCentre] = useState<Centre | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedSlot, setSelectedSlot] = useState<SlotInfo | null>(null)

  useEffect(() => {
    get<Crop[]>('/crops/').then(setCrops).catch(console.error)
    get<Centre[]>('/centres/').then(setCentres).catch(console.error)
  }, [])

  useEffect(() => {
    if (selectedCentre && selectedDate) {
      get<SlotInfo[]>(`/centres/${selectedCentre.id}/slots?date=${selectedDate}`)
        .then(setSlots).catch(console.error)
    }
  }, [selectedCentre, selectedDate])

  const handleNext = () => {
    if (step === 0 && !selectedCrop) { toast.error(t('booking.error.crop')); return }
    if (step === 1) {
      const q = parseFloat(quantity)
      if (!q || q < 1 || q > 500) { toast.error(t('booking.error.quantity')); return }
    }
    if (step === 2 && !selectedCentre) { toast.error(t('booking.error.centre')); return }
    if (step === 3 && !selectedDate) { toast.error(t('booking.error.date')); return }
    if (step === 4 && !selectedSlot) { toast.error(t('booking.error.slot')); return }
    setStep((s) => s + 1)
  }

  const handleConfirm = async () => {
    setLoading(true)
    try {
      const result = await post<BookingResult>('/bookings/', {
        centre_id: selectedCentre!.id,
        crop_id: selectedCrop!.id,
        preferred_date: selectedDate,
        declared_quantity_q: parseFloat(quantity),
        preferred_slot_start_time: selectedSlot!.start_time,
      })
      setBooking(result)
      setStep(6) // success step
      toast.success(t('booking.success.toast'))
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t('booking.error.failed')
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const downloadQR = () => {
    if (!booking?.qr_code_base64) return
    const link = document.createElement('a')
    link.href = `data:image/png;base64,${booking.qr_code_base64}`
    link.download = `kissanflow-qr-${booking.token_number}.png`
    link.click()
  }

  // Calendar helpers
  const getDatesForMonth = () => {
    const today = new Date()
    const dates: string[] = []
    for (let i = 0; i < 30; i++) {
      const d = new Date(today)
      d.setDate(today.getDate() + i)
      dates.push(d.toISOString().split('T')[0])
    }
    return dates
  }

  // Read the success screen aloud for farmers who can't read the QR card.
  const readBookingAloud = () => {
    if (!booking) return
    const lang: 'hi' | 'en' = i18n.language === 'hi' ? 'hi' : 'en'
    const text = lang === 'hi'
      ? `बुकिंग हो गई। टोकन नंबर ${booking.token_number}. मंडी ${booking.centre?.name}. तारीख ${booking.slot_date}, समय ${booking.slot_start_time?.slice(0, 5)}.`
      : `Booking done. Token number ${booking.token_number}. Mandi ${booking.centre?.name}. Date ${booking.slot_date}, time ${booking.slot_start_time?.slice(0, 5)}.`
    speak(text, lang)
  }

  const cropName = (crop: Crop) => t(`crop.name.${crop.crop_code}`, { defaultValue: crop.name })

  if (step === 6 && booking) {
    return (
      <div className="max-w-md mx-auto text-center py-8">
        <div className="card p-8">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">{t('booking.success.title')}</h2>
          <p className="text-gray-500 text-sm mb-6">{t('booking.success.subtitle')}</p>
          <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <p className="text-xs text-gray-400 mb-1">{t('booking.success.token')}</p>
            <p className="text-3xl font-extrabold font-mono text-primary">{booking.token_number}</p>
            <p className="text-xs text-gray-500 mt-2">
              {booking.centre?.name} &bull; {booking.slot_date} {t('booking.success.at')} {booking.slot_start_time?.slice(0, 5)}
            </p>
          </div>
          {booking.qr_code_base64 && (
            <div className="mb-6">
              <img
                src={`data:image/png;base64,${booking.qr_code_base64}`}
                alt="Booking QR Code"
                className="w-44 h-44 mx-auto rounded-xl border border-gray-200 p-2 shadow-xs"
              />
              <button onClick={readBookingAloud} className="btn-secondary mt-3 w-full justify-center text-base py-3">
                🔊 {t('pass.listen')}
              </button>
              <button onClick={downloadQR} className="btn-secondary mt-3 w-full">
                <Download className="w-4 h-4" /> {t('booking.success.download')}
              </button>
            </div>
          )}
          {/* SMS simulation */}
          <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-100 text-xs text-green-700 text-left flex items-start gap-2">
            <Smartphone className="w-4 h-4 text-green-700 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">{t('booking.success.sms', { mobile: 'XXXXXXXX' })}</span>
            </div>
          </div>
          <button onClick={() => navigate('/farmer/dashboard')} className="btn-primary w-full mt-5 text-base py-3">
            {t('booking.success.goDashboard')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress bar */}
      <div className="mb-8">
        <h1 className="page-title mb-4">{t('booking.title')}</h1>
        <div className="flex items-center gap-1">
          {STEP_LABELS.map((_, i) => (
            <div
              key={i}
              className={clsx('h-2 flex-1 rounded-full transition-all', i <= step ? 'bg-primary' : 'bg-gray-200')}
            />
          ))}
        </div>
        <p className="text-sm text-gray-600 font-medium mt-2">{t(STEP_LABELS[step])} ({step + 1}/6)</p>
      </div>

      <div className="card p-6">
        {/* Step 1: Select Crop — emoji cards with bilingual names */}
        {step === 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 animate-fade-in">
            {crops.map((crop) => (
              <button
                key={crop.id}
                onClick={() => setSelectedCrop(crop)}
                className={clsx(
                  'flex flex-col items-center justify-center p-5 rounded-2xl border-2 transition-all min-h-[120px]',
                  selectedCrop?.id === crop.id ? 'border-primary bg-primary-50 shadow-sm' : 'border-gray-100 hover:border-gray-300'
                )}
              >
                <span className="text-4xl" aria-hidden>{CROP_META[crop.crop_code]?.emoji || '🌿'}</span>
                <span className="font-bold text-gray-900 mt-2">{cropName(crop)}</span>
                <span className="text-[11px] text-gray-400 font-mono">{crop.crop_code}</span>
                <span className="text-xs font-bold text-primary mt-1">{t('booking.msp', { amount: crop.msp_per_quintal.toLocaleString('en-IN') })}</span>
              </button>
            ))}
          </div>
        )}

        {/* Step 2: Quantity — quick-pick buttons + free input */}
        {step === 1 && (
          <div className="animate-fade-in space-y-4">
            <div className="p-4 bg-primary-50 rounded-xl flex items-center gap-3">
              <span className="text-3xl" aria-hidden>{CROP_META[selectedCrop?.crop_code || '']?.emoji || '🌿'}</span>
              <p className="text-sm text-primary font-semibold">
                {cropName(selectedCrop!)} · MSP ₹{selectedCrop?.msp_per_quintal}/Q
              </p>
            </div>
            <label className="label">{t('booking.quantity.label')}</label>
            <div className="grid grid-cols-5 gap-2">
              {QUICK_QUANTITIES.map((q) => (
                <button
                  key={q}
                  onClick={() => setQuantity(String(q))}
                  className={clsx(
                    'py-4 rounded-xl border-2 text-lg font-extrabold transition-all',
                    quantity === String(q) ? 'border-primary bg-primary text-white' : 'border-gray-200 bg-gray-50 text-gray-800 hover:border-primary-300'
                  )}
                >
                  {q}
                </button>
              ))}
            </div>
            <div className="relative">
              <input
                type="number"
                min="1"
                max="500"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="input text-2xl font-bold pr-20"
                placeholder="25"
                id="booking-quantity"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-medium">{t('booking.quantity.unit')}</span>
            </div>
            {quantity && parseFloat(quantity) > 0 && (
              <div className="p-4 bg-green-50 rounded-xl border border-green-100">
                <p className="text-sm text-green-700 font-medium">
                  {t('booking.estimated')}: <span className="text-xl font-bold">₹{(parseFloat(quantity) * (selectedCrop?.msp_per_quintal || 0)).toLocaleString('en-IN')}</span>
                </p>
              </div>
            )}
            <p className="text-xs text-gray-400">{t('booking.quantity.min')} · {t('booking.quantity.max')}</p>
          </div>
        )}

        {/* Step 3: Select Mandi */}
        {step === 2 && (
          <div className="space-y-3 animate-fade-in">
            {centres.map((centre) => (
              <button
                key={centre.id}
                onClick={() => setSelectedCentre(centre)}
                className={clsx(
                  'w-full flex items-center justify-between p-4 rounded-xl border-2 transition-all',
                  selectedCentre?.id === centre.id ? 'border-primary bg-primary-50' : 'border-gray-100 hover:border-gray-300'
                )}
              >
                <div className="text-left">
                  <p className="font-semibold text-gray-900">{centre.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{centre.district}, {centre.state}</p>
                </div>
                <div>
                  <span className="badge-green text-xs px-3 py-1 rounded-full bg-green-100 text-green-800 font-medium">
                    {t('booking.capacityPerDay', { count: centre.daily_capacity })}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Step 4: Select Date */}
        {step === 3 && (
          <div className="animate-fade-in">
            <div className="grid grid-cols-7 gap-2">
              {getDatesForMonth().map((d) => {
                const dateObj = new Date(d)
                const dayName = dateObj.toLocaleDateString(i18n.language, { weekday: 'short' })
                const dayNum = dateObj.getDate()
                return (
                  <button
                    key={d}
                    onClick={() => setSelectedDate(d)}
                    className={clsx(
                      'flex flex-col items-center p-2 rounded-lg text-xs font-medium transition-all',
                      selectedDate === d ? 'bg-primary text-white shadow-sm' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                    )}
                  >
                    <span className="opacity-70">{dayName}</span>
                    <span className="text-lg font-bold">{dayNum}</span>
                  </button>
                )
              })}
            </div>
            {selectedDate && <p className="text-sm text-primary font-medium mt-4">{t('booking.selectedDate')}: {new Date(selectedDate).toLocaleDateString(i18n.language, { weekday: 'long', day: 'numeric', month: 'long' })}</p>}
          </div>
        )}

        {/* Step 5: Select Time Slot */}
        {step === 4 && (
          <div className="animate-fade-in">
            <p className="text-sm text-gray-500 mb-4">{selectedDate} · {selectedCentre?.name}</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {slots.map((slot) => {
                const isFull = slot.available === 0
                const isAlmostFull = slot.availability_pct < 30
                return (
                  <button
                    key={slot.start_time}
                    disabled={isFull}
                    onClick={() => setSelectedSlot(slot)}
                    className={clsx(
                      'p-3 rounded-xl border-2 text-sm font-medium transition-all',
                      isFull ? 'border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed' :
                      selectedSlot?.start_time === slot.start_time ? 'border-primary bg-primary text-white' :
                      isAlmostFull ? 'border-yellow-300 bg-yellow-50 text-yellow-800 hover:border-yellow-400' :
                      'border-green-200 bg-green-50 text-green-800 hover:border-green-400'
                    )}
                  >
                    <div className="font-bold">{slot.start_time} – {slot.end_time}</div>
                    <div className="text-xs mt-1 opacity-80">
                      {isFull ? t('booking.slot.full') :
                       isAlmostFull ? t('booking.slot.almostFull') :
                       t('booking.slot.available')} ({slot.available}/{slot.capacity})
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Step 6: Confirm */}
        {step === 5 && (
          <div className="animate-fade-in space-y-4">
            <h3 className="text-base font-bold text-gray-900">{t('booking.summary.title')}</h3>
            <div className="bg-gray-50 rounded-xl p-5 space-y-3 text-sm">
              {[
                [t('booking.summary.crop'), `${cropName(selectedCrop!)} (${selectedCrop?.crop_code})`],
                [t('booking.summary.quantity'), `${quantity} ${t('booking.quantity.unit')}`],
                [t('booking.summary.mandi'), selectedCentre?.name || ''],
                [t('booking.summary.location'), `${selectedCentre?.district}, ${selectedCentre?.state}`],
                [t('booking.summary.date'), new Date(selectedDate).toLocaleDateString(i18n.language, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })],
                [t('booking.summary.slot'), `${selectedSlot?.start_time} – ${selectedSlot?.end_time}`],
                [t('booking.summary.msp'), `₹${selectedCrop?.msp_per_quintal}/Q`],
              ].map(([key, val]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-500">{key}</span>
                  <span className="text-gray-900 font-semibold">{val}</span>
                </div>
              ))}
              <div className="border-t pt-3 flex justify-between">
                <span className="text-gray-700 font-semibold">{t('booking.summary.estimated')}</span>
                <span className="text-xl font-extrabold text-primary">
                  ₹{(parseFloat(quantity) * (selectedCrop?.msp_per_quintal || 0)).toLocaleString('en-IN')}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex gap-3 mt-6">
          {step > 0 && (
            <button onClick={() => setStep((s) => s - 1)} className="btn-secondary text-base px-5 py-3">
              <ChevronLeft className="w-4 h-4" /> {t('auth.register.back')}
            </button>
          )}
          {step < 5 ? (
            <button onClick={handleNext} className="btn-primary flex-1 text-base py-3" id={`booking-next-${step}`}>
              {t('auth.register.next')} <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleConfirm}
              disabled={loading}
              className="btn-primary flex-1 text-base py-3"
              id="booking-confirm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? t('booking.loading') : t('booking.confirm.button')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
