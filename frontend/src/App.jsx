import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, NavLink, useNavigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import {
  FileText,
  Calendar,
  Settings,
  LogOut,
  Sun,
  Moon,
  Monitor,
  CheckSquare,
  Users,
  CalendarDays,
} from 'lucide-react'
import { getAuthStatus } from './api'
import { ThemeProvider, useTheme } from './contexts/ThemeContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ReLoginModal from './components/ReLoginModal'
import { setReLoginHandler } from './api'
import Login from './pages/Login'
import Setup from './pages/Setup'
import DailyReport from './pages/DailyReport'
import WeeklyReport from './pages/WeeklyReport'
import MonthlyReport from './pages/MonthlyReport'
import Tasks from './pages/Tasks'
import SettingsPage from './pages/Settings'
import UserManagement from './pages/UserManagement'
import useMediaQuery from './hooks/useMediaQuery'

/* ─── Route Guards ─────────────────────────────────────── */

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

function SetupGate({ needsSetup, children }) {
  if (needsSetup) return <Navigate to="/setup" replace />
  return children
}

/* ─── Theme Toggle Button ─────────────────────────────── */

const THEME_ICONS = { system: Monitor, light: Sun, dark: Moon }

function ThemeToggle({ className }) {
  const { mode, cycleTheme, label } = useTheme()
  const Icon = THEME_ICONS[mode]
  return (
    <button
      className={`theme-toggle ${className || ''}`}
      onClick={cycleTheme}
      title={label}
      aria-label={label}
    >
      <Icon size={18} />
    </button>
  )
}

/* ─── Top Nav (PC ≥ 1024px) ──────────────────────────── */

function TopNav() {
  const navigate = useNavigate()
  const { user, isAdmin, logout } = useAuth()

  const links = [
    { to: '/', icon: Calendar, label: '日报管理' },
    { to: '/weekly', icon: FileText, label: '周报管理' },
    { to: '/monthly', icon: CalendarDays, label: '月报管理' },
    { to: '/tasks', icon: CheckSquare, label: '工作待办' },
    { to: '/settings', icon: Settings, label: '系统配置' },
  ]

  if (isAdmin) {
    links.push({ to: '/users', icon: Users, label: '用户管理' })
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="top-nav">
      <div className="top-nav-left">
        <span className="top-nav-logo">📋 日周报管理系统</span>
      </div>
      <nav className="top-nav-links">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `top-nav-link ${isActive ? 'active' : ''}`}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      {user && (
        <span className="top-nav-username" title={user.role === 'admin' ? '管理员' : '普通用户'}>
          {user.username}
        </span>
      )}
      <ThemeToggle />
      <button className="top-nav-logout" onClick={handleLogout}>
        <LogOut size={16} />
        退出
      </button>
    </header>
  )
}

/* ─── Mobile Top Bar (< 1024px) ─────────────────────── */

function MobileTopBar() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="mobile-topbar">
      <span className="mobile-topbar-logo">📋 日周报</span>
      <div className="mobile-topbar-actions">
        {user && <span className="mobile-topbar-username">{user.username}</span>}
        <ThemeToggle />
        <button className="mobile-topbar-btn" onClick={handleLogout} aria-label="退出登录">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  )
}

/* ─── Bottom Nav (Mobile < 1024px) ────────────────────── */

function BottomNav() {
  const { isAdmin } = useAuth()

  const links = [
    { to: '/', icon: Calendar, label: '日报' },
    { to: '/weekly', icon: FileText, label: '周报' },
    { to: '/monthly', icon: CalendarDays, label: '月报' },
    { to: '/tasks', icon: CheckSquare, label: '待办' },
    { to: '/settings', icon: Settings, label: '设置' },
  ]

  if (isAdmin) {
    links.push({ to: '/users', icon: Users, label: '管理' })
  }

  return (
    <nav className="bottom-nav">
      {links.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}
        >
          <Icon size={20} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

/* ─── App Layout ───────────────────────────────────────── */

function AppLayout() {
  const { isAdmin } = useAuth()
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const [showReLogin, setShowReLogin] = useState(false)

  // 设置重新登录处理器
  useEffect(() => {
    setReLoginHandler(() => setShowReLogin(true))
    return () => setReLoginHandler(null)
  }, [])

  const handleReLoginSuccess = () => {
    setShowReLogin(false)
    window.location.reload()
  }

  return (
    <div className={`app-layout ${isDesktop ? 'has-topnav' : 'has-bottomnav'}`}>
      {isDesktop ? (
        <TopNav />
      ) : (
        <>
          <MobileTopBar />
          <BottomNav />
        </>
      )}
      <div className="app-content">
        <main className="main-content">
          <Routes>
            <Route path="/" element={<DailyReport />} />
            <Route path="/weekly" element={<WeeklyReport />} />
            <Route path="/monthly" element={<MonthlyReport />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/settings" element={<SettingsPage />} />
            {isAdmin && <Route path="/users" element={<UserManagement />} />}
          </Routes>
        </main>
        <footer className="app-footer">
          © {new Date().getFullYear()} hmilyld · 周报自动生成系统
          {typeof __APP_VERSION__ !== 'undefined' && <span className="app-version"> v{__APP_VERSION__}</span>}
        </footer>
        {showReLogin && <ReLoginModal onClose={() => setShowReLogin(false)} onSuccess={handleReLoginSuccess} />}
      </div>
    </div>
  )
}

/* ─── Root App ─────────────────────────────────────────── */

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
        // API 调用失败时默认显示初始化页面（首次部署场景）
        setNeedsSetup(true)
        setAuthError(true)
      })
  }, [])

  const handleSetupComplete = () => setNeedsSetup(false)

  if (needsSetup === null) {
    return (
      <div className="login-page">
        <span className="spinner spinner-lg" />
      </div>
    )
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Toaster
            position={window.innerWidth < 1024 ? 'bottom-center' : 'top-right'}
            toastOptions={{
              duration: 3000,
              style: {
                fontFamily: 'var(--font-sans)',
                fontSize: '0.8125rem',
                borderRadius: '8px',
              },
            }}
            containerStyle={window.innerWidth < 1024 ? { bottom: 80 } : { top: 20 }}
          />
          <Routes>
            <Route
              path="/setup"
              element={
                needsSetup ? (
                  <Setup onComplete={handleSetupComplete} authError={authError} />
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
      </AuthProvider>
    </ThemeProvider>
  )
}
