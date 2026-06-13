import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const ThemeContext = createContext()

/**
 * Theme modes:
 *  - "system" : follow OS prefers-color-scheme (default)
 *  - "light"  : force light
 *  - "dark"   : force dark
 *
 * Stored in localStorage as "theme_mode".
 * Applied to <html data-theme="light|dark"> (omitted when "system").
 */
export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    try {
      return localStorage.getItem('theme_mode') || 'system'
    } catch {
      return 'system'
    }
  })

  // Apply data-theme attribute to <html>
  useEffect(() => {
    const root = document.documentElement
    if (mode === 'system') {
      root.removeAttribute('data-theme')
    } else {
      root.setAttribute('data-theme', mode)
    }
    try {
      localStorage.setItem('theme_mode', mode)
    } catch {
      /* ignore */
    }
  }, [mode])

  // Cycle: system → light → dark → system
  const cycleTheme = useCallback(() => {
    setMode((prev) => {
      if (prev === 'system') return 'light'
      if (prev === 'light') return 'dark'
      return 'system'
    })
  }, [])

  const label = mode === 'system' ? '跟随系统' : mode === 'dark' ? '暗色模式' : '亮色模式'

  return (
    <ThemeContext.Provider value={{ mode, cycleTheme, label }}>{children}</ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
