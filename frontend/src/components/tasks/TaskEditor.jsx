import { useId, useState } from 'react'
import { Check, X } from 'lucide-react'

import Button from '../ui/Button'
import { todayInput } from './deadline'

/** Inline editor for one row; validation stays local until the save succeeds. */
export default function TaskEditor({ task, onSave, onCancel }) {
  const [content, setContent] = useState(task.content)
  const [deadline, setDeadline] = useState(task.deadline || '')
  const [error, setError] = useState('')
  // Two rows can be in edit mode at once, so the message id must not be a
  // constant: a duplicated id makes the second field describe the first row's
  // error.
  const errorId = useId()

  const submit = (event) => {
    event.preventDefault()
    if (!content.trim()) {
      setError('待办内容不能为空')
      event.currentTarget.querySelector('[name="content"]')?.focus()
      return
    }
    onSave(content.trim(), deadline || null)
  }

  return (
    <form className="task-edit" onSubmit={submit} noValidate>
      <input
        className="input"
        name="content"
        value={content}
        onChange={(event) => {
          setContent(event.target.value)
          if (error) setError('')
        }}
        placeholder="待办内容"
        aria-label="待办内容"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        autoFocus
      />
      <input
        className="input"
        type="date"
        name="deadline"
        value={deadline}
        min={todayInput()}
        onChange={(event) => setDeadline(event.target.value)}
        aria-label="截止日期"
      />
      <div className="row">
        <Button type="submit" variant="primary" size="sm" icon={Check} iconOnly aria-label="保存" />
        <Button variant="ghost" size="sm" icon={X} iconOnly aria-label="取消" onClick={onCancel} />
      </div>
      {error && (
        <p className="field-error task-edit-error" id={errorId} role="alert">
          {error}
        </p>
      )}
    </form>
  )
}
