/** Main app layout with sticky navbar, fixed sidebar, and scrollable content area. */
import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '@/stores/authStore'

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { isAuthenticated } = useAuthStore()

  return (
    <div className="min-h-screen bg-muted">
      {/* Top Navbar — fixed, full width, z-50 */}
      <Navbar onMenuClick={isAuthenticated ? () => setSidebarOpen(true) : undefined} />

      <div className="flex pt-16">
        {/* Desktop Sidebar — fixed below navbar, hidden on mobile */}
        {isAuthenticated && (
          <aside className="hidden md:flex flex-col fixed left-0 top-16 bottom-0 w-64 bg-white border-r border-gray-100 shadow-sm z-40 overflow-y-auto">
            <Sidebar isOpen={true} onClose={() => {}} desktopMode />
          </aside>
        )}

        {/* Mobile Sidebar Drawer */}
        {isAuthenticated && (
          <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        )}

        {/* Main Content */}
        <main className={`flex-1 min-w-0 overflow-auto ${isAuthenticated ? 'md:ml-64' : ''}`}>
          <div className="max-w-7xl mx-auto p-4 md:p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
