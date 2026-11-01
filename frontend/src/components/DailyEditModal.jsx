import { useRef, useState } from 'react'
import { Save } from 'lucide-react'
import Modal from './ui/Modal'
import Button from './ui/Button'

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function describeDate(dateStr) {
  const date = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(date.getTime())) return dateStr
  return `${date.getFullYear()} 年 ${date.getMonth() + 1} 月 ${date.getDate()} 日 · ${WEEKDAY_NAMES[date.getDay()]}`
}

/**
 * Writing a daily record: one textarea, one save, keyboard-first.
 * Ctrl/Cmd+Enter saves, Esc closes without saving.
 */
export default function DailyEditModal({ date, content, onSave, onClose }) {
  const [text, setText] = useState(content ?? '')
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const textareaRef = useRef(null)

  const handleSave = async () => {
    if (savingRef.current) return
    savingRef.current = true
    setSaving(true)
    try {
      await onSave(date, text)
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  const hasContent = text.trim().length > 0
  const isDirty = text !== (content ?? '')

  return (
    <Modal
      title={content ? '编辑日报' : '记录今天的进展'}
      description={describeDate(date)}
      onClose={onClose}
      dismissible={!saving}
      footer={
        <>
          <span className="hint grow">
            {hasContent ? `${text.trim().length} 字` : 'Ctrl / ⌘ + Enter 保存'}
          </span>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            取消
          </Button>
          <Button
            variant="primary"
            icon={Save}
            onClick={handleSave}
            loading={saving}
            disabled={!isDirty}
          >
            保存
          </Button>
        </>
      }
    >
      <textarea
        ref={textareaRef}
        className="textarea"
        rows={9}
        placeholder="今天做了什么？一两句就够，比如：修了导出 CSV 的日期偏移，原因是时区没按本地取。"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            event.preventDefault()
            handleSave()
          }
        }}
        disabled={saving}
        aria-label="日报正文"
        autoFocus
      />
    </Modal>
  )
}
