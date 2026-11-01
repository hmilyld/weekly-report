import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Pencil, Trash2 } from 'lucide-react'
import { getDailyReportsWeek, deleteDailyReport } from '../api'
import { addDays, formatDate, formatWeekRange, getMonday } from '../utils/date'
import { useConfirm } from './ui/ConfirmProvider'
import Button from './ui/Button'
import EmptyState from './ui/EmptyState'
import PeriodBar from './ui/PeriodBar'

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

/**
 * Phone view of the daily record: one week, one row per day.
 * The calendar is a desktop affordance; this is the same data at 390px.
 */
export default function WeekList({ onEditDate, refreshRef }) {
  const confirm = useConfirm()
  const [monday, setMonday] = useState(() => getMonday(new Date()))
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingDate, setDeletingDate] = useState(null)

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

  const handleDelete = async (date) => {
    const ok = await confirm({
      title: '删除这条日报？',
      body: `${date} 的记录将被移除，删除后无法恢复。`,
      confirmLabel: '删除',
      tone: 'danger',
    })
    if (!ok) return
    setDeletingDate(date)
    try {
      await deleteDailyReport(date)
      toast.success('已删除')
      fetchReports()
    } catch {
      toast.error('删除失败')
    } finally {
      setDeletingDate(null)
    }
  }

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
              >
                <div className="week-date">
                  <span>{dateStr.slice(5)}</span>
                  <span className="weekday">{WEEKDAYS[index]}</span>
                  {isToday && <span className="badge badge-accent">今天</span>}
                </div>
                <div
                  className="week-body"
                  onClick={() => onEditDate(dateStr, report?.content || '')}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onEditDate(dateStr, report?.content || '')
                    }
                  }}
                >
                  <span className={`week-text ${report ? '' : 'is-empty'}`.trim()}>
                    {report?.content || '还没有记录，点这里写今天的进展'}
                  </span>
                </div>
                <div className="week-actions">
                  <Button
                    variant="ghost"
                    size="sm"
                    iconOnly
                    icon={Pencil}
                    aria-label={`编辑 ${dateStr}`}
                    onClick={() => onEditDate(dateStr, report?.content || '')}
                  />
                  {report && (
                    <Button
                      variant="danger"
                      size="sm"
                      iconOnly
                      icon={Trash2}
                      aria-label={`删除 ${dateStr}`}
                      loading={deletingDate === dateStr}
                      onClick={() => handleDelete(dateStr)}
                    />
                  )}
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
