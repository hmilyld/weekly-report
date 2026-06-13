import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Check, Pencil, Trash2, Plus, X, CheckCircle, Circle, ListFilter } from 'lucide-react'
import { getTasks, getCompletedTasks, createTask, updateTask, deleteTask } from '../api'
import useMediaQuery from '../hooks/useMediaQuery'

/* ─── Helpers ──────────────────────────────────────────── */

const PAGE_SIZE = 20

function isOverdue(deadline) {
  if (!deadline) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const deadlineDate = new Date(deadline + 'T00:00:00')
  return deadlineDate < today
}

function isUrgent(deadline) {
  if (!deadline) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const deadlineDate = new Date(deadline + 'T00:00:00')
  const diffDays = Math.ceil((deadlineDate - today) / (1000 * 60 * 60 * 24))
  return diffDays >= 0 && diffDays < 3
}

/* ─── useTaskList Hook ──────────────────────────────────── */

function useTaskList() {
  const [pendingTasks, setPendingTasks] = useState([])
  const [completedTasks, setCompletedTasks] = useState([])
  const [completedTotal, setCompletedTotal] = useState(0)
  const [completedPage, setCompletedPage] = useState(1)
  const [completedLoading, setCompletedLoading] = useState(false)

  const fetchPendingTasks = useCallback(async () => {
    try {
      const { data } = await getTasks()
      setPendingTasks(data.filter((t) => !t.is_completed))
    } catch {
      toast.error('加载待办失败')
    }
  }, [])

  const fetchCompletedTasks = useCallback(async (page) => {
    setCompletedLoading(true)
    try {
      const offset = (page - 1) * PAGE_SIZE
      const { data } = await getCompletedTasks(offset, PAGE_SIZE)
      setCompletedTasks(data.tasks)
      setCompletedTotal(data.total)
    } catch {
      toast.error('加载已完成待办失败')
    } finally {
      setCompletedLoading(false)
    }
  }, [])

  const fetchCompletedCount = useCallback(async () => {
    try {
      const { data } = await getCompletedTasks(0, 1)
      setCompletedTotal(data.total)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchPendingTasks()
    fetchCompletedCount()
  }, [fetchPendingTasks, fetchCompletedCount])

  const handleToggle = async (taskId, isCompleted) => {
    try {
      await updateTask(taskId, { is_completed: isCompleted })
      toast.success(isCompleted ? '已完成' : '已恢复')
      if (isCompleted) {
        const task = pendingTasks.find((t) => t.id === taskId)
        setPendingTasks((prev) => prev.filter((t) => t.id !== taskId))
        setCompletedTotal((prev) => prev + 1)
        if (task) setCompletedTasks((prev) => [task, ...prev])
      } else {
        const task = completedTasks.find((t) => t.id === taskId)
        setCompletedTasks((prev) => prev.filter((t) => t.id !== taskId))
        setCompletedTotal((prev) => prev - 1)
        if (task) setPendingTasks((prev) => [task, ...prev])
      }
    } catch {
      toast.error('操作失败')
    }
  }

  const handleEdit = async (taskId, content, deadline, currentTab) => {
    try {
      const { data } = await updateTask(taskId, { content, deadline })
      toast.success('已更新')
      if (currentTab === 'pending') {
        setPendingTasks((prev) => prev.map((t) => (t.id === taskId ? data : t)))
      } else {
        setCompletedTasks((prev) => prev.map((t) => (t.id === taskId ? data : t)))
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || '更新失败')
    }
  }

  const handleDelete = (taskId, currentTab) => {
    if (currentTab === 'pending') {
      setPendingTasks((prev) => prev.filter((t) => t.id !== taskId))
    } else {
      setCompletedTasks((prev) => prev.filter((t) => t.id !== taskId))
      setCompletedTotal((prev) => prev - 1)
    }
  }

  const handleAdd = (newTask) => {
    setPendingTasks((prev) => [newTask, ...prev])
  }

  return {
    pendingTasks,
    completedTasks,
    completedTotal,
    completedPage,
    setCompletedPage,
    completedLoading,
    fetchPendingTasks,
    fetchCompletedTasks,
    handleToggle,
    handleEdit,
    handleDelete,
    handleAdd,
    totalPages: Math.ceil(completedTotal / PAGE_SIZE),
  }
}

/* ─── Inline Edit Row ──────────────────────────────────── */

function InlineEditRow({ content, deadline, onSave, onCancel }) {
  const [editContent, setEditContent] = useState(content)
  const [editDeadline, setEditDeadline] = useState(deadline || '')
  const today = new Date().toISOString().split('T')[0]

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!editContent.trim()) {
      toast.error('待办内容不能为空')
      return
    }
    onSave(editContent.trim(), editDeadline || null)
  }

  return (
    <form className="task-edit-row" onSubmit={handleSubmit}>
      <input
        className="form-input task-edit-input"
        value={editContent}
        onChange={(e) => setEditContent(e.target.value)}
        placeholder="待办内容"
        autoFocus
      />
      <input
        className="form-input task-edit-deadline"
        type="date"
        value={editDeadline}
        min={today}
        onChange={(e) => setEditDeadline(e.target.value)}
      />
      <div className="task-edit-actions">
        <button type="submit" className="btn btn-accent btn-sm" title="保存">
          <Check size={15} />
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel} title="取消">
          <X size={15} />
        </button>
      </div>
    </form>
  )
}

