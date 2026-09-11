/** Top navbar with logo, language toggle, and notification bell. */
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bell, Globe, LogOut, Menu } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useNotificationStore } from '@/stores/notificationStore'

interface NavbarProps {
  onMenuClick?: () => void
}

export function Navbar({ onMenuClick }: NavbarProps) {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuthStore()
  const { unreadCount } = useNotificationStore()
  const navigate = useNavigate()

  const toggleLanguage = () => {
    const next = i18n.language === 'en' ? 'hi' : 'en'
    i18n.changeLanguage(next)
    localStorage.setItem('kissanflow-lang', next)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-b border-gray-200/80 shadow-[0_4px_20px_rgba(15,23,42,0.04)]">
      <div className="flex items-center justify-between h-16 px-4 md:px-6 lg:px-8">
        {/* Left: Menu + Logo */}
        <div className="flex items-center gap-3">
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="md:hidden p-2 rounded-lg hover:bg-primary-50 transition-colors"
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5 text-gray-600" />
            </button>
          )}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-sm shadow-primary/20">
              <span className="text-white font-bold text-sm">AS</span>
            </div>
            <span className="font-bold text-gray-900 text-lg hidden sm:block">{t('app.name')}</span>
          </Link>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold text-gray-600 hover:bg-primary-50 hover:text-primary-dark transition-colors"
            aria-label={t('nav.language')}
          >
            <Globe className="w-4 h-4" />
            <span>{i18n.language === 'en' ? 'हिं' : 'EN'}</span>
          </button>

          {user && (
            <>
              {/* Notification Bell */}
              <Link
                to="/notifications"
                className="relative p-2 rounded-lg hover:bg-primary-50 transition-colors"
                aria-label={t('nav.notifications')}
              >
                <Bell className="w-5 h-5 text-gray-600" strokeWidth={2.2} />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Link>

              {/* User Info + Logout */}
              <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-gray-200">
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-900 leading-tight">{user.name}</p>
                  <p className="text-xs text-gray-500 capitalize">{user.role.replace('_', ' ').toLowerCase()}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-lg hover:bg-red-50 hover:text-red-600 transition-colors text-gray-500"
                  aria-label={t('nav.logout')}
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
