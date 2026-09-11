/**
 * Zustand auth store — manages user, tokens, and login/logout.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '@/utils/api'

export interface User {
  id: string
  name: string
  mobile: string
  role: 'FARMER' | 'MANDI_STAFF' | 'MANDI_OFFICER' | 'GOVT_ADMIN' | 'CSC_OPERATOR'
  assigned_centre_id?: string | null
  created_at: string
  farmer_profile?: {
    id: string
    village: string
    district: string
    state: string
    land_holding: number
    bank_ifsc_code?: string
    registry_number?: string
  } | null
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (mobile: string, password: string, role?: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  setTokens: (access: string, refresh: string, user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      setTokens: (access, refresh, user) => {
        localStorage.setItem('access_token', access)
        localStorage.setItem('refresh_token', refresh)
        set({ accessToken: access, refreshToken: refresh, user, isAuthenticated: true })
      },

      login: async (mobile, password, role) => {
        set({ isLoading: true })
        try {
          const res = await api.post('/auth/login', { mobile, password, role })
          const { access_token, refresh_token, user } = res.data.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
            user,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (err) {
          set({ isLoading: false })
          throw err
        }
      },

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
      },

      refreshUser: async () => {
        try {
          const res = await api.get('/auth/me')
          set({ user: res.data.data })
        } catch {
          get().logout()
        }
      },
    }),
    {
      name: 'kissanflow-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
