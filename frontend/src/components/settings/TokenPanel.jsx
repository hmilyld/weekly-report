import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Check, Copy, ExternalLink, Key, Plus, ShieldOff, Trash2 } from 'lucide-react'

import { createToken, deleteToken, getTokens, revokeAllTokens } from '../../api'
import { useConfirm } from '../ui/confirm'
import { copyText } from '../../utils/clipboard'
import { formatDateTime } from '../../utils/date'
import Button from '../ui/Button'
import { Panel, PanelBody, PanelFooter, PanelHeader } from '../ui/Panel'

/** Per-account API tokens for scripts; the full value is shown only once. */
export default function TokenPanel() {
  const confirm = useConfirm()

  const [tokens, setTokens] = useState([])
  const [loadingTokens, setLoadingTokens] = useState(true)
  const [tokenName, setTokenName] = useState('')
  const [creatingToken, setCreatingToken] = useState(false)
  const [createdToken, setCreatedToken] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [revokingAll, setRevokingAll] = useState(false)
  const [copied, setCopied] = useState(null)

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
    loadTokens()
  }, [loadTokens])

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

  const handleRevokeAll = async () => {
    const ok = await confirm({
      title: '吊销全部 Token？',
      body: '所有脚本、手机端和其他设备上的调用会立刻失效，需要重新创建。网页端登录状态不受影响。',
      confirmLabel: '全部吊销',
      tone: 'danger',
    })
    if (!ok) return
    setRevokingAll(true)
    try {
      const { data } = await revokeAllTokens()
      setCreatedToken(null)
      loadTokens()
      if (data?.revoked) {
        toast.success(`已吊销 ${data.revoked} 个 Token`)
      } else {
        toast('没有需要吊销的 Token')
      }
    } catch {
      toast.error('吊销失败')
    } finally {
      setRevokingAll(false)
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

        {/* A real form, so Enter submits natively: the browser already
            suppresses implicit submission while an IME is composing, which a
            keydown handler has to reproduce by hand. */}
        <form
          className="row token-create"
          onSubmit={(event) => {
            event.preventDefault()
            handleCreateToken()
          }}
        >
          <input
            className="input"
            type="text"
            name="token-name"
            placeholder="Token 名称，例如 ci-bot"
            value={tokenName}
            onChange={(event) => setTokenName(event.target.value)}
            aria-label="Token 名称"
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
          />
          <Button type="submit" variant="primary" icon={Plus} loading={creatingToken}>
            创建
          </Button>
        </form>
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
        <pre className="code-block">{`curl -X POST ${apiBase}/api/v1/daily \\
  -H "X-API-Token: <你的Token>" \\
  -H "Content-Type: application/json" \\
  -d '{"content":"今天完成了 xxx","append":true}'`}</pre>
        <p className="field-hint usage-hint">
          date 与 append 为可选参数：date 默认当天，append 默认 false（覆盖当天内容）。Token
          仅可访问日报/周报/月报/待办接口，不能修改账号或系统配置。
        </p>
        <p className="field-hint usage-hint">
          修改密码只会让网页端的登录失效，不会吊销 Token；换机或怀疑泄露时用下方按钮一次性吊销。
        </p>
      </PanelBody>

      <PanelFooter>
        <Button
          variant="danger"
          icon={ShieldOff}
          loading={revokingAll}
          disabled={tokens.length === 0}
          onClick={handleRevokeAll}
        >
          吊销全部 Token
        </Button>
      </PanelFooter>
    </Panel>
  )
}
