import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import {
  Save,
  Zap,
  CheckCircle,
  XCircle,
  KeyRound,
  Plus,
  Trash2,
  Copy,
  Check,
  Key,
  ExternalLink,
} from 'lucide-react'
import {
  getConfig,
  updateConfig,
  testConnection,
  changePassword,
  getTokens,
  createToken,
  deleteToken,
} from '../api'
import { useAuth } from '../contexts/AuthContext'

export default function SettingsPage() {
  const { isAdmin } = useAuth()
  // ─── LLM Config ─────────────────────────────────────
  const [config, setConfig] = useState({
    llm_api_url: '',
    llm_model_name: '',
    api_key: '',
  })
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [saving, setSaving] = useState(false)

  // ─── Password ───────────────────────────────────────
  const [pwd, setPwd] = useState({ new_password: '', confirm: '' })
  const [changingPwd, setChangingPwd] = useState(false)

  // ─── Tokens ─────────────────────────────────────────
  const [tokens, setTokens] = useState([])
  const [loadingTokens, setLoadingTokens] = useState(false)
  const [newTokenName, setNewTokenName] = useState('')
  const [creatingToken, setCreatingToken] = useState(false)
  const [deletingTokenId, setDeletingTokenId] = useState(null)
  const [createdToken, setCreatedToken] = useState(null) // Show once
  const [copiedId, setCopiedId] = useState(null)

  useEffect(() => {
    if (isAdmin) {
      loadConfig()
    }
    loadTokens()
  }, [isAdmin])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const { data } = await getConfig()
      setConfig({
        llm_api_url: data.llm_api_url || '',
        llm_model_name: data.llm_model_name || '',
        api_key: data.api_key || '',
      })
    } catch (_) {
      toast.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  const loadTokens = async () => {
    setLoadingTokens(true)
    try {
      const { data } = await getTokens()
      setTokens(data)
    } catch (err) {
      console.error('Failed to load tokens', err)
    } finally {
      setLoadingTokens(false)
    }
  }

  // ─── LLM handlers ──────────────────────────────────
  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      // Only send api_key if user changed it from the masked version
      const payload = { ...config }
      if (config.api_key && config.api_key.includes('*')) {
        delete payload.api_key
      }
      await updateConfig(payload)
      toast.success('配置已保存')
      loadConfig() // Reload to get fresh masked key
    } catch (err) {
      toast.error(err.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      // Save config first (skip masked key)
      const payload = { ...config }
      if (config.api_key && config.api_key.includes('*')) {
        delete payload.api_key
      }
      await updateConfig(payload)
      const { data } = await testConnection()
      setTestResult(data)
      toast[data.success ? 'success' : 'error'](data.message)
    } catch (err) {
      setTestResult({ success: false, message: err.message || '测试失败' })
    } finally {
      setTesting(false)
    }
  }

  // ─── Password handler ──────────────────────────────
  const handleChangePassword = async () => {
    if (!pwd.new_password) {
      toast.error('请输入新密码')
      return
    }
    if (pwd.new_password.length < 6) {
      toast.error('密码至少 6 位')
      return
    }
    if (pwd.new_password !== pwd.confirm) {
      toast.error('两次密码不一致')
      return
    }
    setChangingPwd(true)
    try {
      await changePassword(pwd.new_password)
      toast.success('密码修改成功')
      setPwd({ new_password: '', confirm: '' })
    } catch (err) {
      toast.error(err.response?.data?.detail || '修改失败')
    } finally {
      setChangingPwd(false)
    }
  }

  // ─── Token handlers ────────────────────────────────
  const handleCreateToken = async () => {
    setCreatingToken(true)
    try {
      const { data } = await createToken(newTokenName || 'default')
      setCreatedToken(data)
      setNewTokenName('')
      loadTokens()
      toast.success('Token 创建成功，请保存，只显示一次')
    } catch (err) {
      toast.error(err.response?.data?.detail || '创建失败')
    } finally {
      setCreatingToken(false)
    }
  }

  const handleDeleteToken = async (id, name) => {
    if (!confirm(`确定删除 Token "${name}"？`)) return
    setDeletingTokenId(id)
    try {
      await deleteToken(id)
      toast.success('已删除')
      loadTokens()
    } catch (_) {
      toast.error('删除失败')
    } finally {
      setDeletingTokenId(null)
    }
  }

  const handleCopyToken = async (token) => {
    try {
      await navigator.clipboard.writeText(token)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = token
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopiedId(token)
    toast.success('已复制')
    setTimeout(() => setCopiedId(null), 2000)
  }

  if (loading && isAdmin) {
    return (
      <>
        <div className="page-header">
          <h2>系统配置</h2>
          <p>配置大模型接口参数和账户设置</p>
        </div>
        <div className="page-body">
          <div className="loading-center">
            <span className="spinner spinner-lg" />
          </div>
        </div>
      </>
    )
  }

  const apiBase = window.location.origin

  return (
    <>
      <div className="page-header">
        <h2>系统配置</h2>
        <p>配置大模型接口、账户设置和 API Token</p>
      </div>
      <div className="page-body">
        {/* ─── LLM Config Card (admin only) ─────── */}
        {isAdmin && (
          <div className="settings-section">
            <div className="card">
              <div className="card-header">
                <h3>大模型配置</h3>
              </div>
              <div className="card-body">
                <div className="config-grid">
                  <div className="form-group">
                    <label className="form-label">API 地址</label>
                    <input
                      type="url"
                      className="form-input"
                      placeholder="http://localhost:11434/v1/chat/completions"
                      value={config.llm_api_url}
                      onChange={(e) => setConfig({ ...config, llm_api_url: e.target.value })}
                    />
                    <p
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--color-text-muted)',
                        marginTop: '4px',
                      }}
                    >
                      完整的 OpenAI 兼容接口地址
                    </p>
                  </div>
                  <div className="form-group">
                    <label className="form-label">模型名称</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="llama2"
                      value={config.llm_model_name}
                      onChange={(e) => setConfig({ ...config, llm_model_name: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">API Key（可选）</label>
                    <input
                      type="password"
                      className="form-input"
                      placeholder="留空则不发送 Authorization 头"
                      value={config.api_key}
                      onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                    />
                  </div>
                  {testResult && (
                    <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
                      {testResult.success ? (
                        <CheckCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                      ) : (
                        <XCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                      )}
                      <span>{testResult.message}</span>
                    </div>
                  )}
                  <div className="config-actions">
                    <button
                      className="btn btn-primary"
                      onClick={handleSaveConfig}
                      disabled={saving}
                    >
                      {saving ? (
                        <span className="spinner" />
                      ) : (
                        <>
                          <Save size={16} /> 保存配置
                        </>
                      )}
                    </button>
                    <button className="btn btn-outline" onClick={handleTest} disabled={testing}>
                      {testing ? (
                        <span className="spinner" />
                      ) : (
                        <>
                          <Zap size={16} /> 测试连接
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─── Password Change Card ────────────── */}
        <div className="settings-section">
          <div className="card">
            <div className="card-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <KeyRound size={18} /> 修改密码
              </h3>
            </div>
            <div className="card-body">
              <div className="config-grid">
                <div className="form-group">
                  <label className="form-label">新密码</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="至少 6 位"
                    value={pwd.new_password}
                    onChange={(e) => setPwd({ ...pwd, new_password: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">确认新密码</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="再次输入新密码"
                    value={pwd.confirm}
                    onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })}
                  />
                </div>
                <div className="config-actions">
                  <button
                    className="btn btn-primary"
                    onClick={handleChangePassword}
                    disabled={changingPwd}
                  >
                    {changingPwd ? (
                      <span className="spinner" />
                    ) : (
                      <>
                        <KeyRound size={16} /> 修改密码
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ─── API Token Card ──────────────────── */}
        <div className="settings-section">
          <div className="card">
            <div className="card-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Key size={18} /> API Token
              </h3>
            </div>
            <div className="card-body">
              <p
                style={{
                  fontSize: '0.8125rem',
                  color: 'var(--color-text-secondary)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                创建 Token 后，可通过 API 直接提交日报，无需登录。
              </p>

              {/* Created token notice */}
              {createdToken && (
                <div
                  style={{
                    padding: 'var(--space-4)',
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: 'var(--radius-md)',
                    marginBottom: 'var(--space-4)',
                  }}
                >
                  <p
                    style={{
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: '#166534',
                      marginBottom: '8px',
                    }}
                  >
                    ✅ Token 创建成功（仅显示一次，请妥善保存）
                  </p>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      background: 'white',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #d1fae5',
                    }}
                  >
                    <code
                      style={{
                        flex: 1,
                        fontSize: '0.75rem',
                        wordBreak: 'break-all',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {createdToken.token}
                    </code>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleCopyToken(createdToken.token)}
                    >
                      {copiedId === createdToken.token ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                </div>
              )}

              {/* Create new token */}
              <div
                style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}
              >
                <input
                  type="text"
                  className="form-input"
                  placeholder="Token 名称（可选）"
                  value={newTokenName}
                  onChange={(e) => setNewTokenName(e.target.value)}
                  style={{ flex: 1 }}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateToken()}
                />
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleCreateToken}
                  disabled={creatingToken}
                >
                  {creatingToken ? (
                    <span className="spinner" />
                  ) : (
                    <>
                      <Plus size={14} /> 创建
                    </>
                  )}
                </button>
              </div>

              {/* Token list */}
              {loadingTokens ? (
                <div className="loading-center" style={{ padding: 'var(--space-6)' }}>
                  <span className="spinner" />
                </div>
              ) : tokens.length === 0 ? (
                <p
                  style={{
                    fontSize: '0.8125rem',
                    color: 'var(--color-text-muted)',
                    textAlign: 'center',
                    padding: 'var(--space-6)',
                  }}
                >
                  暂无 Token
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {tokens.map((t) => (
                    <div
                      key={t.id}
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
                      <div>
                        <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{t.name}</span>
                        <span
                          style={{
                            fontSize: '0.75rem',
                            color: 'var(--color-text-muted)',
                            marginLeft: '8px',
                          }}
                        >
                          {new Date(t.created_at).toLocaleDateString('zh-CN')}
                        </span>
                        {t.last_used_at && (
                          <span
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--color-text-muted)',
                              marginLeft: '8px',
                            }}
                          >
                            最近使用: {new Date(t.last_used_at).toLocaleDateString('zh-CN')}
                          </span>
                        )}
                      </div>
                      <button
                        className={`btn btn-ghost btn-sm ${deletingTokenId === t.id ? 'btn-loading' : ''}`}
                        onClick={() => handleDeleteToken(t.id, t.name)}
                        disabled={deletingTokenId === t.id}
                        style={{ color: 'var(--color-danger)' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* API usage example */}
              <div
                style={{
                  marginTop: 'var(--space-5)',
                  padding: 'var(--space-4)',
                  background: 'var(--color-bg)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <p
                  style={{
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    marginBottom: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <ExternalLink size={14} /> 使用示例
                </p>
                <pre
                  style={{
                    fontSize: '0.75rem',
                    lineHeight: 1.6,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--color-text-secondary)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {`curl -X POST ${apiBase}/api/v1/external/daily \\
  -H "X-API-Token: <你的Token>" \\
  -H "Content-Type: application/json" \\
  -d '{"content":"今天完成了xxx","date":"2026-06-10","append":false}'`}
                </pre>
                <p
                  style={{
                    fontSize: '0.6875rem',
                    color: 'var(--color-text-muted)',
                    marginTop: '8px',
                  }}
                >
                  date 和 append 为可选参数。date 默认当天，append 默认 false（覆盖模式）
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
