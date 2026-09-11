/**
 * Speech helper — reads status text aloud using the browser's built-in
 * speechSynthesis (no external dependency). Designed for low-literacy
 * farmers: Hindi when the UI is Hindi, English otherwise.
 */

let cachedVoices: SpeechSynthesisVoice[] | null = null

function loadVoices(): SpeechSynthesisVoice[] {
  if (cachedVoices) return cachedVoices
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return []
  cachedVoices = window.speechSynthesis.getVoices()
  return cachedVoices
}

export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function speak(text: string, language: 'hi' | 'en' = 'en') {
  if (!isSpeechSupported() || !text) return
  const synth = window.speechSynthesis
  synth.cancel()

  const utterance = new SpeechSynthesisUtterance(text)
  const langCode = language === 'hi' ? 'hi-IN' : 'en-IN'
  utterance.lang = langCode
  utterance.rate = 0.9 // slightly slower for clarity

  const voices = loadVoices()
  const match =
    voices.find((v) => v.lang === langCode) ||
    voices.find((v) => v.lang.startsWith(language === 'hi' ? 'hi' : 'en'))
  if (match) utterance.voice = match

  synth.speak(utterance)
}

export function stopSpeaking() {
  if (isSpeechSupported()) window.speechSynthesis.cancel()
}
