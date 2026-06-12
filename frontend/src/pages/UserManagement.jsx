import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { Users, Plus, Trash2, Shield, User } from 'lucide-react'
import { getUsers, createUser, deleteUser, updateUserRole } from '../api'
import { useAuth } from '../contexts/AuthContext'

export default function UserManagement() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ username: '', password: '', role: 'user' })
  const [creating, setCreating] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const { data } = await getUsers()
      setUsers(data.users)
    } catch (err) {
      toast.error('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setForm({ username: '', password: '', role: 'user' })
    setShowCreate(false)
  }

  // 锁定 body 滚动（弹窗打开时）
  useEffect(() => {
    if (showCreate) {
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [showCreate])

  const handleCreate = async () => {
    if (!form.username.trim()) {
      toast.error('请输入用户名')
      return
    }
    if (form.username.trim().length < 2) {
      toast.error('用户名至少 2 个字符')
      return
    }
    if (!form.password) {
      toast.error('请输入密码')
      return
    }
    if (form.password.length < 8) {
      toast.error('密码至少 8 位')
      return
    }
    setCreating(true)
    try {
      await createUser(form.username.trim(), form.password, form.role)
      toast.success('用户创建成功')
      resetForm()
      loadUsers()
    } catch (err) {
      toast.error(err.response?.data?.detail || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (u) => {
    if (u.id === currentUser?.id) {
      toast.error('不能删除自己')
      return
    }
    if (!confirm(`确定删除用户「${u.username}」？此操作不可恢复。`)) return
    setDeletingId(u.id)
    try {
      await deleteUser(u.id)
      toast.success('已删除')
      loadUsers()
    } catch (err) {
      toast.error(err.response?.data?.detail || '删除失败')
    } finally {
      setDeletingId(null)
    }
  }

  const handleToggleRole = async (u) => {
    const newRole = u.role === 'admin' ? 'user' : 'admin'
    if (u.role === 'admin' && newRole === 'user') {
      const adminCount = users.filter((usr) => usr.role === 'admin').length
      if (adminCount <= 1) {
        toast.error('不能将最后一个管理员降级为普通用户')
        return
      }
    }
    try {
      await updateUserRole(u.id, newRole)
      toast.success(`已将「${u.username}」设为${newRole === 'admin' ? '管理员' : '普通用户'}`)
      loadUsers()
    } catch (err) {
      toast.error(err.response?.data?.detail || '修改失败')
    }
  }

  /* ─── Create User Form ─────────────────────────────── */
  const CreateUserForm = ({ form, setForm, creating, onSubmit, onCancel }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      <div className="form-group" style={{ marginBottom: 0 }}>
        <label className="form-label">用户名</label>
        <input
          type="text"
          className="form-input"
          placeholder="至少 2 个字符"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />
      </div>
      <div className="form-group" style={{ marginBottom: 0 }}>
        <label className="form-label">密码</label>
        <input
          type="password"
          className="form-input"
          placeholder="至少 8 位"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
      </div>
      <div className="form-group" style={{ marginBottom: 0 }}>
        <label className="form-label">角色</label>
        <select
          className="form-input"
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
        >
          <option value="user">普通用户</option>
          <option value="admin">管理员</option>
        </select>
      </div>
      <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
        <button className="btn btn-outline btn-sm" onClick={onCancel}>
          取消
        </button>
        <button className="btn btn-primary btn-sm" onClick={onSubmit} disabled={creating}>
          {creating ? <span className="spinner" /> : '创建'}
        </button>
      </div>
    </div>
  )

  return (
    <>
      <div className="page-header">
        <h2>
          <Users size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
          用户管理
        </h2>
        <p>管理系统用户和权限</p>
      </div>
      <div className="page-body">
        <div className="settings-section">
          <div className="card">
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>用户列表</h3>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => setShowCreate(true)}
              >
                <Plus size={14} /> 创建用户
              </button>
            </div>
            <div className="card-body">
              {loading ? (
                <div className="loading-center" style={{ padding: 'var(--space-6)' }}>
                  <span className="spinner" />
                </div>
              ) : users.length === 0 ? (
                <p
                  style={{
                    fontSize: '0.8125rem',
                    color: 'var(--color-text-muted)',
                    textAlign: 'center',
                    padding: 'var(--space-6)',
                  }}
                >
                  暂无用户
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {users.map((u) => (
                    <div
                      key={u.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: 'var(--space-3) var(--space-4)',
                        background: 'var(--color-bg)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        {u.role === 'admin' ? (
                          <Shield size={18} style={{ color: 'var(--color-primary)' }} />
                        ) : (
                          <User size={18} style={{ color: 'var(--color-text-muted)' }} />
                        )}
                        <div>
                          <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                            {u.username}
                            {u.id === currentUser?.id && (
                              <span
                                style={{
                                  fontSize: '0.75rem',
                                  color: 'var(--color-text-muted)',
                                  marginLeft: '8px',
                                  fontWeight: 400,
                                }}
                              >
                                (当前)
                              </span>
                            )}
                          </span>
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--color-text-muted)',
                              marginTop: '2px',
                            }}
                          >
                            {u.role === 'admin' ? '管理员' : '普通用户'} · 创建于{' '}
                            {new Date(u.created_at).toLocaleDateString('zh-CN')}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {u.id !== currentUser?.id && (
                          <>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={() => handleToggleRole(u)}
                              title={u.role === 'admin' ? '设为普通用户' : '设为管理员'}
                            >
                              {u.role === 'admin' ? (
                                <User size={14} />
                              ) : (
                                <Shield size={14} />
                              )}
                            </button>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={() => handleDelete(u)}
                              disabled={deletingId === u.id}
                              style={{ color: 'var(--color-danger)' }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ─── Create User Modal ──────────────────────── */}
      {showCreate && (
        <div className="modal-overlay" onClick={creating ? undefined : resetForm}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="创建用户"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3>创建用户</h3>
              <button
                className="btn btn-ghost btn-sm"
                onClick={resetForm}
                disabled={creating}
                aria-label="关闭"
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <CreateUserForm
                form={form}
                setForm={setForm}
                creating={creating}
                onSubmit={handleCreate}
                onCancel={resetForm}
              />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
