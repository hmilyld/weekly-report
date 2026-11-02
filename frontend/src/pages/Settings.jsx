import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  Key,
  KeyRound,
  Plus,
  Save,
  Trash2,
  XCircle,
  Zap,
} from 'lucide-react'
import {
  changePassword,
  createToken,
  deleteToken,
  getConfig,
  getTokens,
  testConnection,
  updateConfig,
} from '../api'
import { useAuth } from '../contexts/AuthContext'
import { useConfirm } from '../components/ui/ConfirmProvider'
import { copyText } from '../utils/clipboard'
import { formatDateTime } from '../utils/date'
import Button from '../components/ui/Button'
import Field from '../components/ui/Field'
import PageHeader from '../components/ui/PageHeader'
import { Panel, PanelBody, PanelFooter, PanelHeader } from '../components/ui/Panel'

export default function SettingsPage() {
  const { isAdmin } = useAuth()
  const confirm = useConfirm()

  /* LLM config */
  const [config, setConfig] = useState({ llm_api_url: '', llm_model_name: '', api_key: '' })
  const [loadingConfig, setLoadingConfig] = useState(isAdmin)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  /* Password */
  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' })
  const [changingPwd, setChangingPwd] = useState(false)

  /* Tokens */
  const [tokens, setTokens] = useState([])
  const [loadingTokens, setLoadingTokens] = useState(true)
  const [tokenName, setTokenName] = useState('')
  const [creatingToken, setCreatingToken] = useState(false)
  const [createdToken, setCreatedToken] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [copied, setCopied] = useState(null)

  const loadConfig = useCallback(async () => {
    setLoadingConfig(true)
    try {
      const { data } = await getConfig()
      setConfig({
        llm_api_url: data.llm_api_url || '',
        llm_model_name: data.llm_model_name || '',
        api_key: data.api_key || '',
      })
    } catch {
      toast.error('加载配置失败')
    } finally {
      setLoadingConfig(false)
    }
  }, [])

  const loadTokens = useCallback(async () => {
    setLoadingTokens(true)
    try {
      const { data } = await getTokens()
      setTokens(data)
    } catch {
      toast.error('加载 Token 列表失败')
    } finally {
      setLoadingTokens(false)
    }
  }, [])

  useEffect(() => {
    if (isAdmin) loadConfig()
    loadTokens()
  }, [isAdmin, loadConfig, loadTokens])

  // A masked key must not be sent back; only a freshly typed key is written.
  const configPayload = () => {
    const payload = { ...config }
    if (config.api_key && config.api_key.includes('*')) delete payload.api_key
    return payload
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      await updateConfig(configPayload())
      toast.success('配置已保存')
      loadConfig()
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
      await updateConfig(configPayload())
      const { data } = await testConnection()
      setTestResult(data)
      toast[data.success ? 'success' : 'error'](data.message)
    } catch (err) {
      setTestResult({ success: false, message: err.message || '测试失败' })
    } finally {
      setTesting(false)
    }
  }

  const handleChangePassword = async () => {
    if (!pwd.current) {
      toast.error('请输入当前密码')
      return
    }
    if (pwd.next.length < 8) {
      toast.error('新密码至少 8 位')
      return
    }
    if (!/[A-Za-z]/.test(pwd.next) || !/\d/.test(pwd.next)) {
      toast.error('新密码需要同时包含字母和数字')
      return
    }
    if (pwd.next === pwd.current) {
      toast.error('新密码不能与当前密码相同')
      return
    }
    if (pwd.next !== pwd.confirm) {
      toast.error('两次输入的新密码不一致')
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
      toast.error(err.response?.data?.detail || '修改失败')
    } finally {
      setChangingPwd(false)
    }
  }

  const handleCreateToken = async () => {
    setCreatingToken(true)
    try {
      const { data } = await createToken(tokenName || 'default')
      setCreatedToken(data)
      setTokenName('')
      loadTokens()
      toast.success('Token 已创建')
    } catch (err) {
      toast.error(err.response?.data?.detail || '创建失败')
    } finally {
      setCreatingToken(false)
    }
  }

  const handleDeleteToken = async (token) => {
    const ok = await confirm({
      title: `删除 Token「${token.name}」？`,
      body: '使用这个 Token 的脚本会立刻失去写入权限。',
      confirmLabel: '删除',
      tone: 'danger',
    })
    if (!ok) return
    setDeletingId(token.id)
    try {
      await deleteToken(token.id)
      toast.success('已删除')
      loadTokens()
    } catch {
      toast.error('删除失败')
    } finally {
      setDeletingId(null)
    }
  }

  const handleCopy = async (value) => {
    const ok = await copyText(value)
    if (!ok) {
      toast.error('复制失败，请手动选择')
      return
    }
    setCopied(value)
    toast.success('已复制')
    window.setTimeout(() => setCopied(null), 2000)
  }

  const apiBase = window.location.origin

  return (
    <div className="page page-narrow">
      <PageHeader title="系统配置" subtitle="模型接入、账号安全，以及给脚本用的 API Token。" />

      {isAdmin && (
        <Panel className="page-section">
          <PanelHeader title="大模型配置" icon={Zap} />
          <PanelBody>
            {loadingConfig ? (
              <div className="loading-block">
                <span className="spinner" aria-hidden="true" />
                正在读取配置…
              </div>
            ) : (
              <div className="form-stack">
                <Field label="API 地址" hint="以 /chat/completions 结尾的完整 OpenAI 兼容地址">
                  <input
                    className="input"
                    type="url"
                    placeholder="http://localhost:11434/v1/chat/completions"
                    value={config.llm_api_url}
                    onChange={(event) => setConfig({ ...config, llm_api_url: event.target.value })}
                  />
                </Field>
                <Field label="模型名称" hint="与接口返回的模型标识一致，例如 llama2、gpt-4o-mini">
                  <input
                    className="input"
                    type="text"
                    placeholder="llama2"
                    value={config.llm_model_name}
                    onChange={(event) =>
                      setConfig({ ...config, llm_model_name: event.target.value })
                    }
                  />
                </Field>
                <Field
                  label="API Key"
                  optional
                  hint="留空则不发送 Authorization 头；已保存的密钥显示为掩码。"
                >
                  <input
                    className="input"
                    type="password"
                    placeholder="留空则不发送 Authorization 头"
                    value={config.api_key}
                    onChange={(event) => setConfig({ ...config, api_key: event.target.value })}
                  />
                </Field>
                {testResult && (
                  <div
                    className={`notice ${testResult.success ? 'notice-success' : 'notice-danger'}`}
                    role="status"
                  >
                    {testResult.success ? (
                      <CheckCircle2 size={16} aria-hidden="true" />
                    ) : (
                      <XCircle size={16} aria-hidden="true" />
                    )}
                    <span>{testResult.message}</span>
                  </div>
                )}
              </div>
            )}
          </PanelBody>
          <PanelFooter>
            <Button variant="outline" icon={Zap} onClick={handleTest} loading={testing}>
              测试连接
            </Button>
            <Button variant="primary" icon={Save} onClick={handleSaveConfig} loading={saving}>
              保存配置
            </Button>
          </PanelFooter>
        </Panel>
      )}

      <Panel className="page-section">
        <PanelHeader title="修改密码" icon={KeyRound} />
        <PanelBody>
          <div className="form-stack">
            <Field label="当前密码" hint="修改密码会用当前密码重新加密全部日报、周报、月报与待办。">
              <input
                className="input"
                type="password"
                placeholder="输入当前密码"
                value={pwd.current}
                onChange={(event) => setPwd({ ...pwd, current: event.target.value })}
                autoComplete="current-password"
              />
            </Field>
            <Field
              label="新密码"
              hint="至少 8 位，且同时包含字母和数字；修改后其他设备需要重新登录。"
            >
              <input
                className="input"
                type="password"
                placeholder="输入新密码"
                value={pwd.next}
                onChange={(event) => setPwd({ ...pwd, next: event.target.value })}
                autoComplete="new-password"
              />
            </Field>
            <Field label="确认新密码">
              <input
                className="input"
                type="password"
                placeholder="再次输入新密码"
                value={pwd.confirm}
                onChange={(event) => setPwd({ ...pwd, confirm: event.target.value })}
                autoComplete="new-password"
              />
            </Field>
          </div>
        </PanelBody>
        <PanelFooter>
          <Button
            variant="primary"
            icon={KeyRound}
            onClick={handleChangePassword}
            loading={changingPwd}
            disabled={!pwd.current || !pwd.next || !pwd.confirm}
          >
            修改密码
          </Button>
        </PanelFooter>
      </Panel>

      <Panel className="page-section">
        <PanelHeader title="API Token" icon={Key} />
        <PanelBody>
          <p className="section-note">
            创建 Token 后，脚本可以带着 <code>X-API-Token</code> 直接写入日报，无需登录。
          </p>

          {createdToken && (
            <div className="notice notice-success token-notice">
              <div className="token-notice-body">
                <strong>Token 已创建，只显示这一次</strong>
                <div className="token-reveal">
                  <code>{createdToken.token}</code>
                  <Button
                    variant="ghost"
                    size="sm"
                    iconOnly
                    icon={copied === createdToken.token ? Check : Copy}
                    aria-label="复制 Token"
                    onClick={() => handleCopy(createdToken.token)}
                  />
                </div>
              </div>
            </div>
          )}

          <div className="row token-create">
            <input
              className="input"
              type="text"
              placeholder="Token 名称，例如 ci-bot"
              value={tokenName}
              onChange={(event) => setTokenName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') handleCreateToken()
              }}
              aria-label="Token 名称"
            />
            <Button
              variant="primary"
              icon={Plus}
              onClick={handleCreateToken}
              loading={creatingToken}
            >
              创建
            </Button>
          </div>
        </PanelBody>

        {loadingTokens ? (
          <div className="loading-block">
            <span className="spinner" aria-hidden="true" />
            正在读取 Token…
          </div>
        ) : tokens.length === 0 ? (
          <p className="panel-note">
            还没有 Token。创建后请在脚本里妥善保存，页面上不会再显示完整值。
          </p>
        ) : (
          <div>
            {tokens.map((token) => (
              <div className="record-row" key={token.id}>
                <div className="record-main">
                  <span className="record-icon">
                    <Key size={14} aria-hidden="true" />
                  </span>
                  <div>
                    <div className="record-title">{token.name}</div>
                    <div className="record-meta">
                      <span>创建 {formatDateTime(token.created_at)}</span>
                      <span>
                        {token.last_used_at
                          ? `最近使用 ${formatDateTime(token.last_used_at)}`
                          : '尚未使用'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="record-actions">
                  <Button
                    variant="danger"
                    size="sm"
                    iconOnly
                    icon={Trash2}
                    aria-label={`删除 ${token.name}`}
                    loading={deletingId === token.id}
                    onClick={() => handleDeleteToken(token)}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        <PanelBody className="token-usage">
          <p className="usage-label">
            <ExternalLink size={14} aria-hidden="true" />
            使用示例
          </p>
          <pre className="code-block">{`curl -X POST ${apiBase}/api/v1/external/daily \\
  -H "X-API-Token: <你的Token>" \\
  -H "Content-Type: application/json" \\
  -d '{"content":"今天完成了 xxx","date":"2026-06-10","append":false}'`}</pre>
          <p className="field-hint usage-hint">
            date 与 append 为可选参数：date 默认当天，append 默认 false（覆盖当天内容）。
          </p>
        </PanelBody>
      </Panel>
    </div>
  )
}
