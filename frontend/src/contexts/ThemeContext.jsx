import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const ThemeContext = createContext()

/* The two <meta name="theme-color"> tags carry the system-preference colours.
   Pinning a scheme has to move them too, otherwise the browser chrome keeps
   the OS colour while the page shows the pinned one. Both tags get the same
   value when pinned, so whichever media query wins still yields that colour. */
const THEME_COLOURS = { light: '#ffffff', dark: '#0c0f14' }
const SYSTEM_COLOURS = ['#ffffff', '#0c0f14']

function syncThemeColour(mode) {
  const metas = [...document.querySelectorAll('meta[name="theme-color"]')]
  metas.forEach((meta, index) => {
    meta.content =
      mode === 'system' ? (SYSTEM_COLOURS[index] ?? SYSTEM_COLOURS[0]) : THEME_COLOURS[mode]
  })
}

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

  // Apply the theme to <html>. The attribute drives CSS color-scheme, the
  // <meta> keeps native UI (scrollbars, pickers, the canvas) on the pinned
  // scheme, and theme-color does the same for browser chrome.
  useEffect(() => {
    const root = document.documentElement
    const meta = document.querySelector('meta[name="color-scheme"]')
    if (mode === 'system') {
      root.removeAttribute('data-theme')
      if (meta) meta.content = 'light dark'
    } else {
      root.setAttribute('data-theme', mode)
      if (meta) meta.content = mode
    }
    syncThemeColour(mode)
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
