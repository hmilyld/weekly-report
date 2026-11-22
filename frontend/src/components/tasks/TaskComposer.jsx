import { useState } from 'react'
import toast from 'react-hot-toast'
import { Plus } from 'lucide-react'

import { createTask } from '../../api'
import Button from '../ui/Button'
import Field from '../ui/Field'
import { todayInput } from './deadline'

/** New-task form: validates locally, then hands the created task to the page. */
export default function TaskComposer({ onAdd }) {
  const [content, setContent] = useState('')
  const [deadline, setDeadline] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    if (!content.trim()) {
      setError('这件待办还没有内容，写一句要做的事')
      event.currentTarget.querySelector('[name="content"]')?.focus()
      return
    }
    setLoading(true)
    try {
      const { data } = await createTask(content.trim(), deadline || null)
      toast.success('已添加')
      setContent('')
      setDeadline('')
      onAdd(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || '添加失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="task-composer" onSubmit={submit} noValidate>
      <Field label="要做的事" error={error}>
        <input
          className="input"
          name="content"
          value={content}
          onChange={(event) => {
            setContent(event.target.value)
            if (error) setError('')
          }}
          placeholder="例如：把月报草稿发给组长过一遍"
        />
      </Field>
      <Field label="截止日期" optional>
        <input
          className="input"
          type="date"
          name="deadline"
          value={deadline}
          min={todayInput()}
          onChange={(event) => setDeadline(event.target.value)}
        />
      </Field>
      <Button
        type="submit"
        variant="primary"
        icon={Plus}
        loading={loading}
        className="task-composer-submit"
      >
        添加
      </Button>
    </form>
  )
}
