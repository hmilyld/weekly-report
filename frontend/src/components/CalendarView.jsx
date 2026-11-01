import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { Plus, Trash2 } from 'lucide-react'
import { getDailyReportsRange } from '../api'
import useMediaQuery from '../hooks/useMediaQuery'
import { formatDate, formatMonth } from '../utils/date'
import PeriodBar from './ui/PeriodBar'

const WEEKDAY_HEADERS = ['一', '二', '三', '四', '五', '六', '日']

function isSameDay(a, b) {
  return formatDate(a) === formatDate(b)
}

function getMonthDays(year, month) {
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  let startDow = firstDay.getDay() - 1
  if (startDow < 0) startDow = 6
  const days = []
  for (let i = startDow - 1; i >= 0; i--) days.push(new Date(year, month, -i))
  for (let d = 1; d <= lastDay.getDate(); d++) days.push(new Date(year, month, d))
  const rows = Math.ceil((startDow + lastDay.getDate()) / 7)
  while (days.length < rows * 7) {
    days.push(new Date(year, month + 1, days.length - startDow - lastDay.getDate() + 1))
  }
  return days
}

export default function CalendarView({ onEditDate, onDeleteDate, refreshRef }) {
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const gridRef = useRef(null)

  const monthDays = getMonthDays(year, month)
  const rangeStart = formatDate(monthDays[0])
  const rangeEnd = formatDate(monthDays[monthDays.length - 1])

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getDailyReportsRange(rangeStart, rangeEnd)
      setReports(Array.isArray(data) ? data : data.reports || [])
    } catch {
      toast.error('加载日报失败')
    } finally {
      setLoading(false)
    }
  }, [rangeStart, rangeEnd])

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  useEffect(() => {
    if (refreshRef) refreshRef.current = fetchReports
  }, [fetchReports, refreshRef])

  const reportFor = (dateStr) => reports.find((report) => report.date === dateStr)

  const handleDelete = async (event, dateStr) => {
    event.stopPropagation()
    try {
      await onDeleteDate(dateStr)
      fetchReports()
    } catch {
      toast.error('删除失败')
    }
  }

  const shiftMonth = (delta) => {
    const next = new Date(year, month + delta, 1)
    setYear(next.getFullYear())
    setMonth(next.getMonth())
  }

  const goToday = () => {
    setYear(today.getFullYear())
    setMonth(today.getMonth())
  }

  const isCurrentMonth = (date) => date.getMonth() === month
  const isCurrentMonthToday = year === today.getFullYear() && month === today.getMonth()

  // Arrow keys walk the grid, as they would in any calendar.
  const onGridKeyDown = (event) => {
    const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key]
    if (!step) return
    const buttons = Array.from(gridRef.current?.querySelectorAll('.day') || [])
    const index = buttons.indexOf(document.activeElement)
    if (index === -1) return
    event.preventDefault()
    buttons[index + step]?.focus()
  }

  return (
    <div>
      <PeriodBar
        label={formatMonth(year, month + 1)}
        onPrev={() => shiftMonth(-1)}
        onNext={() => shiftMonth(1)}
        onToday={goToday}
        todayLabel="回到本月"
        todayDisabled={isCurrentMonthToday}
        prevLabel="上个月"
        nextLabel="下个月"
      />

      <div className="calendar">
        <div className="calendar-weekdays">
          {WEEKDAY_HEADERS.map((header, index) => (
            <div
              className={`calendar-weekday ${index > 4 ? 'is-weekend' : ''}`.trim()}
              key={header}
            >
              {header}
            </div>
          ))}
        </div>

        {loading ? (
          <div className="calendar-loading">
            <span className="spinner" aria-hidden="true" />
            正在读取本月日报…
          </div>
        ) : (
          <div className="calendar-grid" ref={gridRef} onKeyDown={onGridKeyDown}>
            {monthDays.map((date) => {
              const dateStr = formatDate(date)
              const report = reportFor(dateStr)
              const inMonth = isCurrentMonth(date)
              const isToday = isSameDay(date, today)
              const classes = [
                'day',
                !inMonth && 'is-outside',
                isToday && 'is-today',
                report && 'is-filled',
              ]
                .filter(Boolean)
                .join(' ')

              return (
                <div key={dateStr} className={classes}>
                  {/* The cell's open action and its delete action are
                      siblings: a button may not contain another control. */}
                  <button
                    type="button"
                    className="day-open"
                    onClick={() => onEditDate(dateStr, report?.content || '')}
                    aria-label={`${dateStr}${report ? '，已有日报' : '，暂无日报'}`}
                  >
                    <span className="day-head">
                      <span className="day-num">{date.getDate()}</span>
                      {report && <span className="chip-band" title="有日报" />}
                    </span>
                    {isDesktop && (
                      <span className="day-preview">
                        {report?.content || (
                          <span className="day-add">
                            <Plus size={12} aria-hidden="true" />
                            记录
                          </span>
                        )}
                      </span>
                    )}
                    {isDesktop && <span className="day-slash" aria-hidden="true" />}
                  </button>
                  {isDesktop && report && (
                    <button
                      type="button"
                      className="day-delete"
                      onClick={(event) => handleDelete(event, dateStr)}
                      title="删除这条日报"
                      aria-label={`删除 ${dateStr} 的日报`}
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="calendar-legend">
        <span className="calendar-legend-item">
          <span className="chip-band" aria-hidden="true" /> 有日报
        </span>
        <span className="calendar-legend-item">
          <span className="legend-swatch-today" aria-hidden="true" /> 今天
        </span>
        <span className="calendar-legend-item">点格子记录，← → ↑ ↓ 切换日期</span>
      </div>
    </div>
  )
}
