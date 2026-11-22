import { createContext, useContext } from 'react'

// Kept apart from AuthContext.jsx so that file only exports a component
// (React Fast Refresh rewires modules that mix components and plain values).
export const AuthContext = createContext(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
