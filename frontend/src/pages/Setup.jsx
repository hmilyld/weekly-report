import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle, UserPlus } from 'lucide-react'
import { setupAccount } from '../api'
import Button from '../components/ui/Button'
import Field from '../components/ui/Field'
import Wordmark from '../components/ui/Wordmark'

export default function Setup({ onComplete, authError }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!username.trim()) {
      toast.error('请输入用户名')
      return
    }
    if (username.trim().length < 2) {
      toast.error('用户名至少 2 个字符')
      return
    }
    if (password.length < 8) {
      toast.error('密码至少 8 位')
      return
    }
    if (password !== confirm) {
      toast.error('两次密码不一致')
      return
    }

    setLoading(true)
    try {
      const { data } = await setupAccount(username.trim(), password)
      localStorage.setItem('token', data.access_token)
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
        <form className="auth-form" onSubmit={handleSubmit}>
          <Field label="用户名" hint="至少 2 个字符">
            <input
              className="input"
              type="text"
              placeholder="设置用户名"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoFocus
              autoComplete="username"
            />
          </Field>
          <Field label="密码" hint="至少 8 位">
            <input
              className="input"
              type="password"
              placeholder="设置密码"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
            />
          </Field>
          <Field label="确认密码">
            <input
              className="input"
              type="password"
              placeholder="再次输入密码"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
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
