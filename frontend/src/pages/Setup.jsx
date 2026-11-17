import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle, UserPlus } from 'lucide-react'
import { setupAccount } from '../api'
import { useAuth } from '../contexts/AuthContext'
import Button from '../components/ui/Button'
import Field from '../components/ui/Field'
import PasswordInput from '../components/ui/PasswordInput'
import Wordmark from '../components/ui/Wordmark'

const validate = ({ username, password, confirm }) => {
  const errors = {}
  if (!username.trim()) errors.username = '请输入用户名'
  else if (username.trim().length < 2) errors.username = '用户名至少 2 个字符'
  if (!password) errors.password = '请设置密码'
  else if (password.length < 8) errors.password = '密码至少 8 位'
  else if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
    errors.password = '密码需同时包含字母和数字'
  if (!confirm) errors.confirm = '请再次输入密码'
  else if (password !== confirm) errors.confirm = '两次输入的密码不一致'
  return errors
}

export default function Setup({ onComplete, authError }) {
  const [form, setForm] = useState({ username: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { refreshUser } = useAuth()

  const update = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }))
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const next = validate(form)
    setErrors(next)
    if (Object.keys(next).length > 0) {
      const first = Object.keys(next)[0]
      event.currentTarget.querySelector(`[name="${first}"]`)?.focus()
      return
    }

    setLoading(true)
    try {
      const { data } = await setupAccount(form.username.trim(), form.password)
      localStorage.setItem('token', data.access_token)
      // Load the new admin into the auth context, otherwise the
      // admin-only entries stay hidden until a manual reload.
      await refreshUser()
      toast.success('账户已创建')
      onComplete()
      navigate('/', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.detail || '创建失败')
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
            先建一个账号，
            <br />
            这里是你的记录本。
          </h2>
          <ul className="auth-points">
            <li>
              <span>01</span>
              <span>第一个账号是管理员，可以继续添加团队成员。</span>
            </li>
            <li>
              <span>02</span>
              <span>日报内容加密存储，密钥随登录口令派生。</span>
            </li>
            <li>
              <span>03</span>
              <span>之后可在「系统配置」里接入大模型并测试连接。</span>
            </li>
          </ul>
        </div>
        <p className="auth-aside-foot">首次启动 · 仅需一次</p>
      </aside>

      <section className="auth-panel">
        <div className="auth-mobile-brand">
          <Wordmark compact />
        </div>
        <div className="auth-panel-head">
          <h1>创建管理员账户</h1>
          <p>首次使用，请设置你的账号与密码。</p>
        </div>
        {authError && (
          <div className="notice notice-warning" role="alert">
            <AlertTriangle size={16} aria-hidden="true" />
            <span>无法连接后端 API。请确认服务已启动，且当前地址可以访问 /api。</span>
          </div>
        )}
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <Field label="用户名" hint="至少 2 个字符" error={errors.username}>
            <input
              className="input"
              type="text"
              required
              name="username"
              placeholder="设置用户名"
              value={form.username}
              onChange={update('username')}
              autoFocus
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
          </Field>
          <Field label="密码" hint="至少 8 位，且同时包含字母和数字" error={errors.password}>
            <PasswordInput
              required
              name="password"
              placeholder="设置密码"
              value={form.password}
              onChange={update('password')}
              autoComplete="new-password"
            />
          </Field>
          <Field label="确认密码" error={errors.confirm}>
            <PasswordInput
              required
              name="confirm"
              placeholder="再次输入密码"
              value={form.confirm}
              onChange={update('confirm')}
              autoComplete="new-password"
            />
          </Field>
          <Button type="submit" variant="primary" size="lg" block icon={UserPlus} loading={loading}>
            创建账户
          </Button>
        </form>
      </section>
    </div>
  )
}
