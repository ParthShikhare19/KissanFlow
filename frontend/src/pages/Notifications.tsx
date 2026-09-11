/** Notifications center — paginated, filterable, mark-read. */
import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'react-hot-toast'
import { Bell, CheckCheck, MessageSquare, Phone } from 'lucide-react'
import { get, put } from '@/utils/api'
import { useAuthStore } from '@/stores/authStore'
import { useNotificationStore, AppNotification } from '@/stores/notificationStore'
import clsx from 'clsx'

export default function Notifications() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { setNotifications, markRead, markAllRead } = useNotificationStore()
  const [notifications, setLocal] = useState<AppNotification[]>([])
  const [filter, setFilter] = useState<'ALL' | 'APP' | 'SMS' | 'IVR'>('ALL')
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const load = async () => {
    if (!user) return
    try {
      const channelParam = filter !== 'ALL' ? `&channel=${filter}` : ''
      const res = await get<{ items: AppNotification[]; total: number; page: number; page_size: number }>(
        `/notifications/${user.id}?page=${page}&page_size=20${channelParam}`
      )
      setLocal(res.items)
      setTotal(res.total)
      setNotifications(res.items)
    } catch { toast.error('Failed to load notifications') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [user, page, filter])

  const handleMarkRead = async (id: string) => {
    try {
      await put(`/notifications/${id}/read`)
      markRead(id)
      setLocal((l) => l.map((n) => n.id === id ? { ...n, is_read: true } : n))
    } catch { toast.error('Failed to mark as read') }
  }

  const handleMarkAllRead = async () => {
    notifications.filter((n) => !n.is_read).forEach((n) => handleMarkRead(n.id))
    markAllRead()
    toast.success('All notifications marked as read')
  }

  const FILTERS: Array<{ key: 'ALL' | 'APP' | 'SMS' | 'IVR'; label: string }> = [
    { key: 'ALL', label: t('notifications.filter.all') },
    { key: 'APP', label: t('notifications.filter.app') },
    { key: 'SMS', label: t('notifications.filter.sms') },
    { key: 'IVR', label: t('notifications.filter.ivr') },
  ]

  const CHANNEL_ICONS: Record<string, React.ReactNode> = {
    APP: <Bell className="w-4 h-4" />,
    SMS: <MessageSquare className="w-4 h-4" />,
    IVR: <Phone className="w-4 h-4" />,
  }

  const filtered = filter === 'ALL' ? notifications : notifications.filter((n) => n.channel === filter)
  const totalPages = Math.ceil(total / 20)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="page-title">{t('notifications.title')}</h1>
        {notifications.some((n) => !n.is_read) && (
          <button onClick={handleMarkAllRead} className="btn-secondary text-sm" id="mark-all-read">
            <CheckCheck className="w-4 h-4" /> {t('notifications.markAllRead')}
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => { setFilter(f.key); setPage(1) }}
            className={clsx(
              'flex-1 py-2 rounded-lg text-sm font-semibold transition-all',
              filter === f.key ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
            )}
            id={`filter-${f.key.toLowerCase()}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Notification List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="card p-4 h-20 animate-pulse bg-gray-50" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <Bell className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-400">{t('notifications.empty')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((notif) => (
            <div
              key={notif.id}
              onClick={() => !notif.is_read ? handleMarkRead(notif.id) : undefined}
              className={clsx(
                'card p-4 transition-all cursor-pointer',
                !notif.is_read ? 'border-l-4 border-primary bg-primary-50 hover:shadow-card-hover' : 'hover:bg-gray-50'
              )}
            >
              <div className="flex items-start gap-3">
                {/* Channel Icon */}
                <div className={clsx(
                  'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
                  notif.channel === 'APP' ? 'bg-primary-50 text-primary' :
                  notif.channel === 'SMS' ? 'bg-green-50 text-green-600' : 'bg-orange-50 text-orange-600'
                )}>
                  {CHANNEL_ICONS[notif.channel]}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className={clsx('text-sm font-semibold', !notif.is_read ? 'text-gray-900' : 'text-gray-600')}>
                    {notif.title}
                  </p>
                  <p className="text-sm text-gray-500 mt-0.5 leading-relaxed">{notif.body}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(notif.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    {' · '}{notif.channel}
                  </p>
                </div>

                {/* Unread dot */}
                {!notif.is_read && (
                  <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0 mt-1" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary px-4">
            {t('common.previous')}
          </button>
          <span className="text-sm text-gray-600">
            {t('common.page')} {page} {t('common.of')} {totalPages}
          </span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-secondary px-4">
            {t('common.next')}
          </button>
        </div>
      )}
    </div>
  )
}
