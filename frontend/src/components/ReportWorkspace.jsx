import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { Check, Copy, FileText, Pencil, RefreshCw, Save, X } from 'lucide-react'
import Button from './ui/Button'
import { Panel, PanelBody, PanelFooter, PanelHeader } from './ui/Panel'
import EmptyState from './ui/EmptyState'
import { copyText } from '../utils/clipboard'
import { formatDateTime } from '../utils/date'

/**
 * The weekly and monthly surfaces are the same surface at two scales:
 * one period, one generated report, the same four actions.
 * This component owns that shape so both pages stay identical.
 */
export default function ReportWorkspace({
  cadence,
  periodLabel,
  periodNode,
  report,
  loading,
  generating,
  saving,
  onGenerate,
  onSave,
  emptyHint,
  regenerateLabel = '重新生成',
  generateLabel,
}) {
  const isWeekly = cadence === 'weekly'
  const noun = isWeekly ? '周报' : '月报'
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [copied, setCopied] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => () => clearTimeout(timerRef.current), [])

  // Leaving a period discards an open editor rather than saving it silently.
  useEffect(() => {
    setEditing(false)
    setDraft('')
  }, [periodLabel])

  const startEdit = () => {
    setDraft(report?.content ?? '')
    setEditing(true)
  }

  const cancelEdit = () => {
    setEditing(false)
    setDraft('')
  }

  const submitEdit = async () => {
    if (!draft.trim()) {
      toast.error('内容不能为空')
      return
    }
    const ok = await onSave(draft)
    if (ok) setEditing(false)
  }

  const handleCopy = async () => {
    const ok = await copyText(report?.content ?? '')
    if (!ok) {
      toast.error('复制失败，请手动选择文本')
      return
    }
    setCopied(true)
    toast.success(`已复制${noun}`)
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <>
        {periodNode}
        <Panel>
          <div className="loading-block">
            <span className="spinner" aria-hidden="true" />
            正在读取{noun}…
          </div>
        </Panel>
      </>
    )
  }

  if (editing) {
    return (
      <>
        {periodNode}
        <Panel>
          <PanelHeader title={`编辑${noun}`} />
          <PanelBody>
            <textarea
              className="textarea report-editor"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
                  event.preventDefault()
                  submitEdit()
                }
                if (event.key === 'Escape') cancelEdit()
              }}
              aria-label={`${noun}正文`}
              autoFocus
            />
          </PanelBody>
          <PanelFooter>
            <Button variant="ghost" icon={X} onClick={cancelEdit} disabled={saving}>
              取消
            </Button>
            <Button variant="primary" icon={Save} onClick={submitEdit} loading={saving}>
              保存
            </Button>
          </PanelFooter>
        </Panel>
      </>
    )
  }

  if (!report) {
    return (
      <>
        {periodNode}
        <Panel>
          <EmptyState
            icon={FileText}
            title={`${isWeekly ? '这一周' : '这个月'}还没有${noun}`}
            description={emptyHint}
            actions={
              <Button variant="accent" icon={RefreshCw} onClick={onGenerate} loading={generating}>
                {generateLabel || `生成${noun}`}
              </Button>
            }
          />
        </Panel>
      </>
    )
  }

  return (
    <>
      {periodNode}
      <Panel>
        <PanelHeader
          title={
            <>
              <span
                className={`chip-band ${isWeekly ? 'is-weekly' : 'is-monthly'}`.trim()}
                aria-hidden="true"
              />
              {noun}内容
            </>
          }
          actions={
            <>
              <Button variant="ghost" size="sm" icon={Pencil} onClick={startEdit}>
                编辑
              </Button>
              <Button variant="ghost" size="sm" icon={copied ? Check : Copy} onClick={handleCopy}>
                {copied ? '已复制' : '复制'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                icon={RefreshCw}
                onClick={onGenerate}
                loading={generating}
              >
                {regenerateLabel}
              </Button>
            </>
          }
        />
        <PanelBody>
          <div className="report-text">{report.content}</div>
          <div className="report-meta">
            <span>生成于 {formatDateTime(report.generated_at)}</span>
            {report.model_name && <span>· {report.model_name}</span>}
            {report.updated_at && report.updated_at !== report.generated_at && (
              <span>· 编辑于 {formatDateTime(report.updated_at)}</span>
            )}
          </div>
        </PanelBody>
      </Panel>
    </>
  )
}
