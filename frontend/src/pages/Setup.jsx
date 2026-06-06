import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { setupAccount } from '../api'

export default function Setup({ onComplete }) {
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
    if (password.length < 6) {
      toast.error('密码至少 6 位')
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
      // Tell parent setup is done, then navigate
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
              placeholder="至少 6 位"
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
