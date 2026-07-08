import { useState, useCallback, useEffect } from 'react'
import toast from 'react-hot-toast'
import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { getDailyReportsRange } from '../api'
import useMediaQuery from '../hooks/useMediaQuery'
import { formatDate } from '../utils/date'

const WEEKDAY_HEADERS = ['一', '二', '三', '四', '五', '六', '日']
const MONTH_NAMES = [
  '1月',
  '2月',
  '3月',
  '4月',
  '5月',
  '6月',
  '7月',
  '8月',
  '9月',
  '10月',
  '11月',
  '12月',
]

function isSameDay(a, b) {
  return formatDate(a) === formatDate(b)
}

function getMonthDays(year, month) {
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  let startDow = firstDay.getDay() - 1
  if (startDow < 0) startDow = 6
  const days = []
  for (let i = startDow - 1; i >= 0; i--) {
    days.push(new Date(year, month, -i))
  }
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push(new Date(year, month, d))
  }
  const totalDays = startDow + lastDay.getDate()
  const rows = Math.ceil(totalDays / 7)
  const targetLength = rows * 7
  while (days.length < targetLength) {
    days.push(new Date(year, month + 1, days.length - startDow - lastDay.getDate() + 1))
  }
  return days
}

export default function CalendarView({ onEditDate, onDeleteDate, refreshRef }) {
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [deletingDate, setDeletingDate] = useState(null)

  const monthDays = getMonthDays(year, month)
  const rangeStart = formatDate(monthDays[0])
  const rangeEnd = formatDate(monthDays[monthDays.length - 1])

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getDailyReportsRange(rangeStart, rangeEnd)
      // 新格式: { reports: [...], _decryption_failed: bool }
      const reports = Array.isArray(data) ? data : data.reports || []
      setReports(reports)
    } catch {
      toast.error('加载日报失败')
    } finally {
      setLoading(false)
    }
  }, [rangeStart, rangeEnd])

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  // Expose refresh function to parent
  useEffect(() => {
    if (refreshRef) {
      refreshRef.current = fetchReports
    }
  }, [fetchReports, refreshRef])

  const getReportForDate = (dateStr) => reports.find((r) => r.date === dateStr)

  const handleDelete = async (e, dateStr) => {
    e.stopPropagation()
    if (!confirm('确定删除该日报？')) return
    setDeletingDate(dateStr)
    try {
      await onDeleteDate(dateStr)
      fetchReports()
    } catch {
      toast.error('删除失败')
    } finally {
      setDeletingDate(null)
    }
  }

  const prevMonth = () => {
    if (month === 0) {
      setMonth(11)
      setYear(year - 1)
    } else {
      setMonth(month - 1)
    }
  }

  const nextMonth = () => {
    if (month === 11) {
      setMonth(0)
      setYear(year + 1)
    } else {
      setMonth(month + 1)
    }
  }

  const goToday = () => {
    setYear(today.getFullYear())
    setMonth(today.getMonth())
  }

  const isCurrentMonth = (d) => d.getMonth() === month
  const isToday = (d) => isSameDay(d, today)

  return (
    <div className="calendar-container">
      {/* Month Navigation */}
      <div className="calendar-nav">
        <button className="btn btn-ghost btn-sm" onClick={prevMonth} aria-label="上个月">
          <ChevronLeft size={18} />
        </button>
        <span className="calendar-nav-label">
          {year}年 {MONTH_NAMES[month]}
        </span>
        <button className="btn btn-ghost btn-sm" onClick={nextMonth} aria-label="下个月">
          <ChevronRight size={18} />
        </button>
        <button className="btn btn-outline btn-sm" onClick={goToday}>
          今天
        </button>
      </div>

      {/* Calendar Grid */}
      <div className={`calendar-grid ${isDesktop ? 'with-preview' : ''}`}>
        {/* Weekday headers */}
        {WEEKDAY_HEADERS.map((h) => (
          <div className="calendar-weekday" key={h}>
            {h}
          </div>
        ))}

        {/* Day cells */}
        {loading ? (
          <div className="calendar-loading">
            <span className="spinner spinner-lg" />
          </div>
        ) : (
          monthDays.map((d) => {
            const dateStr = formatDate(d)
            const report = getReportForDate(dateStr)
            const inMonth = isCurrentMonth(d)
            const todayCls = isToday(d)
            const hasReport = !!report
            const preview = hasReport ? report.content : ''
            const isDeleting = deletingDate === dateStr

            return (
              <button
                key={dateStr}
                type="button"
                className={[
                  'calendar-day',
                  !inMonth && 'other-month',
                  todayCls && 'is-today',
                  hasReport && 'has-report',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => onEditDate(dateStr, report?.content || '')}
              >
                <div className="calendar-day-header">
                  <span className="calendar-day-num">{d.getDate()}</span>
                  {hasReport && <span className="calendar-day-dot" />}
                </div>
                {/* Content preview (PC only via .with-preview) */}
                {isDesktop && (
                  <div className="calendar-day-preview">
                    {preview || <span className="calendar-day-empty">+</span>}
                  </div>
                )}
                {/* Delete button for days with reports */}
                {isDesktop && hasReport && (
                  <span
                    className={`calendar-day-delete ${isDeleting ? 'deleting' : ''}`}
                    role="button"
                    tabIndex={0}
                    onClick={(e) => handleDelete(e, dateStr)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') handleDelete(e, dateStr)
                    }}
                    title="删除日报"
                    aria-label={`删除 ${dateStr} 日报`}
                  >
                    {isDeleting ? (
                      <span className="spinner" style={{ width: '12px', height: '12px' }} />
                    ) : (
                      <Trash2 size={12} />
                    )}
                  </span>
                )}
              </button>
            )
          })
        )}
      </div>

      {/* Legend */}
      <div className="calendar-legend">
        <span className="calendar-legend-item">
          <span className="calendar-day-dot" style={{ position: 'static' }} /> 有日报
        </span>
        <span className="calendar-legend-item">
          <span className="calendar-legend-today" /> 今天
        </span>
      </div>
    </div>
  )
}
