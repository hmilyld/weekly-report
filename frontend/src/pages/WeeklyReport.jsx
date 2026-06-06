import { useState, useEffect, useCallback, useRef } from 'react'
import toast from 'react-hot-toast'
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  FileText,
  Copy,
  Pencil,
  Save,
  X,
  Check,
} from 'lucide-react'
import { getWeeklyReport, generateWeeklyReport, updateWeeklyReport } from '../api'
import { getMonday, formatDate, addDays, formatWeekRange } from '../utils/date'

export default function WeeklyReport() {
  const [currentMonday, setCurrentMonday] = useState(() => getMonday(new Date()))
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  // Edit state
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)

  // Copy state
  const [copied, setCopied] = useState(false)
  const copyTimerRef = useRef(null)

  useEffect(() => {
    return () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
    }
  }, [])

  // When switching weeks, try to load existing report (don't auto-generate)
  const loadReport = useCallback(async () => {
    setLoading(true)
    setReport(null)
    setEditing(false)
    const ws = formatDate(currentMonday)
    try {
      const { data } = await getWeeklyReport(ws)
      setReport(data)
    } catch (err) {
      // 404 = not generated yet, which is fine
      if (err.response?.status !== 404) {
        toast.error(err.response?.data?.detail || '加载周报失败')
      }
      setReport(null)
    } finally {
      setLoading(false)
    }
  }, [currentMonday])

  useEffect(() => {
    loadReport()
  }, [loadReport])

  // Generate
  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const ws = formatDate(currentMonday)
      const { data } = await generateWeeklyReport(ws)
      setReport(data)
      toast.success('周报生成成功')
    } catch (err) {
      toast.error(err.response?.data?.detail || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  // Edit
  const startEdit = () => {
    setEditContent(report.content)
    setEditing(true)
  }

  const cancelEdit = () => {
    setEditing(false)
    setEditContent('')
  }

  const saveEdit = async () => {
    if (!editContent.trim()) {
      toast.error('内容不能为空')
      return
    }
    setSaving(true)
    try {
      const ws = formatDate(currentMonday)
      const { data } = await updateWeeklyReport(ws, editContent)
      setReport(data)
      setEditing(false)
      toast.success('已保存')
    } catch (err) {
      toast.error(err.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // Copy
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(report.content)
    } catch {
      // Fallback for insecure contexts
      const ta = document.createElement('textarea')
      ta.value = report.content
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    toast.success('已复制到剪贴板')
    if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
    copyTimerRef.current = setTimeout(() => setCopied(false), 2000)
  }

  return (
    <>
      <div className="page-header">
        <h2>周报管理</h2>
        <p>基于日报自动生成每周工作总结</p>
      </div>
      <div className="page-body">
        {/* Week Navigation */}
        <div className="week-nav">
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setCurrentMonday(addDays(currentMonday, -7))}
            aria-label="上一周"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="week-nav-label">{formatWeekRange(currentMonday)}</span>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setCurrentMonday(addDays(currentMonday, 7))}
            aria-label="下一周"
          >
            <ChevronRight size={18} />
          </button>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => setCurrentMonday(getMonday(new Date()))}
          >
            本周
          </button>
        </div>

        {/* Loading */}
        {loading ? (
          <div className="loading-center">
            <span className="spinner spinner-lg" />
          </div>
        ) : report && !editing ? (
          /* ─── Report View ──────────────────────── */
          <div className="card">
            <div className="card-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} />
                周报内容
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <span className="badge">{report.model_name}</span>
              </div>
            </div>
            <div className="card-body">
              <div className="weekly-content">{report.content}</div>
              <p
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  marginTop: 'var(--space-3)',
                }}
              >
                生成时间: {new Date(report.generated_at).toLocaleString('zh-CN')}
              </p>
            </div>
            {/* Action buttons */}
            <div
              style={{
                padding: 'var(--space-3) var(--space-5)',
                borderTop: '1px solid var(--color-border)',
                display: 'flex',
                gap: 'var(--space-3)',
                flexWrap: 'wrap',
              }}
            >
              <button className="btn btn-outline btn-sm" onClick={startEdit}>
                <Pencil size={14} /> 编辑
              </button>
              <button className="btn btn-outline btn-sm" onClick={handleCopy}>
                {copied ? (
                  <>
                    <Check size={14} /> 已复制
                  </>
                ) : (
                  <>
                    <Copy size={14} /> 复制
                  </>
                )}
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleGenerate}
                disabled={generating}
                style={{ marginLeft: 'auto' }}
              >
                {generating ? (
                  <>
                    <span className="spinner" /> 生成中...
                  </>
                ) : (
                  <>
                    <RefreshCw size={14} /> 重新生成
                  </>
                )}
              </button>
            </div>
          </div>
        ) : editing ? (
          /* ─── Edit Mode ───────────────────────── */
          <div className="card">
            <div className="card-header">
              <h3>编辑周报</h3>
            </div>
            <div className="card-body">
              <textarea
                className="form-input weekly-edit-textarea"
                rows={14}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                style={{ minHeight: '280px', fontSize: '14px', lineHeight: '1.8' }}
              />
            </div>
            <div
              style={{
                padding: 'var(--space-3) var(--space-5)',
                borderTop: '1px solid var(--color-border)',
                display: 'flex',
                gap: 'var(--space-3)',
                justifyContent: 'flex-end',
              }}
            >
              <button className="btn btn-outline btn-sm" onClick={cancelEdit}>
                <X size={14} /> 取消
              </button>
              <button className="btn btn-primary btn-sm" onClick={saveEdit} disabled={saving}>
                {saving ? (
                  <span className="spinner" />
                ) : (
                  <>
                    <Save size={14} /> 保存
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          /* ─── Empty State ─────────────────────── */
          <div style={{ textAlign: 'center' }}>
            <div className="empty-state">
              <FileText size={48} />
              <p>该周暂无周报</p>
              <p style={{ marginTop: '4px' }}>请先填写日报，然后点击下方按钮生成</p>
            </div>
            <button
              className="btn btn-accent"
              onClick={handleGenerate}
              disabled={generating}
              style={{ maxWidth: '280px' }}
            >
              {generating ? (
                <>
                  <span className="spinner" /> 生成中...
                </>
              ) : (
                <>
                  <RefreshCw size={16} /> 生成周报
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </>
  )
}
