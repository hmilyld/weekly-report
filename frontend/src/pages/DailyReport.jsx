import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { ChevronLeft, ChevronRight, Pencil, Trash2 } from 'lucide-react'
import { getDailyReportsWeek, saveDailyReport, deleteDailyReport } from '../api'
import DailyEditModal from '../components/DailyEditModal'
import CalendarView from '../components/CalendarView'
import useMediaQuery from '../hooks/useMediaQuery'

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function getMonday(date) {
  const d = new Date(date)
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  d.setDate(diff)
  d.setHours(0, 0, 0, 0)
  return d
}

function formatDate(d) {
  return d.toISOString().split('T')[0]
}

function addDays(d, n) {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

function formatWeekRange(monday) {
  const sunday = addDays(monday, 6)
  return `${formatDate(monday)} ~ ${formatDate(sunday)}`
}

/* ─── Week List View (Mobile) ─────────────────────────── */

function WeekListView({ onEditDate }) {
  const [currentMonday, setCurrentMonday] = useState(() => getMonday(new Date()))
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [deletingDate, setDeletingDate] = useState(null)

  const weekDates = Array.from({ length: 7 }, (_, i) => addDays(currentMonday, i))

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const ws = formatDate(currentMonday)
      const { data } = await getDailyReportsWeek(ws)
      setReports(data)
    } catch (_) {
      toast.error('加载日报失败')
    } finally {
      setLoading(false)
    }
  }, [currentMonday])

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  const getReportForDate = (date) => reports.find((r) => r.date === formatDate(date))

  const handleDelete = async (date) => {
    if (!confirm('确定删除该日报？')) return
    setDeletingDate(date)
    try {
      await deleteDailyReport(date)
      toast.success('已删除')
      fetchReports()
    } catch (_) {
      toast.error('删除失败')
    } finally {
      setDeletingDate(null)
    }
  }

  const isToday = (date) => formatDate(date) === formatDate(new Date())

  return (
    <>
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

      {loading ? (
        <div className="loading-center">
          <span className="spinner spinner-lg" />
        </div>
      ) : (
        <div className="daily-list">
          {weekDates.map((date, idx) => {
            const report = getReportForDate(date)
            const content = report?.content || ''
            const today = isToday(date)
            const isDeleting = deletingDate === formatDate(date)
            return (
              <div
                className="daily-item"
                key={formatDate(date)}
                style={
                  today ? { borderColor: 'var(--color-accent)', borderWidth: '1.5px' } : undefined
                }
              >
                <div className="daily-date">
                  {formatDate(date).slice(5)}
                  <span className="weekday">{WEEKDAYS[idx]}</span>
                  {today && (
                    <span
                      className="badge"
                      style={{ marginLeft: '6px', background: '#eff6ff', color: '#2563eb' }}
                    >
                      今天
                    </span>
                  )}
                </div>
                <div
                  className={content ? 'daily-content' : 'daily-content daily-empty'}
                  onClick={() => onEditDate(formatDate(date), content)}
                  style={{ cursor: 'pointer' }}
                >
                  {content || '点击添加日报...'}
                </div>
                <div className="daily-actions">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => onEditDate(formatDate(date), content)}
                    title="编辑"
                    aria-label="编辑日报"
                  >
                    <Pencil size={15} />
                  </button>
                  {report && (
                    <button
                      className={`btn btn-ghost btn-sm ${isDeleting ? 'btn-loading' : ''}`}
                      onClick={() => handleDelete(formatDate(date))}
                      disabled={isDeleting}
                      title="删除"
                      aria-label="删除日报"
                      style={{ color: 'var(--color-danger)' }}
                    >
                      {isDeleting ? <span className="spinner" /> : <Trash2 size={15} />}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}

/* ─── Main Component ──────────────────────────────────── */

export default function DailyReport() {
  const isDesktop = useMediaQuery('(min-width: 769px)')
  const [modal, setModal] = useState({ open: false, date: null, content: '' })

  // Shared: fetch reports after save to refresh whichever view is active
  const [refreshKey, setRefreshKey] = useState(0)

  const handleSave = async (date, content) => {
    try {
      await saveDailyReport(date, content)
      toast.success('保存成功')
      setModal({ open: false, date: null, content: '' })
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error(err.response?.data?.detail || '保存失败')
    }
  }

  const openEdit = (date, content) => {
    setModal({ open: true, date, content: content || '' })
  }

  const handleDelete = async (date) => {
    await deleteDailyReport(date)
    toast.success('已删除')
  }

  return (
    <>
      <div className="page-header">
        <h2>日报管理</h2>
        <p>记录每天的工作内容，用于自动生成周报</p>
      </div>
      <div className="page-body">
        {isDesktop ? (
          <CalendarView key={refreshKey} onEditDate={openEdit} onDeleteDate={handleDelete} />
        ) : (
          <WeekListView key={refreshKey} onEditDate={openEdit} />
        )}
      </div>

      {modal.open && (
        <DailyEditModal
          date={modal.date}
          content={modal.content}
          onSave={handleSave}
          onClose={() => setModal({ open: false, date: null, content: '' })}
        />
      )}
    </>
  )
}
