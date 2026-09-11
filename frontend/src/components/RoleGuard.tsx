/** Role guard — redirects if user lacks required role. */
import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

type Role = 'FARMER' | 'MANDI_STAFF' | 'MANDI_OFFICER' | 'GOVT_ADMIN' | 'CSC_OPERATOR'

interface RoleGuardProps {
  roles: Role[]
  children: React.ReactNode
  redirectTo?: string
}

export function RoleGuard({ roles, children, redirectTo = '/login' }: RoleGuardProps) {
  const { user, isAuthenticated } = useAuthStore()

  if (!isAuthenticated || !user) {
    return <Navigate to={redirectTo} replace />
  }

  if (!roles.includes(user.role as Role)) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
