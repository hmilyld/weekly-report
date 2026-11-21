import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { deleteTask, getCompletedTasks, getTasks, updateTask } from '../api'
import useMediaQuery from '../hooks/useMediaQuery'
import { useConfirm } from '../components/ui/confirm'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import PageHeader from '../components/ui/PageHeader'
import TaskComposer from '../components/tasks/TaskComposer'
import TaskRow from '../components/tasks/TaskRow'

const PAGE_SIZE = 20

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
