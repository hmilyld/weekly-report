import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Plus, Shield, Trash2, User } from 'lucide-react'
import { createUser, deleteUser, getUsers, updateUserRole } from '../api'
import { formatDateTime } from '../utils/date'
import { useAuth } from '../contexts/AuthContext'
import { useConfirm } from '../components/ui/ConfirmProvider'
import Button from '../components/ui/Button'
import Field from '../components/ui/Field'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import { Panel, PanelBody, PanelHeader } from '../components/ui/Panel'

export default function UserManagement() {
  const { user: currentUser } = useAuth()
  const confirm = useConfirm()

  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [form, setForm] = useState({ username: '', password: '', role: 'user' })
  const [showCreate, setShowCreate] = useState(false)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getUsers()
      setUsers(data.users)
    } catch {
      toast.error('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const closeCreate = () => {
    setShowCreate(false)
    setForm({ username: '', password: '', role: 'user' })
  }

  const handleCreate = async (event) => {
    event?.preventDefault()
    if (!form.username.trim()) {
      toast.error('请输入用户名')
      return
    }
    if (form.username.trim().length < 2) {
      toast.error('用户名至少 2 个字符')
      return
    }
    if (form.password.length < 8) {
      toast.error('密码至少 8 位')
      return
    }
    setCreating(true)
    try {
      await createUser(form.username.trim(), form.password, form.role)
      toast.success('用户已创建')
      closeCreate()
      loadUsers()
    } catch (err) {
      toast.error(err.response?.data?.detail || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (target) => {
    if (target.id === currentUser?.id) {
      toast.error('不能删除自己的账号')
      return
    }
    const ok = await confirm({
      title: `删除用户「${target.username}」？`,
      body: '该账号的日报、周报与月报会一并移除，此操作不可恢复。',
      confirmLabel: '删除用户',
      tone: 'danger',
    })
    if (!ok) return
    setBusyId(target.id)
    try {
      await deleteUser(target.id)
      toast.success('已删除')
      loadUsers()
    } catch (err) {
      toast.error(err.response?.data?.detail || '删除失败')
    } finally {
      setBusyId(null)
    }
  }

  const handleToggleRole = async (target) => {
    const nextRole = target.role === 'admin' ? 'user' : 'admin'
    if (target.role === 'admin') {
      const admins = users.filter((item) => item.role === 'admin').length
      if (admins <= 1) {
        toast.error('至少要保留一名管理员')
        return
      }
    }
    setBusyId(target.id)
    try {
      await updateUserRole(target.id, nextRole)
      toast.success(`「${target.username}」已设为${nextRole === 'admin' ? '管理员' : '普通用户'}`)
      loadUsers()
    } catch (err) {
      toast.error(err.response?.data?.detail || '修改失败')
    } finally {
      setBusyId(null)
    }
  }

  const adminCount = users.filter((item) => item.role === 'admin').length

  return (
    <div className="page">
      <PageHeader
        title="用户管理"
        subtitle={`共 ${users.length} 个账号，其中 ${adminCount} 名管理员。每个人的日报互不可见。`}
        actions={
          <Button variant="primary" icon={Plus} onClick={() => setShowCreate(true)}>
            创建用户
          </Button>
        }
      />

      <Panel>
        <PanelHeader title="用户列表" />
        {loading ? (
          <div className="loading-block">
            <span className="spinner" aria-hidden="true" />
            正在读取用户…
          </div>
        ) : users.length === 0 ? (
          <PanelBody>
            <p className="section-note">还没有其他账号。创建用户后，他们可以各自记录日报。</p>
          </PanelBody>
        ) : (
          <div>
            {users.map((item) => {
              const isSelf = item.id === currentUser?.id
              const isAdmin = item.role === 'admin'
              return (
                <div className="record-row" key={item.id}>
                  <div className="record-main">
                    <span className="record-icon">
                      {isAdmin ? (
                        <Shield size={14} aria-hidden="true" />
                      ) : (
                        <User size={14} aria-hidden="true" />
                      )}
                    </span>
                    <div>
                      <div className="record-title">
                        {item.username}
                        {isSelf && <span className="badge">当前</span>}
                        <span className={`badge ${isAdmin ? 'badge-accent' : ''}`.trim()}>
                          {isAdmin ? '管理员' : '普通用户'}
                        </span>
                      </div>
                      <div className="record-meta">
                        <span>创建于 {formatDateTime(item.created_at)}</span>
                        <span>
                          {item.last_login_at
                            ? `最近登录 ${formatDateTime(item.last_login_at)}`
                            : '从未登录'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="record-actions">
                    {!isSelf && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          iconOnly
                          icon={isAdmin ? User : Shield}
                          aria-label={isAdmin ? '设为普通用户' : '设为管理员'}
                          title={isAdmin ? '设为普通用户' : '设为管理员'}
                          loading={busyId === item.id}
                          onClick={() => handleToggleRole(item)}
                        />
                        <Button
                          variant="danger"
                          size="sm"
                          iconOnly
                          icon={Trash2}
                          aria-label={`删除 ${item.username}`}
                          onClick={() => handleDelete(item)}
                        />
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Panel>

      {showCreate && (
        <Modal
          title="创建用户"
          description="新用户会收到用户名和初始密码，首次登录后建议修改密码。"
          onClose={closeCreate}
          dismissible={!creating}
          footer={
            <>
              <Button variant="ghost" onClick={closeCreate} disabled={creating}>
                取消
              </Button>
              <Button
                variant="primary"
                icon={Plus}
                onClick={handleCreate}
                loading={creating}
                disabled={!form.username || !form.password}
              >
                创建
              </Button>
            </>
          }
        >
          <form className="form-stack" onSubmit={handleCreate}>
            <Field label="用户名" hint="至少 2 个字符">
              <input
                className="input"
                type="text"
                placeholder="例如 zhangsan"
                value={form.username}
                onChange={(event) => setForm({ ...form, username: event.target.value })}
                autoComplete="off"
              />
            </Field>
            <Field label="初始密码" hint="至少 8 位">
              <input
                className="input"
                type="password"
                placeholder="设置初始密码"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                autoComplete="new-password"
              />
            </Field>
            <Field label="角色" hint="管理员可以配置模型、管理账号与 Token。">
              <select
                className="select"
                value={form.role}
                onChange={(event) => setForm({ ...form, role: event.target.value })}
              >
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
            </Field>
            <button type="submit" hidden aria-hidden="true" tabIndex={-1} />
          </form>
        </Modal>
      )}
    </div>
  )
}
