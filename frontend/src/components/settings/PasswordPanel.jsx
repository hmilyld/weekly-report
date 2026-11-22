import { useState } from 'react'
import toast from 'react-hot-toast'
import { KeyRound } from 'lucide-react'

import { changePassword } from '../../api'
import Button from '../ui/Button'
import Field from '../ui/Field'
import PasswordInput from '../ui/PasswordInput'
import { Panel, PanelBody, PanelFooter, PanelHeader } from '../ui/Panel'

/** Change the current account's password; 402 lands on the field, not a toast. */
export default function PasswordPanel() {
  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' })
  const [pwdErrors, setPwdErrors] = useState({})
  const [changingPwd, setChangingPwd] = useState(false)

  const updatePwd = (key, value) => {
    setPwd((prev) => ({ ...prev, [key]: value }))
    if (pwdErrors[key]) setPwdErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const handleChangePassword = async (event) => {
    const form = event?.currentTarget
    event?.preventDefault()
    const errors = {}
    if (!pwd.current) errors.current = '请输入当前密码'
    if (!pwd.next) errors.next = '请输入新密码'
    else if (pwd.next.length < 8) errors.next = '新密码至少 8 位'
    else if (!/[A-Za-z]/.test(pwd.next) || !/\d/.test(pwd.next))
      errors.next = '新密码需要同时包含字母和数字'
    else if (pwd.next === pwd.current) errors.next = '新密码不能与当前密码相同'
    if (!pwd.confirm) errors.confirm = '请再次输入新密码'
    else if (pwd.next !== pwd.confirm) errors.confirm = '两次输入的新密码不一致'
    setPwdErrors(errors)
    if (Object.keys(errors).length > 0) {
      const fieldName = {
        current: 'current_password',
        next: 'new_password',
        confirm: 'confirm_password',
      }
      const first = fieldName[Object.keys(errors)[0]]
      form?.querySelector(`[name="${first}"]`)?.focus()
      return
    }
    setChangingPwd(true)
    try {
      const { data } = await changePassword(pwd.current, pwd.next)
      // Changing the password invalidates every existing token; keep this
      // session alive with the fresh one the server just issued.
      if (data?.access_token) localStorage.setItem('token', data.access_token)
      toast.success('密码已修改，其他设备需要重新登录')
      setPwd({ current: '', next: '', confirm: '' })
    } catch (err) {
      // 402 means the session is fine and only the re-supplied password is
      // wrong, so the message belongs on that field, not in a toast. Anything
      // else is a failure of the operation as a whole.
      if (err.response?.status === 402) {
        setPwdErrors({ current: err.response?.data?.detail || '当前密码不正确' })
        form?.querySelector('[name="current_password"]')?.focus()
      } else {
        toast.error(err.response?.data?.detail || '修改失败')
      }
    } finally {
      setChangingPwd(false)
    }
  }

  return (
    <Panel className="page-section">
      <PanelHeader title="修改密码" icon={KeyRound} />
      <form onSubmit={handleChangePassword} noValidate>
        <PanelBody>
          <div className="form-stack">
            <Field
              label="当前密码"
              hint="修改密码会用当前密码重新加密全部日报、周报、月报与待办。"
              error={pwdErrors.current}
            >
              <PasswordInput
                required
                name="current_password"
                placeholder="输入当前密码"
                value={pwd.current}
                onChange={(event) => updatePwd('current', event.target.value)}
                autoComplete="current-password"
              />
            </Field>
            <Field
              label="新密码"
              hint="至少 8 位，且同时包含字母和数字；修改后其他设备需要重新登录。"
              error={pwdErrors.next}
            >
              <PasswordInput
                required
                name="new_password"
                placeholder="输入新密码"
                value={pwd.next}
                onChange={(event) => updatePwd('next', event.target.value)}
                autoComplete="new-password"
              />
            </Field>
            <Field label="确认新密码" error={pwdErrors.confirm}>
              <PasswordInput
                required
                name="confirm_password"
                placeholder="再次输入新密码"
                value={pwd.confirm}
                onChange={(event) => updatePwd('confirm', event.target.value)}
                autoComplete="new-password"
              />
            </Field>
          </div>
        </PanelBody>
        <PanelFooter>
          <Button type="submit" variant="primary" icon={KeyRound} loading={changingPwd}>
            修改密码
          </Button>
        </PanelFooter>
      </form>
    </Panel>
  )
}
