import { useState, useRef, useEffect } from 'react'
import { Save } from 'lucide-react'

export default function DailyEditModal({ date, content, onSave, onClose }) {
  const [text, setText] = useState(content)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false) // ← ref for synchronous guard
  const textareaRef = useRef(null)

  useEffect(() => {
    const timer = setTimeout(() => textareaRef.current?.focus(), 100)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  const handleSave = async () => {
    if (savingRef.current) return // ← synchronous check, no stale closure
    savingRef.current = true
    setSaving(true)
    try {
      await onSave(date, text)
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape' && !savingRef.current) onClose()
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault() // ← prevent browser newline insert
      handleSave()
    }
  }

  return (
    <div className="modal-overlay" onClick={saving ? undefined : onClose} onKeyDown={handleKeyDown}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>编辑日报 · {date}</h3>
          <button
            className="btn btn-ghost btn-sm"
            onClick={onClose}
            disabled={saving}
            aria-label="关闭"
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            ✕
          </button>
        </div>
        <div className="modal-body">
          <div className="form-group" style={{ marginBottom: 0 }}>
            <textarea
              ref={textareaRef}
              className="form-input"
              rows={8}
              placeholder="记录今天的工作内容..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={saving}
              onKeyDown={(e) => {
                // Handle Ctrl+Enter directly on textarea for reliability
                if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                  e.preventDefault()
                  handleSave()
                }
              }}
              style={{
                minHeight: '180px',
                fontSize: '16px',
              }}
            />
            <p
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                marginTop: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '4px',
              }}
            >
              <span>Ctrl+Enter 保存</span>
              <span>Esc 取消</span>
            </p>
          </div>
        </div>
        <div className="modal-footer">
          <button
            className="btn btn-outline"
            onClick={onClose}
            disabled={saving}
            style={{ flex: 1 }}
          >
            取消
          </button>
          <button
            className={`btn btn-primary ${saving ? 'btn-loading' : ''}`}
            onClick={handleSave}
            disabled={saving}
            style={{ flex: 1 }}
          >
            {saving ? (
              <>
                <span className="spinner" /> 保存中...
              </>
            ) : (
              <>
                <Save size={16} /> 保存
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
