/**
 * KissanFlow 24x7 Toll-Free Voice Helpline (IVR) Guide.
 * 
 * Farmers call a real toll-free phone number from any phone (basic keypad or smartphone)
 * without needing internet or a computer.
 *
 * Displays:
 *   - The toll-free number to call
 *   - Static visual diagram of the IVR menu decision tree
 *   - Call history section with IVR grievances raised by phone
 */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  PhoneCall, ShieldCheck, Clock, CheckCircle2,
  AlertCircle, Smartphone, Volume2, ArrowDown,
  Building, CreditCard, Scale, HelpCircle, FileText, UserCheck
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { get } from '@/utils/api'
import clsx from 'clsx'

interface Grievance {
  id: string
  category: string
  description: string
  status: string
  created_at: string
}

export default function IVRHelpline() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [grievances, setGrievances] = useState<Grievance[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Toll-free phone number from environment or official default
  const TOLL_FREE_NUMBER = (
    (import.meta as unknown as { env: Record<string, string> }).env?.VITE_TWILIO_PHONE_NUMBER ||
    '1800-180-1551'
  )

  useEffect(() => {
    if (user?.id) {
      setLoadingHistory(true)
      get<Grievance[]>('/grievances/')
        .then((data) => {
          setGrievances(data || [])
        })
        .catch(() => {})
        .finally(() => setLoadingHistory(false))
    }
  }, [user])

  // Filter grievances initiated via IVR / phone
  const ivrGrievances = grievances.filter(
    (g) => g.description?.toLowerCase().includes('ivr') || g.description?.toLowerCase().includes('voice') || g.description?.toLowerCase().includes('helpline')
  )
  const displayGrievances = ivrGrievances.length > 0 ? ivrGrievances : grievances

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in pb-16">
      {/* ─── Hero Card: Toll-Free Calling Number ─── */}
      <div className="bg-gradient-to-br from-emerald-800 to-teal-900 text-white rounded-3xl p-8 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 translate-x-12 -translate-y-12 w-72 h-72 bg-white/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-700/60 border border-emerald-400/30 text-emerald-100 text-xs font-semibold tracking-wide">
              <span className="w-2 h-2 rounded-full bg-emerald-300 animate-pulse" />
              24x7 Automated Voice Telephony
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
              {t('ivr.title')}
            </h1>
            <p className="text-emerald-100 text-base max-w-xl leading-relaxed">
              {t('ivr.subtitle')}
            </p>
          </div>

          {/* Direct Calling Box */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 p-6 rounded-2xl text-center md:text-right flex-shrink-0 shadow-lg">
            <p className="text-xs text-emerald-200 uppercase font-bold tracking-wider">
              {t('ivr.tollFree')}
            </p>
            <p className="text-3xl sm:text-4xl font-black font-mono tracking-wider text-white mt-1">
              {TOLL_FREE_NUMBER}
            </p>
            <a
              href={`tel:${TOLL_FREE_NUMBER.replace(/[^0-9+]/g, '')}`}
              className="mt-4 inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-emerald-400 hover:bg-emerald-300 text-emerald-950 font-extrabold text-sm shadow-md hover:shadow-xl transition-all w-full"
            >
              <PhoneCall className="w-4 h-4" />
              {t('ivr.callNow')}
            </a>
          </div>
        </div>

        {/* Feature Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6 border-t border-emerald-700/60 text-sm">
          <div className="flex items-center gap-2.5 text-emerald-100 font-medium">
            <Smartphone className="w-5 h-5 text-emerald-300 flex-shrink-0" />
            <span>Works on Any Phone</span>
          </div>
          <div className="flex items-center gap-2.5 text-emerald-100 font-medium">
            <UserCheck className="w-5 h-5 text-emerald-300 flex-shrink-0" />
            <span>Caller ID Auto-Detect</span>
          </div>
          <div className="flex items-center gap-2.5 text-emerald-100 font-medium">
            <Volume2 className="w-5 h-5 text-emerald-300 flex-shrink-0" />
            <span>Hindi & English Voice</span>
          </div>
          <div className="flex items-center gap-2.5 text-emerald-100 font-medium">
            <Clock className="w-5 h-5 text-emerald-300 flex-shrink-0" />
            <span>Zero Internet Needed</span>
          </div>
        </div>
      </div>

      {/* ─── Static Visual IVR Menu Tree ─── */}
      <div className="card p-8 border border-gray-200 bg-white shadow-sm space-y-6">
        <div>
          <h2 className="text-2xl font-extrabold text-gray-900 tracking-tight">
            {t('ivr.treeTitle')}
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            Visual flowchart of what happens when you dial the helpline from your phone
          </p>
        </div>

        {/* Root Node: Dialing */}
        <div className="flex flex-col items-center">
          <div className="w-full max-w-md p-4 rounded-2xl bg-emerald-50 border-2 border-emerald-300 text-center shadow-xs">
            <p className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Step 1: Farmer Dials</p>
            <p className="text-lg font-black font-mono text-emerald-950 mt-0.5">{TOLL_FREE_NUMBER}</p>
            <p className="text-xs text-emerald-700 mt-1">
              System identifies caller mobile number and greets you in Hindi & English
            </p>
          </div>

          <ArrowDown className="w-6 h-6 text-gray-300 my-2 stroke-[2.5]" />

          <div className="w-full max-w-lg p-3.5 rounded-xl bg-gray-900 text-white text-center shadow-xs">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Main Audio Menu</p>
            <p className="text-sm font-bold text-emerald-300 mt-0.5">
              &ldquo;Welcome to KissanFlow. किसानफ्लो हेल्पलाइन में आपका स्वागत है।&rdquo;
            </p>
          </div>

          <ArrowDown className="w-6 h-6 text-gray-300 my-2 stroke-[2.5]" />
        </div>

        {/* Branching Grid of 4 Key Options */}
        <div className="grid sm:grid-cols-2 gap-4 pt-2">
          {/* Option 1 */}
          <div className="p-5 rounded-2xl border-2 border-blue-200 bg-blue-50/40 hover:border-blue-300 transition-colors">
            <div className="flex items-center gap-3 mb-2">
              <span className="w-8 h-8 rounded-xl bg-blue-600 text-white font-mono font-black text-sm flex items-center justify-center shadow-xs">
                1
              </span>
              <div>
                <h3 className="font-extrabold text-blue-950 text-base">Press 1: Booking & Queue Status</h3>
                <p className="text-xs text-blue-700">अपनी बुकिंग स्थिति के लिए</p>
              </div>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed mt-2 bg-white/80 p-3 rounded-xl border border-blue-100">
              Bot looks up your active slot in the database and reads:
              <br />
              <strong className="text-gray-900">&ldquo;Your token WHT-00001 is in queue at Ludhiana Mandi. You are number 3. Estimated wait: 15 minutes.&rdquo;</strong>
            </p>
          </div>

          {/* Option 2 */}
          <div className="p-5 rounded-2xl border-2 border-rose-200 bg-rose-50/40 hover:border-rose-300 transition-colors">
            <div className="flex items-center gap-3 mb-2">
              <span className="w-8 h-8 rounded-xl bg-rose-600 text-white font-mono font-black text-sm flex items-center justify-center shadow-xs">
                2
              </span>
              <div>
                <h3 className="font-extrabold text-rose-950 text-base">Press 2: Raise a Grievance</h3>
                <p className="text-xs text-rose-700">शिकायत दर्ज करने के लिए</p>
              </div>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed mt-2 bg-white/80 p-3 rounded-xl border border-rose-100">
              Select issue category with keypad:
              <br />
              <span className="font-mono text-[11px] text-rose-800 font-bold">1: Slot Issue &bull; 2: Payment Issue &bull; 3: Quality &bull; 4: Weighment</span>
              <br />
              Creates ticket in DB and speaks your reference ID (e.g. <strong className="text-gray-900">GRV-2024-001</strong>).
            </p>
          </div>

          {/* Option 3 */}
          <div className="p-5 rounded-2xl border-2 border-amber-200 bg-amber-50/40 hover:border-amber-300 transition-colors">
            <div className="flex items-center gap-3 mb-2">
              <span className="w-8 h-8 rounded-xl bg-amber-600 text-white font-mono font-black text-sm flex items-center justify-center shadow-xs">
                3
              </span>
              <div>
                <h3 className="font-extrabold text-amber-950 text-base">Press 3: Booking Information</h3>
                <p className="text-xs text-amber-700">स्लॉट बुकिंग जानकारी</p>
              </div>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed mt-2 bg-white/80 p-3 rounded-xl border border-amber-100">
              Bot explains slot booking instructions:
              <br />
              <strong className="text-gray-900">&ldquo;To book a slot, visit kissanflow.in or call your local CSC Common Service Centre with your Aadhaar and bank passbook.&rdquo;</strong>
            </p>
          </div>

          {/* Option 0 */}
          <div className="p-5 rounded-2xl border-2 border-purple-200 bg-purple-50/40 hover:border-purple-300 transition-colors">
            <div className="flex items-center gap-3 mb-2">
              <span className="w-8 h-8 rounded-xl bg-purple-600 text-white font-mono font-black text-sm flex items-center justify-center shadow-xs">
                0
              </span>
              <div>
                <h3 className="font-extrabold text-purple-950 text-base">Press 0: Speak to Officer</h3>
                <p className="text-xs text-purple-700">मंडी अधिकारी से बात करें</p>
              </div>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed mt-2 bg-white/80 p-3 rounded-xl border border-purple-100">
              Transfers the call to the Mandi Helpdesk operator or Mandi Officer on duty during working hours (Mon–Sat, 9 AM–6 PM).
            </p>
          </div>
        </div>

        {/* Footer info strip */}
        <div className="p-4 rounded-xl bg-gray-50 border border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-600">
          <span className="flex items-center gap-1.5 font-medium">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            Press <strong className="font-mono text-gray-900">9</strong> at any time to repeat the audio menu
          </span>
          <span className="text-gray-500">
            SMS confirmation is automatically sent to caller mobile upon completion
          </span>
        </div>
      </div>

      {/* ─── Call History / Registered Grievances Section ─── */}
      <div className="card p-8 border border-gray-200 bg-white shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-2xl font-extrabold text-gray-900 tracking-tight">
              {t('ivr.historyTitle')}
            </h2>
            <p className="text-gray-500 text-sm mt-0.5">
              Grievance tickets logged through the phone helpline for your registered mobile
            </p>
          </div>
          <span className="badge badge-green text-xs font-semibold self-start sm:self-auto">
            {displayGrievances.length} Tickets on File
          </span>
        </div>

        {loadingHistory ? (
          <p className="text-gray-400 text-sm text-center py-8">Loading your tickets...</p>
        ) : displayGrievances.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-2xl bg-gray-50/50">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-base font-bold text-gray-800">No active grievances on record</h3>
            <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1">
              If you face any issues with your slot, weighment, or payment at the mandi, dial {TOLL_FREE_NUMBER} and press 2 to lodge a ticket.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {displayGrievances.map((g) => (
              <div key={g.id} className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5">
                    <span className="font-bold text-gray-900 text-sm">
                      {g.category.replace(/_/g, ' ')}
                    </span>
                    <span className={clsx('badge text-xs font-semibold', {
                      'badge-green': g.status === 'RESOLVED',
                      'badge-yellow': g.status === 'IN_PROGRESS',
                      'badge-gray': g.status === 'OPEN',
                    })}>
                      {g.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 leading-relaxed">{g.description}</p>
                </div>
                <div className="text-xs text-gray-400 font-medium flex-shrink-0">
                  {new Date(g.created_at).toLocaleDateString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric'
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
