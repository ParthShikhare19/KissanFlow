/**
 * Socket.IO hook — connects to backend via the Vite dev proxy,
 * joins rooms, and wires up real-time events.
 */
import { useEffect, useRef } from 'react'
import { io, Socket } from 'socket.io-client'
import { toast } from 'react-hot-toast'
import { useQueueStore } from '@/stores/queueStore'
import { useNotificationStore } from '@/stores/notificationStore'
import { useAuthStore } from '@/stores/authStore'

// Connect via the Vite dev proxy (same origin) so CORS is never an issue.
// In production, set VITE_SOCKET_URL to your backend URL.
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || window.location.origin

let globalSocket: Socket | null = null

export function useSocket(centreId?: string, bookingId?: string) {
  const socketRef = useRef<Socket | null>(null)
  const { user } = useAuthStore()
  const { setCentreQueue, setYourTurn } = useQueueStore()
  const { addNotification } = useNotificationStore()

  useEffect(() => {
    if (!user) return

    // Reuse existing connection
    if (!globalSocket || !globalSocket.connected) {
      globalSocket = io(SOCKET_URL, {
        path: '/ws/socket.io',
        transports: ['websocket', 'polling'],
        auth: { user_id: user.id },
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 2000,
      })
    }

    const socket = globalSocket
    socketRef.current = socket

    const onConnect = () => {
      console.log('[Socket] Connected:', socket.id)

      // Join centre room (for staff/officers)
      if (centreId) {
        socket.emit('join_centre', { centre_id: centreId })
      }

      // Join personal farmer room
      if (bookingId) {
        socket.emit('join_farmer', { booking_id: bookingId })
      }
    }

    const onQueueUpdated = (data: { queue: ReturnType<typeof useQueueStore.getState>['centreQueue'] }) => {
      setCentreQueue(data.queue)
    }

    const onYourTurn = (data: { message: string; booking_id: string }) => {
      setYourTurn(true)
      toast.success(data.message || "It's your turn!", {
        duration: 10000,
      })
      addNotification({
        id: Date.now().toString(),
        title: "It's Your Turn!",
        body: data.message,
        channel: 'APP',
        is_read: false,
        created_at: new Date().toISOString(),
      })
    }

    const onAlertNew = (data: { type: string; message: string; severity: string }) => {
      toast.error(data.message, { duration: 8000 })
    }

    const onDisconnect = () => {
      console.log('[Socket] Disconnected')
    }

    // Register events (avoid duplicate listeners)
    socket.off('connect', onConnect).on('connect', onConnect)
    socket.off('queue:updated', onQueueUpdated).on('queue:updated', onQueueUpdated)
    socket.off('queue:your-turn', onYourTurn).on('queue:your-turn', onYourTurn)
    socket.off('alert:new', onAlertNew).on('alert:new', onAlertNew)
    socket.off('disconnect', onDisconnect).on('disconnect', onDisconnect)

    // If already connected, join rooms immediately
    if (socket.connected) {
      onConnect()
    }

    return () => {
      if (centreId) socket.emit('leave_centre', { centre_id: centreId })
      if (bookingId) socket.emit('leave_farmer', { booking_id: bookingId })
      // Remove listeners but keep connection alive for reuse
      socket.off('connect', onConnect)
      socket.off('queue:updated', onQueueUpdated)
      socket.off('queue:your-turn', onYourTurn)
      socket.off('alert:new', onAlertNew)
      socket.off('disconnect', onDisconnect)
    }
  }, [user?.id, centreId, bookingId])

  return socketRef.current
}
