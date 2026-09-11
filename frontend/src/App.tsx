/**
 * KissanFlow — React Router v6 app with role-based routes.
 */
import React, { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Layout } from '@/components/Layout'
import { RoleGuard } from '@/components/RoleGuard'
import { PageSkeleton } from '@/components/LoadingSkeleton'
import { useAuthStore } from '@/stores/authStore'
import './i18n'

// Lazy-loaded pages
const Landing      = lazy(() => import('@/pages/Landing'))
const Login        = lazy(() => import('@/pages/auth/Login'))
const Register     = lazy(() => import('@/pages/auth/Register'))
const Notifications = lazy(() => import('@/pages/Notifications'))

// Farmer
const FarmerDashboard = lazy(() => import('@/pages/farmer/Dashboard'))
const BookSlot        = lazy(() => import('@/pages/farmer/BookSlot'))
const IVRSim          = lazy(() => import('@/pages/farmer/IVRSim'))
const Grievances      = lazy(() => import('@/pages/farmer/Grievances'))

// Staff
const GateEntry       = lazy(() => import('@/pages/staff/GateEntry'))
const QueueManager    = lazy(() => import('@/pages/staff/QueueManager'))
const TransactionEntry = lazy(() => import('@/pages/staff/TransactionEntry'))

// Officer
const OfficerDashboard = lazy(() => import('@/pages/officer/Dashboard'))

// Govt
const GovtDashboard = lazy(() => import('@/pages/govt/Dashboard'))

function AuthRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  // A signed-in user selecting a landing-page login link should be taken to
  // their role dashboard, not redirected back to the landing page in a loop.
  return isAuthenticated ? <Navigate to="/home" replace /> : <>{children}</>
}

function HomeRedirect() {
  const { user, isAuthenticated } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/" replace />
  const routes: Record<string, string> = {
    FARMER: '/farmer/dashboard',
    MANDI_STAFF: '/staff/gate-entry',
    MANDI_OFFICER: '/officer/dashboard',
    GOVT_ADMIN: '/govt/dashboard',
    CSC_OPERATOR: '/farmer/book-slot',
  }
  return <Navigate to={routes[user?.role || ''] || '/'} replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 4000, style: { borderRadius: '10px', fontFamily: 'Inter, sans-serif' } }} />
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<AuthRoute><Login /></AuthRoute>} />
          <Route path="/register" element={<AuthRoute><Register /></AuthRoute>} />

          {/* Authenticated layout */}
          <Route element={<Layout />}>
            <Route path="/home" element={<HomeRedirect />} />
            <Route path="/notifications" element={<Notifications />} />

            {/* Farmer routes */}
            <Route path="/farmer/dashboard" element={
              <RoleGuard roles={['FARMER', 'CSC_OPERATOR']}><FarmerDashboard /></RoleGuard>
            } />
            <Route path="/farmer/book-slot" element={
              <RoleGuard roles={['FARMER', 'CSC_OPERATOR']}><BookSlot /></RoleGuard>
            } />
            <Route path="/farmer/ivr" element={
              <RoleGuard roles={['FARMER', 'CSC_OPERATOR']}><IVRSim /></RoleGuard>
            } />
            <Route path="/farmer/grievances" element={
              <RoleGuard roles={['FARMER', 'CSC_OPERATOR']}><Grievances /></RoleGuard>
            } />

            {/* Staff routes */}
            <Route path="/staff/gate-entry" element={
              <RoleGuard roles={['MANDI_STAFF', 'MANDI_OFFICER']}><GateEntry /></RoleGuard>
            } />
            <Route path="/staff/queue" element={
              <RoleGuard roles={['MANDI_STAFF', 'MANDI_OFFICER']}><QueueManager /></RoleGuard>
            } />
            <Route path="/staff/transaction/:bookingId" element={
              <RoleGuard roles={['MANDI_STAFF', 'MANDI_OFFICER']}><TransactionEntry /></RoleGuard>
            } />

            {/* Officer routes */}
            <Route path="/officer/dashboard" element={
              <RoleGuard roles={['MANDI_OFFICER']}><OfficerDashboard /></RoleGuard>
            } />

            {/* Govt routes */}
            <Route path="/govt/dashboard" element={
              <RoleGuard roles={['GOVT_ADMIN']}><GovtDashboard /></RoleGuard>
            } />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