/* ─── Task Item ─────────────────────────────────────────── */

function TaskItem({ task, onToggle, onDelete, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [animatingOut, setAnimatingOut] = useState(false)

  const handleEdit = (content, deadline) => {
    onEdit(task.id, content, deadline)
    setEditing(false)
  }

  const handleDelete = async () => {
    if (!confirm('确定删除该待办？')) return
    setDeleting(true)
    try {
      await deleteTask(task.id)
      toast.success('已删除')
      onDelete(task.id)
    } catch {
      toast.error('删除失败')
    } finally {
      setDeleting(false)
    }
  }

  const handleToggle = () => {
    setAnimatingOut(true)
    setTimeout(() => {
      onToggle(task.id, !task.is_completed)
    }, 300)
  }

  if (editing) {
    return (
      <InlineEditRow
        content={task.content}
        deadline={task.deadline}
        onSave={handleEdit}
        onCancel={() => setEditing(false)}
      />
    )
  }

  const overdue = !task.is_completed && isOverdue(task.deadline)
  const urgent = !task.is_completed && !overdue && isUrgent(task.deadline)

  return (
    <div
      className={`task-item ${task.is_completed ? 'completed' : ''} ${overdue ? 'overdue' : ''} ${urgent ? 'urgent' : ''} ${animatingOut ? 'task-removing' : ''}`}
    >
      <button
        className="task-checkbox"
        onClick={handleToggle}
        title={task.is_completed ? '标记为未完成' : '标记为已完成'}
      >
        {task.is_completed ? <CheckCircle size={20} /> : <Circle size={20} />}
      </button>
      <div className="task-content">
        <span className="task-text">
          {urgent && <span className="task-urgent-star">*</span>}
          {task.content}
        </span>
        {task.deadline && (
          <span className={`task-deadline ${overdue ? 'overdue' : ''} ${urgent ? 'urgent' : ''}`}>
            截止: {task.deadline}
          </span>
        )}
      </div>
      <div className="task-actions">
        <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)} title="编辑">
          <Pencil size={15} />
        </button>
        <button
          className={`btn btn-ghost btn-sm ${deleting ? 'btn-loading' : ''}`}
          onClick={handleDelete}
          disabled={deleting}
          title="删除"
          style={{ color: 'var(--color-danger)' }}
        >
          {deleting ? <span className="spinner" /> : <Trash2 size={15} />}
        </button>
      </div>
    </div>
  )
}

/* ─── Add Task Row ──────────────────────────────────────── */

function AddTaskRow({ onAdd }) {
  const [content, setContent] = useState('')
  const [deadline, setDeadline] = useState('')
  const [loading, setLoading] = useState(false)
  const today = new Date().toISOString().split('T')[0]

  const handleSubmit = async (e) => {
    e.preventDefault()
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
    <form className="task-add-row" onSubmit={handleSubmit}>
      <input
        className="form-input task-add-input"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="输入新的待办内容..."
      />
      <input
        className="form-input task-add-deadline"
        type="date"
        value={deadline}
        min={today}
        onChange={(e) => setDeadline(e.target.value)}
      />
      <button
        type="submit"
        className={`btn btn-accent btn-sm ${loading ? 'btn-loading' : ''}`}
        disabled={loading}
      >
        {loading ? <span className="spinner" /> : <Plus size={16} />}
        添加
      </button>
    </form>
  )
}

/* ─── Pagination ──────────────────────────────────────── */

function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null

  return (
    <div className="task-pagination">
      <button
        className="btn btn-ghost btn-sm"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        上一页
      </button>
      <span className="task-pagination-info">
        {page} / {totalPages}
      </span>
      <button
        className="btn btn-ghost btn-sm"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
      >
        下一页
      </button>
    </div>
  )
}

/* ─── Task List Component ─────────────────────────────── */

