/** Role-based sidebar navigation. Renders as a full-height panel (desktop) or drawer (mobile). */
import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import {
  LayoutDashboard, CalendarPlus, Phone, AlertCircle,
  Bell, ScanLine, Users, BarChart3, LogOut, X
} from 'lucide-react'
import clsx from 'clsx'

const FARMER_NAV = [
  { to: '/farmer/dashboard', label: 'nav.dashboard', icon: LayoutDashboard },
  { to: '/farmer/book-slot', label: 'nav.bookSlot', icon: CalendarPlus },
  { to: '/farmer/ivr', label: 'nav.ivr', icon: Phone },
  { to: '/farmer/grievances', label: 'nav.grievances', icon: AlertCircle },
  { to: '/notifications', label: 'nav.notifications', icon: Bell },
]

const STAFF_NAV = [
  { to: '/staff/gate-entry', label: 'staff.gateEntry.title', icon: ScanLine },
  { to: '/staff/queue', label: 'staff.queue.title', icon: Users },
  { to: '/notifications', label: 'nav.notifications', icon: Bell },
]

const OFFICER_NAV = [
  { to: '/officer/dashboard', label: 'officer.dashboard.title', icon: LayoutDashboard },
  { to: '/staff/gate-entry', label: 'staff.gateEntry.title', icon: ScanLine },
  { to: '/staff/queue', label: 'staff.queue.title', icon: Users },
  { to: '/notifications', label: 'nav.notifications', icon: Bell },
]

const GOVT_NAV = [
  { to: '/govt/dashboard', label: 'govt.dashboard.title', icon: BarChart3 },
  { to: '/notifications', label: 'nav.notifications', icon: Bell },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  /** When true, renders nav-only (no overlay, no drawer animation, no own header) */
  desktopMode?: boolean
}

export function Sidebar({ isOpen, onClose, desktopMode = false }: SidebarProps) {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const getNav = () => {
    switch (user?.role) {
      case 'FARMER': return FARMER_NAV
      case 'MANDI_STAFF': return STAFF_NAV
      case 'MANDI_OFFICER': return OFFICER_NAV
      case 'GOVT_ADMIN': return GOVT_NAV
      case 'CSC_OPERATOR': return FARMER_NAV
      default: return []
    }
  }

  const navItems = getNav()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Desktop mode — render just the nav content inline (Layout wraps it in <aside>)
  if (desktopMode) {
    return (
      <div className="flex flex-col h-full">
        {/* User Info */}
        {user && (
          <div className="px-5 py-4 bg-primary-50/70 border-b border-primary-100">
            <p className="font-semibold text-gray-900 text-sm truncate">{user.name}</p>
            <p className="text-xs text-primary capitalize mt-0.5">
              {user.role.replace(/_/g, ' ').toLowerCase()}
            </p>
          </div>
        )}

        {/* Nav Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all',
                    isActive
                      ? 'bg-primary text-white shadow-md shadow-primary/15'
                      : 'text-gray-600 hover:bg-primary-50 hover:text-primary-dark'
                  )
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{t(item.label)}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Logout */}
        <div className="p-3 border-t border-gray-100">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-all"
          >
            <LogOut className="w-4 h-4" />
            <span>{t('nav.logout')}</span>
          </button>
        </div>
      </div>
    )
  }

  // Mobile drawer mode
  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <aside
        className={clsx(
          'fixed left-0 top-0 bottom-0 z-50 w-72 bg-white shadow-2xl',
          'flex flex-col border-r border-gray-200 transition-transform duration-300',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Drawer Header with logo + close */}
        <div className="flex items-center justify-between h-16 px-5 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-white font-bold text-xs">AS</span>
            </div>
            <span className="font-bold text-gray-900">KissanFlow</span>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100" aria-label="Close menu">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* User Info */}
        {user && (
          <div className="px-5 py-4 bg-primary-50/70 border-b border-primary-100">
            <p className="font-semibold text-gray-900 text-sm truncate">{user.name}</p>
            <p className="text-xs text-primary capitalize mt-0.5">
              {user.role.replace(/_/g, ' ').toLowerCase()}
            </p>
          </div>
        )}

        {/* Nav Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all',
                    isActive
                      ? 'bg-primary text-white shadow-md shadow-primary/15'
                      : 'text-gray-600 hover:bg-primary-50 hover:text-primary-dark'
                  )
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{t(item.label)}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Logout */}
        <div className="p-3 border-t border-gray-100">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-all"
          >
            <LogOut className="w-4 h-4" />
            <span>{t('nav.logout')}</span>
          </button>
        </div>
      </aside>
    </>
  )
}
