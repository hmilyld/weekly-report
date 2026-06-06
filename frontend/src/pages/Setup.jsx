import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle } from 'lucide-react'
import { setupAccount } from '../api'

export default function Setup({ onComplete, authError }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()

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
      toast.success('账户创建成功！')
      onComplete()
      navigate('/', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.detail || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>📋 欢迎使用周报系统</h1>
        <p className="subtitle">首次使用，请设置您的账户</p>
        {authError && (
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              padding: '10px 12px',
              marginBottom: '16px',
              background: '#fef9c3',
              border: '1px solid #fde047',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.8125rem',
              color: '#854d0e',
              lineHeight: 1.5,
            }}
          >
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>无法连接后端 API，请确认服务已启动且可通过当前地址访问。</span>
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">用户名</label>
            <input
              type="text"
              className="form-input"
              placeholder="设置用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
            />
          </div>
          <div className="form-group">
            <label className="form-label">密码</label>
            <input
              type="password"
              className="form-input"
              placeholder="至少 8 位，包含字母和数字"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          <div className="form-group">
            <label className="form-label">确认密码</label>
            <input
              type="password"
              className="form-input"
              placeholder="再次输入密码"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            style={{ width: '100%' }}
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : '创建账户'}
          </button>
        </form>
      </div>
    </div>
  )
}