function TaskList({ tasks, loading, onToggle, onDelete, onEdit }) {
  if (loading) {
    return (
      <div className="loading-center">
        <span className="spinner spinner-lg" />
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="empty-state">
        <ListFilter />
        <p>暂无待办</p>
      </div>
    )
  }

  return (
    <div className="task-list">
      {tasks.map((task) => (
        <TaskItem
          key={task.id}
          task={task}
          onToggle={onToggle}
          onDelete={onDelete}
          onEdit={onEdit}
        />
      ))}
    </div>
  )
}

/* ─── Desktop Tabs View ────────────────────────────────── */

function DesktopTabsView() {
  const [tab, setTab] = useState('pending')
  const store = useTaskList()

  useEffect(() => {
    if (tab === 'completed') {
      store.fetchCompletedTasks(store.completedPage)
    } else {
      store.fetchPendingTasks()
    }
  }, [tab, store])

  const handleEdit = (taskId, content, deadline) => {
    store.handleEdit(taskId, content, deadline, tab)
  }

  const handleDelete = (taskId) => {
    store.handleDelete(taskId, tab)
  }

  const activeTasks = tab === 'pending' ? store.pendingTasks : store.completedTasks

  return (
    <div className="task-container">
      <AddTaskRow onAdd={store.handleAdd} />
      <div className="task-tabs">
        <button
          className={`task-tab ${tab === 'pending' ? 'active' : ''}`}
          onClick={() => setTab('pending')}
        >
          未完成 ({store.pendingTasks.length})
        </button>
        <button
          className={`task-tab ${tab === 'completed' ? 'active' : ''}`}
          onClick={() => setTab('completed')}
        >
          已完成 ({store.completedTotal})
        </button>
      </div>
      {activeTasks.length === 0 ? (
        <div className="empty-state">
          <ListFilter />
          <p>{tab === 'pending' ? '暂无未完成的待办' : '暂无已完成的待办'}</p>
        </div>
      ) : tab === 'completed' ? (
        <>
          <TaskList
            tasks={store.completedTasks}
            loading={store.completedLoading}
            onToggle={store.handleToggle}
            onDelete={handleDelete}
            onEdit={handleEdit}
          />
          <Pagination
            page={store.completedPage}
            totalPages={store.totalPages}
            onChange={store.setCompletedPage}
          />
        </>
      ) : (
        <TaskList
          tasks={store.pendingTasks}
          loading={false}
          onToggle={store.handleToggle}
          onDelete={handleDelete}
          onEdit={handleEdit}
        />
      )}
    </div>
  )
}

/* ─── Mobile Filter View ────────────────────────────────── */

function MobileFilterView() {
  const [filter, setFilter] = useState('pending')
  const store = useTaskList()

  useEffect(() => {
    if (filter === 'completed') {
      store.fetchCompletedTasks(store.completedPage)
    } else {
      store.fetchPendingTasks()
    }
  }, [filter, store])

  const handleEdit = (taskId, content, deadline) => {
    store.handleEdit(taskId, content, deadline, filter)
  }

  const handleDelete = (taskId) => {
    store.handleDelete(taskId, filter)
  }

  const activeTasks = filter === 'pending' ? store.pendingTasks : store.completedTasks

  return (
    <div className="task-container">
      <AddTaskRow onAdd={store.handleAdd} />
      <div className="task-filter-bar">
        <button
          className={`task-filter-btn ${filter === 'pending' ? 'active' : ''}`}
          onClick={() => setFilter('pending')}
        >
          进行中 ({store.pendingTasks.length})
        </button>
        <button
          className={`task-filter-btn ${filter === 'completed' ? 'active' : ''}`}
          onClick={() => setFilter('completed')}
        >
          已完成 ({store.completedTotal})
        </button>
      </div>
      {activeTasks.length === 0 ? (
        <div className="empty-state">
          <ListFilter />
          <p>暂无待办</p>
        </div>
      ) : filter === 'completed' ? (
        <>
          <TaskList
            tasks={store.completedTasks}
            loading={store.completedLoading}
            onToggle={store.handleToggle}
            onDelete={handleDelete}
            onEdit={handleEdit}
          />
          <Pagination
            page={store.completedPage}
            totalPages={store.totalPages}
            onChange={store.setCompletedPage}
          />
        </>
      ) : (
        <TaskList
          tasks={store.pendingTasks}
          loading={false}
          onToggle={store.handleToggle}
          onDelete={handleDelete}
          onEdit={handleEdit}
        />
      )}
    </div>
  )
}

/* ─── Main Component ────────────────────────────────────── */

export default function Tasks() {
  const isDesktop = useMediaQuery('(min-width: 769px)')

  return (
    <>
      <div className="page-header">
        <h2>工作待办</h2>
        <p>记录和管理你的工作待办事项</p>
      </div>
      <div className="page-body">{isDesktop ? <DesktopTabsView /> : <MobileFilterView />}</div>
    </>
  )
}
