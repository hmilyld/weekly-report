import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { LogIn } from 'lucide-react'
import { login } from '../api'
import { useAuth } from '../contexts/auth'
import Button from '../components/ui/Button'
import Field from '../components/ui/Field'
import PasswordInput from '../components/ui/PasswordInput'
import Wordmark from '../components/ui/Wordmark'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { refreshUser } = useAuth()

  const handleSubmit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!username.trim()) next.username = '请输入用户名'
    if (!password) next.password = '请输入密码'
    setErrors(next)
    if (Object.keys(next).length > 0) {
      // Move focus to the first field that needs attention, so the keyboard and
      // screen-reader user lands on the problem instead of on an alert.
      const first = Object.keys(next)[0]
      event.currentTarget.querySelector(`[name="${first}"]`)?.focus()
      return
    }
    setLoading(true)
    try {
      const { data } = await login(username, password)
      localStorage.setItem('token', data.access_token)
      await refreshUser()
      navigate('/', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth">
      <aside className="auth-aside">
        <Wordmark />
        <div>
          <h2 className="auth-headline">
            每天记一句，
            <br />
            周五交一份周报。
          </h2>
          <ul className="auth-points">
            <li>
              <span>01</span>
              <span>在日历上写当天的进展，一格一条，不建文档。</span>
            </li>
            <li>
              <span>02</span>
              <span>周报与月报由日报自动汇总，可改可复制。</span>
            </li>
            <li>
              <span>03</span>
              <span>也支持用 API Token 从脚本写入，再回到这里审阅。</span>
            </li>
          </ul>
        </div>
        <p className="auth-aside-foot">JWT · 数据按账号加密隔离</p>
      </aside>

      <section className="auth-panel">
        <div className="auth-mobile-brand">
          <Wordmark compact />
        </div>
        <div className="auth-panel-head">
          <h1>登录</h1>
          <p>使用你的账号继续记录日报。</p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <Field label="用户名" error={errors.username}>
            <input
              className="input"
              type="text"
              required
              name="username"
              placeholder="请输入用户名"
              value={username}
              onChange={(event) => {
                setUsername(event.target.value)
                if (errors.username) setErrors((prev) => ({ ...prev, username: undefined }))
              }}
              autoFocus
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
          </Field>
          <Field label="密码" error={errors.password}>
            <PasswordInput
              required
              name="password"
              placeholder="请输入密码"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }))
              }}
              autoComplete="current-password"
            />
          </Field>
          <Button type="submit" variant="primary" size="lg" block icon={LogIn} loading={loading}>
            登录
          </Button>
        </form>
        <p className="auth-switch">
          <span>忘记密码请联系管理员重置。</span>
          <span className="badge">24 小时有效</span>
        </p>
      </section>
    </div>
  )
}
