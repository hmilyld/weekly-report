import { useState } from 'react'
import toast from 'react-hot-toast'
import { login } from '../api'
import Modal from './ui/Modal'
import Button from './ui/Button'
import Field from './ui/Field'
import PasswordInput from './ui/PasswordInput'

/**
 * Shown when the server restarted and the in-memory key cache is gone:
 * the session is still valid, but data cannot be decrypted until the
 * password is supplied again.
 */
export default function ReLoginModal({ onClose, onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!username) next.username = '请输入用户名'
    if (!password) next.password = '请输入密码'
    setErrors(next)
    if (Object.keys(next).length > 0) {
      event.currentTarget.querySelector(`[name="${Object.keys(next)[0]}"]`)?.focus()
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
      <form id="relogin-form" className="form-stack" onSubmit={handleSubmit} noValidate>
        <Field label="用户名" error={errors.username}>
          <input
            className="input"
            type="text"
            required
            name="username"
            value={username}
            onChange={(event) => {
              setUsername(event.target.value)
              if (errors.username) setErrors((prev) => ({ ...prev, username: undefined }))
            }}
            autoFocus
            data-autofocus
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
            value={password}
            onChange={(event) => {
              setPassword(event.target.value)
              if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }))
            }}
            autoComplete="current-password"
          />
        </Field>
      </form>
    </Modal>
  )
}
