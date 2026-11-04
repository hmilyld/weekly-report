import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { getDailyReportsWeek } from '../api'
import { addDays, formatDate, formatWeekRange, getMonday } from '../utils/date'
import EmptyState from './ui/EmptyState'
import PeriodBar from './ui/PeriodBar'

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

/**
 * Phone view of the daily record: one week, one row per day.
 * The calendar is a desktop affordance; this is the same data at 390px.
 * A row carries no action column: tapping the text opens the edit sheet,
 * which is where a record is saved or deleted.
 */
export default function WeekList({ onEditDate, refreshRef }) {
  const [monday, setMonday] = useState(() => getMonday(new Date()))
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)

  const weekDates = Array.from({ length: 7 }, (_, index) => addDays(monday, index))

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getDailyReportsWeek(formatDate(monday))
      setReports(Array.isArray(data) ? data : data.reports || [])
    } catch {
      toast.error('加载日报失败')
    } finally {
      setLoading(false)
    }
  }, [monday])

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  useEffect(() => {
    if (refreshRef) refreshRef.current = fetchReports
  }, [fetchReports, refreshRef])

  const todayStr = formatDate(new Date())
  const isThisWeek = formatDate(monday) === formatDate(getMonday(new Date()))
  const filled = reports.length

  return (
    <div>
      <PeriodBar
        label={formatWeekRange(monday)}
        range={`已记 ${filled} 天`}
        onPrev={() => setMonday(addDays(monday, -7))}
        onNext={() => setMonday(addDays(monday, 7))}
        onToday={() => setMonday(getMonday(new Date()))}
        todayLabel="回到本周"
        todayDisabled={isThisWeek}
        prevLabel="上一周"
        nextLabel="下一周"
      />

      {loading ? (
        <div className="loading-block">
          <span className="spinner" aria-hidden="true" />
          正在读取本周日报…
        </div>
      ) : (
        <div className="week-list">
          {weekDates.map((date, index) => {
            const dateStr = formatDate(date)
            const report = reports.find((item) => item.date === dateStr)
            const isToday = dateStr === todayStr
            return (
              <div
                className={`week-row ${isToday ? 'is-today' : ''}`.trim()}
                key={dateStr}
                aria-current={isToday ? 'date' : undefined}
                role="button"
                tabIndex={0}
                aria-label={`${dateStr}${report ? '，查看或编辑日报' : '，补记日报'}`}
                onClick={() => onEditDate(dateStr, report?.content || '', Boolean(report))}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onEditDate(dateStr, report?.content || '', Boolean(report))
                  }
                }}
              >
                <div className="week-date">
                  <span>{dateStr.slice(5)}</span>
                  <span className="weekday">{WEEKDAYS[index]}</span>
                  {isToday && <span className="badge badge-accent">今天</span>}
                </div>
                <div className="week-body">
                  <span className={`week-text ${report ? '' : 'is-empty'}`.trim()}>
                    {report?.content || '还没有记录，点这里补记当天进展'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {!loading && filled === 0 && (
        <EmptyState
          title="这一周还是空的"
          description="点任意一天写下当天的进展；周末留空也没关系，周报只汇总写过的内容。"
        />
      )}
    </div>
  )
}
