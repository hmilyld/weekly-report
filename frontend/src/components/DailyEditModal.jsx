import { useLayoutEffect, useRef, useState } from 'react'
import { Save, Trash2 } from 'lucide-react'
import Modal from './ui/Modal'
import Button from './ui/Button'
import { continueOrderedList } from '../utils/listInput'

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const FIRST_ITEM = '1. '

// Leading list numbers are structure, not words: leave them out of the count.
const LIST_MARKER_LINE = /^[ \t]{0,3}\d{1,9}[.)][ \t]+/gm

/** The single contiguous region where `after` differs from `before`. */
function changedRegion(before, after) {
  let start = 0
  while (start < before.length && start < after.length && before[start] === after[start]) {
    start += 1
  }
  let beforeEnd = before.length
  let afterEnd = after.length
  while (beforeEnd > start && afterEnd > start && before[beforeEnd - 1] === after[afterEnd - 1]) {
    beforeEnd -= 1
    afterEnd -= 1
  }
  return { start, end: beforeEnd, text: after.slice(start, afterEnd) }
}

/**
 * Apply the computed edit as one native text edit, so the browser keeps its
 * undo history: swapping the value through React state is what makes Ctrl+Z
 * forget everything typed before. Answers false when the command is missing
 * or does not land, and the caller then falls back to the controlled value.
 */
function applyNativeEdit(el, next) {
  if (typeof document.execCommand !== 'function') return false
  const { start, end, text } = changedRegion(el.value, next.value)
  el.setSelectionRange(start, end)
  if (text) document.execCommand('insertText', false, text)
  else document.execCommand('delete')
  return el.value === next.value
}

function describeDate(dateStr) {
  const date = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(date.getTime())) return dateStr
  return `${date.getFullYear()} 年 ${date.getMonth() + 1} 月 ${date.getDate()} 日 · ${WEEKDAY_NAMES[date.getDay()]}`
}

/**
 * Writing a daily record: one textarea, one save, keyboard-first.
 * Ctrl/Cmd+Enter saves, Esc closes without saving. An existing record
 * can also be deleted here — the record row itself carries no actions.
 * The page owns the confirmation, so `deleting` arrives as a prop.
 *
 * An empty record opens as a numbered list ("1. "), and Enter inside an
 * item writes the next number, so one line holds one piece of work.
 */
export default function DailyEditModal({
  date,
  content = '',
  hasReport = false,
  deleting = false,
  onSave,
  onDelete,
  onClose,
}) {
  // An empty record starts as a list, so a typed Enter continues it.
  const [seeded] = useState(() => !content.trim())
  const [text, setText] = useState(() => (seeded ? FIRST_ITEM : content))
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const textareaRef = useRef(null)
  const caretRef = useRef(null)

  const busy = saving || deleting
  // The markers are structure, so "1. " on its own still counts as empty.
  const body = (seeded && text === FIRST_ITEM ? '' : text).replace(LIST_MARKER_LINE, '')
  const hasContent = body.trim().length > 0
  // The seeded "1. " is not a change of its own, and a day without a record
  // has nothing to save while the box holds no text.
  const isDirty = text !== (seeded ? FIRST_ITEM : content) && (hasReport || hasContent)

  // Put the caret after the seeded marker, so typing continues the list.
  useLayoutEffect(() => {
    if (!seeded) return
    const el = textareaRef.current
    if (!el) return
    el.setSelectionRange(el.value.length, el.value.length)
  }, [seeded])

  // Only the fallback path needs this: a native edit leaves the caret where
  // the browser put it, while rewriting the value moves it to the end.
  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el || caretRef.current == null) return
    el.setSelectionRange(caretRef.current, caretRef.current)
    caretRef.current = null
  }, [text])

  const handleSave = async () => {
    if (savingRef.current || busy || !isDirty) return
    savingRef.current = true
    setSaving(true)
    try {
      await onSave(date, text)
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  const handleKeyDown = (event) => {
    // Enter belongs to the IME while a Chinese candidate window is open.
    // keyCode 229 covers Safari, which does not set isComposing.
    if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return

    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      handleSave()
      return
    }

    if (event.key !== 'Enter' || event.shiftKey || event.altKey || event.metaKey || event.ctrlKey) {
      return
    }
    const el = event.currentTarget
    if (el.selectionStart !== el.selectionEnd) return

    const next = continueOrderedList(el.value, el.selectionStart)
    if (!next) return
    event.preventDefault()
    // A native edit keeps the undo history; React state only has to follow.
    // When it does not land, the state rewrite also moves the caret, so the
    // caret is restored after that render instead.
    if (applyNativeEdit(el, next)) el.setSelectionRange(next.caret, next.caret)
    else caretRef.current = next.caret
    setText(next.value)
  }

  return (
    <Modal
      title={hasReport ? '编辑日报' : '记录今天的进展'}
      description={describeDate(date)}
      onClose={onClose}
      dismissible={!busy}
      footer={
        <>
          <div className="modal-footer-lead">
            {hasReport && (
              <Button
                variant="danger"
                icon={Trash2}
                onClick={() => onDelete(date)}
                loading={deleting}
                disabled={saving}
              >
                删除日报
              </Button>
            )}
            <span className="hint">
              {hasContent ? `${body.trim().length} 字` : 'Ctrl / ⌘ + Enter 保存'}
            </span>
          </div>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            取消
          </Button>
          <Button
            variant="primary"
            icon={Save}
            onClick={handleSave}
            loading={saving}
            disabled={!isDirty || deleting}
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
        onKeyDown={handleKeyDown}
        disabled={busy}
        aria-label="日报正文"
        data-autofocus
        autoFocus
      />
    </Modal>
  )
}
