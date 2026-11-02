import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { CalendarClock, Check, CheckCircle2, Circle, Pencil, Plus, Trash2, X } from 'lucide-react'
import { createTask, deleteTask, getCompletedTasks, getTasks, updateTask } from '../api'
import useMediaQuery from '../hooks/useMediaQuery'
import { useConfirm } from '../components/ui/ConfirmProvider'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import Field from '../components/ui/Field'
import PageHeader from '../components/ui/PageHeader'

const PAGE_SIZE = 20
const DAY = 1000 * 60 * 60 * 24

const startOfToday = () => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return today
}

const deadlineState = (deadline) => {
  if (!deadline) return 'none'
  const date = new Date(`${deadline}T00:00:00`)
  const today = startOfToday()
  if (date < today) return 'overdue'
  if ((date - today) / DAY < 3) return 'urgent'
  return 'later'
}

const todayInput = () => {
  const today = new Date()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${today.getFullYear()}-${month}-${day}`
}

/* ─── Row editor ───────────────────────────────────────── */

function TaskEditor({ task, onSave, onCancel }) {
  const [content, setContent] = useState(task.content)
  const [deadline, setDeadline] = useState(task.deadline || '')

  const submit = (event) => {
    event.preventDefault()
    if (!content.trim()) {
      toast.error('待办内容不能为空')
      return
    }
    onSave(content.trim(), deadline || null)
  }

  return (
    <form className="task-edit" onSubmit={submit}>
      <input
        className="input"
        value={content}
        onChange={(event) => setContent(event.target.value)}
        placeholder="待办内容"
        aria-label="待办内容"
        autoFocus
      />
      <input
        className="input"
        type="date"
        value={deadline}
        min={todayInput()}
        onChange={(event) => setDeadline(event.target.value)}
        aria-label="截止日期"
      />
      <div className="row">
        <Button type="submit" variant="primary" size="sm" icon={Check} iconOnly aria-label="保存" />
        <Button variant="ghost" size="sm" icon={X} iconOnly aria-label="取消" onClick={onCancel} />
      </div>
    </form>
  )
}

/* ─── Row ──────────────────────────────────────────────── */

function TaskRow({ task, onToggle, onEdit, onDelete }) {
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

/* ─── Composer ─────────────────────────────────────────── */

function TaskComposer({ onAdd }) {
  const [content, setContent] = useState('')
  const [deadline, setDeadline] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    if (!content.trim()) {
      toast.error('请输入待办内容')
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
    <form className="task-composer" onSubmit={submit}>
      <Field label="要做的事">
        <input
          className="input"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="例如：把月报草稿发给组长过一遍"
        />
      </Field>
      <Field label="截止日期" optional>
        <input
          className="input"
          type="date"
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

/* ─── Page ─────────────────────────────────────────────── */

export default function Tasks() {
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const confirm = useConfirm()

  const [tab, setTab] = useState('pending')
  const [pending, setPending] = useState([])
  const [completed, setCompleted] = useState([])
  const [completedTotal, setCompletedTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loaded, setLoaded] = useState(false)
  const [completedLoading, setCompletedLoading] = useState(false)

  const pendingRef = useRef(pending)
  const completedRef = useRef(completed)

  useEffect(() => {
    pendingRef.current = pending
  }, [pending])

  useEffect(() => {
    completedRef.current = completed
  }, [completed])

  const fetchPending = useCallback(async () => {
    try {
      const { data } = await getTasks()
      const tasks = Array.isArray(data) ? data : data.tasks || []
      setPending(tasks.filter((task) => !task.is_completed))
    } catch {
      toast.error('加载待办失败')
    } finally {
      setLoaded(true)
    }
  }, [])

  const fetchCompleted = useCallback(async (targetPage) => {
    setCompletedLoading(true)
    try {
      const { data } = await getCompletedTasks((targetPage - 1) * PAGE_SIZE, PAGE_SIZE)
      setCompleted(data.tasks || [])
      setCompletedTotal(data.total ?? 0)
    } catch {
      toast.error('加载已完成待办失败')
    } finally {
      setCompletedLoading(false)
    }
  }, [])

  const fetchCompletedCount = useCallback(async () => {
    try {
      const { data } = await getCompletedTasks(0, 1)
      setCompletedTotal(data.total ?? 0)
    } catch {
      /* the list view reports the real failure */
    }
  }, [])

  useEffect(() => {
    fetchPending()
    fetchCompletedCount()
  }, [fetchPending, fetchCompletedCount])

  useEffect(() => {
    if (tab === 'completed') fetchCompleted(page)
  }, [tab, page, fetchCompleted])

  const toggleTask = useCallback(async (id, isCompleted) => {
    try {
      await updateTask(id, { is_completed: isCompleted })
      if (isCompleted) {
        const task = pendingRef.current.find((item) => item.id === id)
        setPending((items) => items.filter((item) => item.id !== id))
        setCompletedTotal((total) => total + 1)
        if (task) setCompleted((items) => [{ ...task, is_completed: true }, ...items])
        toast.success('已完成')
      } else {
        const task = completedRef.current.find((item) => item.id === id)
        setCompleted((items) => items.filter((item) => item.id !== id))
        setCompletedTotal((total) => Math.max(0, total - 1))
        if (task) setPending((items) => [{ ...task, is_completed: false }, ...items])
        toast.success('已恢复为未完成')
      }
    } catch {
      toast.error('操作失败')
    }
  }, [])

  const editTask = useCallback(async (id, content, deadline) => {
    try {
      const { data } = await updateTask(id, { content, deadline })
      setPending((items) => items.map((item) => (item.id === id ? data : item)))
      setCompleted((items) => items.map((item) => (item.id === id ? data : item)))
      toast.success('已更新')
    } catch (err) {
      toast.error(err.response?.data?.detail || '更新失败')
    }
  }, [])

  const removeTask = useCallback(
    async (id) => {
      const ok = await confirm({
        title: '删除这条待办？',
        body: '删除后无法恢复，日报与周报不会受影响。',
        confirmLabel: '删除',
        tone: 'danger',
      })
      if (!ok) return
      try {
        await deleteTask(id)
        toast.success('已删除')
        setPending((items) => items.filter((item) => item.id !== id))
        setCompleted((items) => items.filter((item) => item.id !== id))
        if (tab === 'completed') setCompletedTotal((total) => Math.max(0, total - 1))
      } catch {
        toast.error('删除失败')
      }
    },
    [confirm, tab],
  )

  const totalPages = Math.max(1, Math.ceil(completedTotal / PAGE_SIZE))
  const rows = tab === 'pending' ? pending : completed
  const busy = tab === 'completed' && completedLoading

  const filters = [
    { key: 'pending', label: '进行中', count: pending.length },
    { key: 'completed', label: '已完成', count: completedTotal },
  ]

  return (
    <div className="page">
      <PageHeader title="工作待办" subtitle="记下要做的杂事，截止日期会让它自己浮上来。" />

      <TaskComposer onAdd={(task) => setPending((items) => [task, ...items])} />

      {isDesktop ? (
        <div className="tabs" role="group" aria-label="待办筛选">
          {filters.map(({ key, label, count }) => (
            <button
              key={key}
              aria-pressed={tab === key}
              className="tab"
              onClick={() => {
                setTab(key)
                setPage(1)
              }}
            >
              {label}
              <span className="count">{count}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="segmented" role="group" aria-label="待办筛选">
          {filters.map(({ key, label, count }) => (
            <button
              key={key}
              aria-pressed={tab === key}
              className="segmented-item"
              onClick={() => {
                setTab(key)
                setPage(1)
              }}
            >
              {label} {count}
            </button>
          ))}
        </div>
      )}

      <div className="task-body-area">
        {!loaded || busy ? (
          <div className="loading-block">
            <span className="spinner" aria-hidden="true" />
            正在读取待办…
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            title={tab === 'pending' ? '没有进行中的待办' : '还没有已完成的待办'}
            description={
              tab === 'pending'
                ? '在上面输入框里写一件要做的事，按回车即可添加。'
                : '勾选完成的待办会移到这里，方便回头核对。'
            }
          />
        ) : (
          <div className="task-list">
            {rows.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                onToggle={toggleTask}
                onEdit={editTask}
                onDelete={removeTask}
              />
            ))}
          </div>
        )}

        {tab === 'completed' && totalPages > 1 && (
          <div className="pagination">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={page <= 1}
            >
              上一页
            </Button>
            <span>
              {page} / {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              disabled={page >= totalPages}
            >
              下一页
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
