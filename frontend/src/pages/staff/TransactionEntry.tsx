/** Mandi Staff — Transaction Entry with 3-tab form. */
import React, { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { CheckCircle, Upload, Loader2 } from 'lucide-react'
import { get, post, put } from '@/utils/api'
import clsx from 'clsx'

interface Transaction {
  id: string; farmer_name?: string; crop_name?: string; centre_name?: string
  gross_weight_q?: number; tare_weight_q?: number; net_weight_q?: number
  msp_per_q?: number; total_amount?: number
  quality_status?: string; moisture_percent?: number; foreign_matter_percent?: number
  quality_notes?: string; procurement_status: string; payment_status: string
  payment_ref?: string; pfms_transaction_id?: string
}

type Tab = 'quality' | 'weighment' | 'confirm'

export default function TransactionEntry() {
  const { bookingId } = useParams<{ bookingId: string }>()
  const { t } = useTranslation()
  const [transaction, setTransaction] = useState<Transaction | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('quality')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [qPhotoPreview, setQPhotoPreview] = useState<string>('')
  const [wPhotoPreview, setWPhotoPreview] = useState<string>('')

  // Quality form
  const [moisture, setMoisture] = useState('')
  const [foreignMatter, setForeignMatter] = useState('')
  const [qualityResult, setQualityResult] = useState<'ACCEPTED' | 'REJECTED' | 'CONDITIONAL'>('ACCEPTED')
  const [qualityNotes, setQualityNotes] = useState('')

  // Weighment form
  const [grossWeight, setGrossWeight] = useState('')
  const [tareWeight, setTareWeight] = useState('')

  useEffect(() => {
    const initTransaction = async () => {
      try {
        let txn: Transaction
        try {
          txn = await get<Transaction>(`/transactions/by-booking/${bookingId}`)
        } catch {
          txn = await post<Transaction>('/transactions/', { slot_booking_id: bookingId })
        }
        setTransaction(txn)
        if (txn.moisture_percent) setMoisture(String(txn.moisture_percent))
        if (txn.foreign_matter_percent) setForeignMatter(String(txn.foreign_matter_percent))
        if (txn.quality_status) setQualityResult(txn.quality_status as typeof qualityResult)
        if (txn.gross_weight_q) setGrossWeight(String(txn.gross_weight_q))
        if (txn.tare_weight_q) setTareWeight(String(txn.tare_weight_q))
      } catch (e) { toast.error('Failed to load transaction') }
      finally { setLoading(false) }
    }
    if (bookingId) initTransaction()
  }, [bookingId])

  const netWeight = grossWeight && tareWeight
    ? Math.max(0, parseFloat(grossWeight) - parseFloat(tareWeight)).toFixed(3)
    : null

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>, setter: (s: string) => void) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setter(reader.result as string)
    reader.readAsDataURL(file)
  }

  const saveQuality = async () => {
    if (!transaction) return
    setSaving(true)
    try {
      const updated = await put<Transaction>(`/transactions/${transaction.id}/quality`, {
        moisture_percent: parseFloat(moisture),
        foreign_matter_percent: parseFloat(foreignMatter),
        quality_status: qualityResult,
        quality_notes: qualityNotes,
        quality_photo_url: qPhotoPreview || undefined,
      })
      setTransaction(updated)
      toast.success('Quality data saved!')
      setActiveTab('weighment')
    } catch { toast.error('Failed to save quality data') }
    finally { setSaving(false) }
  }

  const saveWeighment = async () => {
    if (!transaction || !grossWeight || !tareWeight) { toast.error('Enter gross and tare weights'); return }
    setSaving(true)
    try {
      const updated = await put<Transaction>(`/transactions/${transaction.id}/weighment`, {
        gross_weight_q: parseFloat(grossWeight),
        tare_weight_q: parseFloat(tareWeight),
        weighment_photo_url: wPhotoPreview || undefined,
      })
      setTransaction(updated)
      toast.success('Weighment data saved!')
      setActiveTab('confirm')
    } catch { toast.error('Failed to save weighment data') }
    finally { setSaving(false) }
  }

  const confirmPurchase = async () => {
    if (!transaction) return
    setSaving(true)
    try {
      const updated = await put<Transaction>(`/transactions/${transaction.id}/confirm`)
      setTransaction(updated)
      toast.success('Purchase confirmed!')
    } catch { toast.error('Failed to confirm purchase') }
    finally { setSaving(false) }
  }

  const initiatePayment = async () => {
    if (!transaction) return
    setSaving(true)
    try {
      const updated = await put<Transaction>(`/transactions/${transaction.id}/payment`)
      setTransaction(updated)
      toast.success('Payment initiated via PFMS!')
    } catch { toast.error('Payment failed') }
    finally { setSaving(false) }
  }

  if (loading) return <div className="card p-8 text-center"><Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" /></div>

  const qualityDone = !!transaction?.quality_status
  const weighmentDone = !!transaction?.net_weight_q
  const confirmed = transaction?.procurement_status === 'CONFIRMED'
  const paid = transaction?.payment_status === 'PAID'

  const TABS: Array<{ key: Tab; label: string; done: boolean }> = [
    { key: 'quality', label: t('transaction.tab.quality'), done: qualityDone },
    { key: 'weighment', label: t('transaction.tab.weighment'), done: weighmentDone },
    { key: 'confirm', label: t('transaction.tab.confirm'), done: confirmed },
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title">{t('transaction.title')}</h1>
        <p className="text-gray-500 mt-1">{transaction?.farmer_name} · {transaction?.crop_name} · {transaction?.centre_name}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
        {TABS.map((tab_) => (
          <button
            key={tab_.key}
            onClick={() => setActiveTab(tab_.key)}
            className={clsx(
              'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all',
              activeTab === tab_.key ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
            )}
            id={`tab-${tab_.key}`}
          >
            {tab_.done && <CheckCircle className="w-4 h-4 text-primary" />}
            {tab_.label}
          </button>
        ))}
      </div>

      <div className="card p-6">
        {/* Quality Tab */}
        {activeTab === 'quality' && (
          <div className="space-y-5 animate-fade-in">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">{t('transaction.moisture')} (%)</label>
                <input className="input" type="number" step="0.1" value={moisture}
                  onChange={(e) => setMoisture(e.target.value)} placeholder="12.5" id="moisture-input" />
              </div>
              <div>
                <label className="label">{t('transaction.foreignMatter')} (%)</label>
                <input className="input" type="number" step="0.01" value={foreignMatter}
                  onChange={(e) => setForeignMatter(e.target.value)} placeholder="0.5" id="foreign-matter-input" />
              </div>
            </div>
            <div>
              <label className="label">{t('transaction.qualityResult')}</label>
              <div className="flex gap-3">
                {['ACCEPTED', 'REJECTED', 'CONDITIONAL'].map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setQualityResult(opt as typeof qualityResult)}
                    className={clsx(
                      'flex-1 py-3 rounded-xl text-sm font-bold border-2 transition-all',
                      qualityResult === opt
                        ? opt === 'ACCEPTED' ? 'border-green-500 bg-green-50 text-green-700'
                          : opt === 'REJECTED' ? 'border-red-500 bg-red-50 text-red-700'
                          : 'border-yellow-500 bg-yellow-50 text-yellow-700'
                        : 'border-gray-200 text-gray-500 hover:border-gray-300'
                    )}
                    id={`quality-${opt.toLowerCase()}`}
                  >
                    {opt === 'ACCEPTED' ? 'Accepted' : opt === 'REJECTED' ? 'Rejected' : 'Conditional'}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label">{t('transaction.notes')}</label>
              <textarea className="input min-h-[80px] resize-none" value={qualityNotes}
                onChange={(e) => setQualityNotes(e.target.value)} placeholder="Any notes about quality..." id="quality-notes" />
            </div>
            <div>
              <label className="label">Photo Evidence</label>
              <label className="flex items-center gap-2 border-2 border-dashed border-gray-200 rounded-xl p-4 cursor-pointer hover:border-primary transition-colors">
                <Upload className="w-5 h-5 text-gray-400" />
                <span className="text-sm text-gray-500">Upload quality photo</span>
                <input type="file" accept="image/*" className="hidden" onChange={(e) => handlePhotoUpload(e, setQPhotoPreview)} id="quality-photo" />
              </label>
              {qPhotoPreview && <img src={qPhotoPreview} alt="Quality" className="mt-2 h-32 object-cover rounded-xl w-full" />}
            </div>
            <button onClick={saveQuality} disabled={saving} className="btn-primary w-full" id="save-quality">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {t('transaction.saveQuality')}
            </button>
          </div>
        )}

        {/* Weighment Tab */}
        {activeTab === 'weighment' && (
          <div className="space-y-5 animate-fade-in">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">{t('transaction.grossWeight')}</label>
                <input className="input text-xl font-bold" type="number" step="0.01" value={grossWeight}
                  onChange={(e) => setGrossWeight(e.target.value)} placeholder="50.00" id="gross-weight" />
              </div>
              <div>
                <label className="label">{t('transaction.tareWeight')}</label>
                <input className="input text-xl font-bold" type="number" step="0.01" value={tareWeight}
                  onChange={(e) => setTareWeight(e.target.value)} placeholder="2.50" id="tare-weight" />
              </div>
            </div>
            {netWeight && (
              <div className="p-5 bg-primary-50 rounded-xl border border-primary-100 text-center">
                <p className="text-sm text-gray-500 mb-1">{t('transaction.netWeight')}</p>
                <p className="text-4xl font-extrabold text-primary">{netWeight} Q</p>
              </div>
            )}
            <div>
              <label className="label">Weighment Photo</label>
              <label className="flex items-center gap-2 border-2 border-dashed border-gray-200 rounded-xl p-4 cursor-pointer hover:border-primary transition-colors">
                <Upload className="w-5 h-5 text-gray-400" />
                <span className="text-sm text-gray-500">Upload weighment photo</span>
                <input type="file" accept="image/*" className="hidden" onChange={(e) => handlePhotoUpload(e, setWPhotoPreview)} id="weighment-photo" />
              </label>
              {wPhotoPreview && <img src={wPhotoPreview} alt="Weighment" className="mt-2 h-32 object-cover rounded-xl w-full" />}
            </div>
            <button onClick={saveWeighment} disabled={saving} className="btn-primary w-full" id="save-weighment">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {t('transaction.saveWeighment')}
            </button>
          </div>
        )}

        {/* Confirm & Pay Tab */}
        {activeTab === 'confirm' && (
          <div className="space-y-5 animate-fade-in">
            <div className="table-container">
              <table className="table">
                <tbody>
                  {[
                    ['Farmer', transaction?.farmer_name],
                    ['Crop', transaction?.crop_name],
                    ['Quality', transaction?.quality_status || '—'],
                    ['Net Quantity', transaction?.net_weight_q ? `${transaction.net_weight_q} Q` : '—'],
                    ['MSP Rate', transaction?.msp_per_q ? `₹${transaction.msp_per_q}/Q` : '—'],
                  ].map(([label, value]) => (
                    <tr key={label}><td className="font-medium text-gray-500">{label}</td><td className="font-semibold text-gray-900">{value}</td></tr>
                  ))}
                  <tr className="bg-green-50">
                    <td className="font-bold text-gray-900">{t('transaction.totalAmount')}</td>
                    <td className="text-2xl font-extrabold text-green-700">
                      {transaction?.total_amount ? `₹${transaction.total_amount.toLocaleString('en-IN')}` : '—'}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {!confirmed && (
              <button onClick={confirmPurchase} disabled={saving || !weighmentDone} className="btn-primary w-full" id="confirm-purchase">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                {t('transaction.confirmPurchase')}
              </button>
            )}

            {confirmed && !paid && (
              <div className="space-y-3">
                <div className="p-3 bg-green-50 rounded-lg border border-green-100 text-sm text-green-700 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                  <span>Purchase confirmed. Proceed to payment.</span>
                </div>
                <button onClick={initiatePayment} disabled={saving} className="btn-accent w-full" id="initiate-payment">
                  {saving ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('transaction.paymentProcessing')}
                    </span>
                  ) : t('transaction.initiatePayment')}
                </button>
              </div>
            )}

            {paid && (
              <div className="p-4 bg-green-50 rounded-xl border border-green-200 text-center">
                <CheckCircle className="w-10 h-10 text-green-600 mx-auto mb-2" />
                <p className="font-bold text-green-800">{t('transaction.paymentSuccess')}</p>
                <p className="text-xs text-green-600 mt-1">PFMS Ref: {transaction?.payment_ref}</p>
                <p className="text-xs text-green-600">UTR: {transaction?.pfms_transaction_id}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
