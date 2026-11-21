import { useState } from 'react'
import { CalendarClock, CheckCircle2, Circle, Pencil, Trash2 } from 'lucide-react'

import Button from '../ui/Button'
import TaskEditor from './TaskEditor'
import { deadlineState } from './deadline'

/** One task: toggle, inline edit, delete — with the deadline badge. */
export default function TaskRow({ task, onToggle, onEdit, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const state = task.is_completed ? 'none' : deadlineState(task.deadline)

  if (editing) {
    return (
      <TaskEditor
        task={task}
        onSave={(content, deadline) => {
          onEdit(task.id, content, deadline)
          setEditing(false)
        }}
        onCancel={() => setEditing(false)}
      />
    )
  }

  const handleToggle = () => {
    setRemoving(true)
    window.setTimeout(() => onToggle(task.id, !task.is_completed), 220)
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await onDelete(task.id)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div
      className={['task-row', task.is_completed && 'is-done', removing && 'is-removing']
        .filter(Boolean)
        .join(' ')}
    >
      <button
        className="task-toggle"
        onClick={handleToggle}
        aria-label={task.is_completed ? '标记为未完成' : '标记为已完成'}
        aria-pressed={task.is_completed}
      >
        {task.is_completed ? <CheckCircle2 size={20} /> : <Circle size={20} />}
      </button>

      <div className="task-body">
        <span className="task-text">{task.content}</span>
        {task.deadline && (
          <span className="task-meta">
            <span
              className={`task-deadline ${state === 'overdue' ? 'is-overdue' : ''} ${
                state === 'urgent' ? 'is-urgent' : ''
              }`
                .replace(/\s+/g, ' ')
                .trim()}
            >
              <CalendarClock size={12} aria-hidden="true" />
              {task.deadline}
              {state === 'overdue' && ' · 已逾期'}
              {state === 'urgent' && ' · 即将到期'}
            </span>
          </span>
        )}
      </div>

      <div className="task-actions">
        <Button
          variant="ghost"
          size="sm"
          iconOnly
          icon={Pencil}
          aria-label="编辑待办"
          onClick={() => setEditing(true)}
        />
        <Button
          variant="danger"
          size="sm"
          iconOnly
          icon={Trash2}
          aria-label="删除待办"
          loading={deleting}
          onClick={handleDelete}
        />
      </div>
    </div>
  )
}
