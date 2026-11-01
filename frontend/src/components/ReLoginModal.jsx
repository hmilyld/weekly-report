import { useState } from 'react'
import toast from 'react-hot-toast'
import { login } from '../api'
import Modal from './ui/Modal'
import Button from './ui/Button'
import Field from './ui/Field'

/**
 * Shown when the server restarted and the in-memory key cache is gone:
 * the session is still valid, but data cannot be decrypted until the
 * password is supplied again.
 */
export default function ReLoginModal({ onClose, onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!username || !password) {
      toast.error('请输入用户名和密码')
      return
    }
    setLoading(true)
    try {
      const { data } = await login(username, password)
      localStorage.setItem('token', data.access_token)
      toast.success('已重新登录')
      onSuccess()
    } catch {
      toast.error('登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      size="sm"
      title="需要重新登录"
      description="服务器重启后密钥缓存已清空，重新登录即可恢复数据访问。"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            稍后
          </Button>
          <Button type="submit" form="relogin-form" variant="primary" loading={loading}>
            重新登录
          </Button>
        </>
      }
    >
      <form id="relogin-form" className="form-stack" onSubmit={handleSubmit}>
        <Field label="用户名">
          <input
            className="input"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoFocus
            autoComplete="username"
          />
        </Field>
        <Field label="密码">
          <input
            className="input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </Field>
      </form>
    </Modal>
  )
}
