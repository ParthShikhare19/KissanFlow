/** IVR Simulation Panel — frontend-only phone UI simulation. */
import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Phone, PhoneOff, Hash } from 'lucide-react'

type IVRScreen = 'idle' | 'main' | 'status' | 'status-input' | 'status-result' | 'book' | 'grievance' | 'ended'

const MENU_TREE: Record<string, { text: string; options?: Array<{ key: string; label: string; next: IVRScreen }> }> = {
  main: {
    text: 'Welcome to AnnSetu Helpline. अन्नसेतु हेल्पलाइन में आपका स्वागत है.\n\nPress 1 to check your booking status\nPress 2 to book a slot\nPress 3 to raise a grievance\nPress 9 to repeat this menu',
    options: [
      { key: '1', label: 'Check Status', next: 'status-input' },
      { key: '2', label: 'Book Slot', next: 'book' },
      { key: '3', label: 'Raise Grievance', next: 'grievance' },
      { key: '9', label: 'Repeat', next: 'main' },
    ],
  },
  'status-input': {
    text: 'Please enter your token number followed by #.\nFor example: WHT-00001 then press #',
  },
  'status-result': {
    text: 'Token WHT-00001: Status is IN QUEUE.\nYou are number 5 in queue at Ludhiana Mandi A.\nEstimated wait time: 25 minutes.\n\nPress 1 for main menu\nPress 9 to end call',
    options: [
      { key: '1', label: 'Main Menu', next: 'main' },
      { key: '9', label: 'End Call', next: 'ended' },
    ],
  },
  book: {
    text: 'To book a slot, please use the AnnSetu mobile app or visit your nearest CSC centre.\n\nYour registered mobile will receive booking confirmation.\n\nPress 1 for main menu\nPress 9 to end call',
    options: [
      { key: '1', label: 'Main Menu', next: 'main' },
      { key: '9', label: 'End Call', next: 'ended' },
    ],
  },
  grievance: {
    text: 'To raise a grievance:\nPress 1 for Slot Issue\nPress 2 for Payment Issue\nPress 3 for Quality Dispute\nPress 9 to end call',
    options: [
      { key: '1', label: 'Slot Issue registered. GRV-2024-001 created. You will be contacted within 48 hours.', next: 'main' },
      { key: '2', label: 'Payment Issue registered.', next: 'main' },
      { key: '3', label: 'Quality Dispute registered.', next: 'main' },
      { key: '9', label: 'End Call', next: 'ended' },
    ],
  },
}

