import { useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import {
  Calendar,
  CalendarDays,
  CheckSquare,
  FileText,
  LogOut,
  Monitor,
  Moon,
  Settings,
  Sun,
  Users,
} from 'lucide-react'

import { getAuthStatus, setReLoginHandler } from './api'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider, useTheme } from './contexts/ThemeContext'
import useMediaQuery from './hooks/useMediaQuery'
import ReLoginModal from './components/ReLoginModal'
import Wordmark from './components/ui/Wordmark'
import { ConfirmProvider } from './components/ui/ConfirmProvider'

import DailyReport from './pages/DailyReport'
import Login from './pages/Login'
import MonthlyReport from './pages/MonthlyReport'
import SettingsPage from './pages/Settings'
import Setup from './pages/Setup'
import Tasks from './pages/Tasks'
import UserManagement from './pages/UserManagement'
import WeeklyReport from './pages/WeeklyReport'

/* ─── Route guards ─────────────────────────────────────── */

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

function SetupGate({ needsSetup, children }) {
  if (needsSetup) return <Navigate to="/setup" replace />
  return children
}

/* ─── Navigation model (one source for both navs) ──────── */

const NAV = [
  { to: '/', icon: Calendar, label: '日报', desktopLabel: '日报管理' },
  { to: '/weekly', icon: FileText, label: '周报', desktopLabel: '周报管理' },
  { to: '/monthly', icon: CalendarDays, label: '月报', desktopLabel: '月报管理' },
  { to: '/tasks', icon: CheckSquare, label: '待办', desktopLabel: '工作待办' },
  { to: '/settings', icon: Settings, label: '设置', desktopLabel: '系统配置' },
  { to: '/users', icon: Users, label: '管理', desktopLabel: '用户管理', adminOnly: true },
]

/* ─── Theme control ────────────────────────────────────── */

const THEME_ICONS = { system: Monitor, light: Sun, dark: Moon }

function ThemeToggle() {
  const { mode, cycleTheme, label } = useTheme()
  const Icon = THEME_ICONS[mode]
  return (
    <button className="icon-btn" onClick={cycleTheme} title={label} aria-label={`主题：${label}`}>
      <Icon size={17} />
    </button>
  )
}

/* ─── Desktop top bar ──────────────────────────────────── */

function TopBar() {
  const navigate = useNavigate()
  const { user, isAdmin, logout } = useAuth()
  const links = NAV.filter((item) => !item.adminOnly || isAdmin)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <NavLink to="/" aria-label="日周报管理系统 · 首页">
        <Wordmark />
      </NavLink>
      <nav className="topbar-links" aria-label="主导航">
        {links.map(({ to, icon: Icon, desktopLabel }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className="topbar-link"
            aria-label={desktopLabel}
          >
            <Icon size={15} aria-hidden="true" />
            <span>{desktopLabel}</span>
          </NavLink>
        ))}
      </nav>
      <div className="topbar-account">
        {user && <span className="topbar-user">{user.username}</span>}
        <ThemeToggle />
        <button className="icon-btn" onClick={handleLogout} title="退出登录" aria-label="退出登录">
          <LogOut size={17} />
        </button>
      </div>
    </header>
  )
}

/* ─── Mobile chrome ────────────────────────────────────── */

function MobileBar() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="mobile-bar">
      <NavLink to="/" aria-label="日周报 · 首页">
        <Wordmark compact />
      </NavLink>
      <div className="mobile-bar-actions">
        {user && <span className="topbar-user">{user.username}</span>}
        <ThemeToggle />
        <button className="icon-btn" onClick={handleLogout} aria-label="退出登录">
          <LogOut size={17} />
        </button>
      </div>
    </header>
  )
}

function TabBar() {
  const { isAdmin } = useAuth()
  const links = NAV.filter((item) => !item.adminOnly || isAdmin)

  return (
    <nav className="tabbar" aria-label="主导航">
      {links.map(({ to, icon: Icon, label }) => (
        <NavLink key={to} to={to} end={to === '/'} className="tabbar-item">
          <Icon size={19} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

/* ─── Shell ────────────────────────────────────────────── */

function AppLayout() {
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const [showReLogin, setShowReLogin] = useState(false)

  useEffect(() => {
    setReLoginHandler(() => setShowReLogin(true))
    return () => setReLoginHandler(null)
  }, [])

  return (
    <div className="app-shell">
      {isDesktop ? (
        <TopBar />
      ) : (
        <>
          <MobileBar />
          <TabBar />
        </>
      )}
      <main className="app-main">
        <Routes>
          <Route path="/" element={<DailyReport />} />
          <Route path="/weekly" element={<WeeklyReport />} />
          <Route path="/monthly" element={<MonthlyReport />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="app-footer">
        <span>日周报管理系统 · 由日报自动汇成周报与月报</span>
        {typeof __APP_VERSION__ !== 'undefined' && (
          <span className="app-version">v{__APP_VERSION__}</span>
        )}
      </footer>
      {showReLogin && (
        <ReLoginModal
          onClose={() => setShowReLogin(false)}
          onSuccess={() => {
            setShowReLogin(false)
            window.location.reload()
          }}
        />
      )}
    </div>
  )
}

/* ─── Root ─────────────────────────────────────────────── */

export default function App() {
  const [needsSetup, setNeedsSetup] = useState(null)
  const [authError, setAuthError] = useState(false)

  useEffect(() => {
    getAuthStatus()
      .then(({ data }) => {
        setNeedsSetup(data.needs_setup)
        setAuthError(false)
      })
      .catch(() => {
        // The API is unreachable — show setup with the connection warning.
        setNeedsSetup(true)
        setAuthError(true)
      })
  }, [])

  if (needsSetup === null) {
    return (
      <div className="auth">
        <div className="auth-panel">
          <div className="loading-block">
            <span className="spinner" aria-hidden="true" />
            正在连接服务…
          </div>
        </div>
      </div>
    )
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <ConfirmProvider>
          <BrowserRouter>
            <Toaster
              position="top-center"
              gutter={8}
              toastOptions={{
                duration: 3000,
                style: {
                  fontFamily: 'var(--font-sans)',
                  fontSize: 'var(--text-md)',
                  color: 'var(--color-text)',
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border-strong)',
                  borderRadius: 'var(--radius-sm)',
                  boxShadow: 'var(--shadow-md)',
                  padding: '10px 14px',
                  maxWidth: 'min(92vw, 420px)',
                },
                success: {
                  iconTheme: { primary: 'var(--color-success)', secondary: 'var(--white)' },
                },
                error: { iconTheme: { primary: 'var(--color-danger)', secondary: 'var(--white)' } },
              }}
              containerClassName="toast-container"
            />
            <Routes>
              <Route
                path="/setup"
                element={
                  needsSetup ? (
                    <Setup onComplete={() => setNeedsSetup(false)} authError={authError} />
                  ) : (
                    <Navigate to="/login" replace />
                  )
                }
              />
              <Route
                path="/login"
                element={
                  <SetupGate needsSetup={needsSetup}>
                    <Login />
                  </SetupGate>
                }
              />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <SetupGate needsSetup={needsSetup}>
                      <AppLayout />
                    </SetupGate>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
        </ConfirmProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
