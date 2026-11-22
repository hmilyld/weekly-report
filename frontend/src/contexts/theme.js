import { createContext, useContext } from 'react'

// Kept apart from ThemeContext.jsx so that file only exports a component
// (React Fast Refresh rewires modules that mix components and plain values).
export const ThemeContext = createContext()

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