export default function IVRSim() {
  const { t } = useTranslation()
  const [screen, setScreen] = useState<IVRScreen>('idle')
  const [transcript, setTranscript] = useState<Array<{ speaker: 'system' | 'user'; text: string }>>([])
  const [tokenInput, setTokenInput] = useState('')
  const [callDuration, setCallDuration] = useState(0)
  const [timerRef, setTimerRef] = useState<ReturnType<typeof setInterval> | null>(null)

  const addLine = (speaker: 'system' | 'user', text: string) => {
    setTranscript((t) => [...t, { speaker, text }])
  }

  const startCall = () => {
    setScreen('main')
    setTranscript([])
    addLine('system', t('ivr.connected'))
    setTimeout(() => addLine('system', MENU_TREE.main.text), 500)
    const timer = setInterval(() => setCallDuration((d) => d + 1), 1000)
    setTimerRef(timer)
  }

  const endCall = () => {
    setScreen('ended')
    if (timerRef) clearInterval(timerRef)
    addLine('system', 'Thank you for calling AnnSetu. अन्नसेतु पर कॉल करने के लिए धन्यवाद। Goodbye!')
  }

  const pressKey = (key: string) => {
    addLine('user', `[Pressed ${key}]`)
    const current = MENU_TREE[screen]
    if (!current?.options) {
      if (screen === 'status-input') {
        if (key === '#') {
          addLine('system', 'Checking your token...')
          setTimeout(() => {
            setScreen('status-result')
            addLine('system', MENU_TREE['status-result'].text)
          }, 1500)
        } else {
          setTokenInput((t) => t + key)
          addLine('system', `Token so far: ${tokenInput + key}`)
        }
        return
      }
      return
    }
    const option = current.options.find((o) => o.key === key)
    if (!option) {
      addLine('system', 'Invalid option. Please try again.')
      return
    }
    const nextScreen = option.next
    if (nextScreen === 'ended') {
      endCall()
      return
    }
    setScreen(nextScreen)
    const nextMenu = MENU_TREE[nextScreen]
    if (nextMenu) {
      addLine('system', nextMenu.text || option.label)
    }
  }

  const formatTime = (s: number) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <div className="max-w-sm mx-auto">
      <h1 className="page-title mb-6">{t('ivr.title')}</h1>

      {/* Phone Frame */}
      <div className="bg-gray-900 rounded-[3rem] p-6 shadow-2xl border-4 border-gray-800">
        {/* Screen */}
        <div className="bg-gray-950 rounded-2xl p-4 mb-6 min-h-[360px] flex flex-col">
          {screen === 'idle' ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
              <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
                <Phone className="w-8 h-8 text-primary-light" />
              </div>
              <p className="text-gray-400 text-sm">AnnSetu IVR Helpline<br />Simulation</p>
              <p className="text-gray-600 text-xs">1800-XXX-XXXX (Toll Free)</p>
            </div>
          ) : (
            <>
              {/* Call header */}
              <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-800">
                <div>
                  <p className="text-green-400 text-xs font-semibold">CALL CONNECTED</p>
                  <p className="text-white text-sm font-bold">AnnSetu Helpline</p>
                </div>
                <p className="text-green-400 text-xs font-mono">{formatTime(callDuration)}</p>
              </div>
              {/* Transcript */}
              <div className="flex-1 space-y-2 overflow-y-auto max-h-[260px] pr-1">
                {transcript.map((line, i) => (
                  <div key={i} className={`text-xs ${line.speaker === 'system' ? 'text-gray-300' : 'text-green-400 text-right'}`}>
                    {line.speaker === 'system' && (
                      <span className="text-gray-600 mr-1">[IVR]</span>
                    )}
                    <span style={{ whiteSpace: 'pre-line' }}>{line.text}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Keypad */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {['1','2','3','4','5','6','7','8','9','*','0','#'].map((k) => (
            <button
              key={k}
              onClick={() => screen !== 'idle' && screen !== 'ended' ? pressKey(k) : undefined}
              disabled={screen === 'idle' || screen === 'ended'}
              className={`h-14 rounded-full text-lg font-bold transition-all
                ${screen === 'idle' || screen === 'ended'
                  ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                  : 'bg-gray-700 text-white hover:bg-gray-600 active:scale-95'}`}
            >
              {k === '#' ? <Hash className="w-4 h-4 mx-auto" /> : k}
            </button>
          ))}
        </div>

        {/* Call button */}
        <div className="flex gap-3 justify-center">
          {screen === 'idle' || screen === 'ended' ? (
            <button
              onClick={startCall}
              className="w-16 h-16 rounded-full bg-green-500 hover:bg-green-600 flex items-center justify-center shadow-lg active:scale-95 transition-all"
              aria-label="Start call"
            >
              <Phone className="w-7 h-7 text-white" />
            </button>
          ) : (
            <button
              onClick={endCall}
              className="w-16 h-16 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center shadow-lg active:scale-95 transition-all"
              aria-label="End call"
            >
              <PhoneOff className="w-7 h-7 text-white" />
            </button>
          )}
        </div>
      </div>

      {screen === 'ended' && (
        <div className="mt-4 text-center">
          <p className="text-gray-500 text-sm">{t('ivr.callEnded')}</p>
          <button onClick={() => { setScreen('idle'); setCallDuration(0) }} className="btn-primary mt-3">
            Start New Call
          </button>
        </div>
      )}
    </div>
  )
}
