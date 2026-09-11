/**
 * Zustand notification store — manages unread count and notification list.
 */
import { create } from 'zustand'

export interface AppNotification {
  id: string
  title: string
  body: string
  channel: 'APP' | 'SMS' | 'IVR'
  is_read: boolean
  created_at: string
}

interface NotificationState {
  notifications: AppNotification[]
  unreadCount: number
  setNotifications: (notifs: AppNotification[]) => void
  setUnreadCount: (count: number) => void
  markRead: (id: string) => void
  markAllRead: () => void
  addNotification: (notif: AppNotification) => void
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,

  setNotifications: (notifs) => {
    set({
      notifications: notifs,
      unreadCount: notifs.filter((n) => !n.is_read).length,
    })
  },

  setUnreadCount: (count) => set({ unreadCount: count }),

  markRead: (id) => {
    const updated = get().notifications.map((n) =>
      n.id === id ? { ...n, is_read: true } : n
    )
    set({
      notifications: updated,
      unreadCount: updated.filter((n) => !n.is_read).length,
    })
  },

  markAllRead: () => {
    const updated = get().notifications.map((n) => ({ ...n, is_read: true }))
    set({ notifications: updated, unreadCount: 0 })
  },

  addNotification: (notif) => {
    const updated = [notif, ...get().notifications]
    set({
      notifications: updated,
      unreadCount: updated.filter((n) => !n.is_read).length,
    })
  },
}))
