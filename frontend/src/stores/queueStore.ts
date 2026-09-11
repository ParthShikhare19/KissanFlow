/**
 * Zustand queue store — real-time queue state updated via Socket.IO.
 */
import { create } from 'zustand'

export interface QueueEntry {
  id: string
  slot_booking_id: string
  position: number
  estimated_wait_minutes: number
  status: 'WAITING' | 'CALLED' | 'PROCESSING' | 'DONE'
  farmer_name?: string
  token_number?: string
  crop_name?: string
  declared_quantity_q?: number
}

export interface QueuePosition {
  booking_id: string
  position: number
  estimated_wait_minutes: number
  status: string
  ahead_of_you: number
}

interface QueueState {
  centreQueue: QueueEntry[]
  myPosition: QueuePosition | null
  isYourTurn: boolean
  setCentreQueue: (queue: QueueEntry[]) => void
  setMyPosition: (pos: QueuePosition | null) => void
  setYourTurn: (val: boolean) => void
  clearQueue: () => void
}

export const useQueueStore = create<QueueState>((set) => ({
  centreQueue: [],
  myPosition: null,
  isYourTurn: false,

  setCentreQueue: (queue) => set({ centreQueue: queue }),
  setMyPosition: (pos) => set({ myPosition: pos }),
  setYourTurn: (val) => set({ isYourTurn: val }),
  clearQueue: () => set({ centreQueue: [], myPosition: null, isYourTurn: false }),
}))
