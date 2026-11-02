import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getCurrentUser, logout as logoutApi } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const res = await getCurrentUser()
      setUser(res.data)
    } catch {
      setUser(null)
      localStorage.removeItem('token')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const logout = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (token) {
      // Sign out on the server first, while the token is still attached to
      // requests: this clears the cached encryption key. Only then drop the
      // local session. A failed call still ends the local session.
      try {
        await logoutApi()
      } catch {
        /* the local session ends regardless */
      }
    }
    localStorage.removeItem('token')
    setUser(null)
  }, [])

  const isAdmin = user?.role === 'admin'

  return (
    <AuthContext.Provider value={{ user, isAdmin, loading, refreshUser: fetchUser, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
