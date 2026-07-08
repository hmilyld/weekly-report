import { useState } from 'react'
import { X } from 'lucide-react'
import { login } from '../api'
import toast from 'react-hot-toast'

export default function ReLoginModal({ onClose, onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username || !password) {
      toast.error('请输入用户名和密码')
      return
    }

    setLoading(true)
    try {
      const { data } = await login(username, password)
      localStorage.setItem('token', data.access_token)
      toast.success('重新登录成功')
      onSuccess()
    } catch {
      toast.error('登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>需要重新登录</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <p style={{ marginBottom: '1rem', color: 'var(--color-text-secondary)' }}>
            服务器已重启，密钥缓存已清空。请重新登录以恢复数据访问。
          </p>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="username">用户名</label>
              <input
                id="username"
                type="text"
                className="form-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">密码</label>
              <input
                id="password"
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                取消
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? '登录中...' : '重新登录'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
