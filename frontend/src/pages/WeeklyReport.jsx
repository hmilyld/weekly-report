import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { generateWeeklyReport, getWeeklyReport, updateWeeklyReport } from '../api'
import { addDays, formatDate, formatWeekRange, getMonday } from '../utils/date'
import PageHeader from '../components/ui/PageHeader'
import PeriodBar from '../components/ui/PeriodBar'
import ReportWorkspace from '../components/ReportWorkspace'

export default function WeeklyReport() {
  const [monday, setMonday] = useState(() => getMonday(new Date()))
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)

  const weekStart = formatDate(monday)

  const loadReport = useCallback(async () => {
    setLoading(true)
    setReport(null)
    try {
      const { data } = await getWeeklyReport(weekStart)
      setReport(data.reports ? data.reports[0] || null : data)
    } catch (err) {
      // 404 means "not generated yet", which is a normal state here.
      if (err.response?.status !== 404) {
        toast.error(err.response?.data?.detail || '加载周报失败')
      }
      setReport(null)
    } finally {
      setLoading(false)
    }
  }, [weekStart])

  useEffect(() => {
    loadReport()
  }, [loadReport])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const { data } = await generateWeeklyReport(weekStart)
      setReport(data)
      toast.success('周报已生成')
    } catch (err) {
      toast.error(err.response?.data?.detail || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleSave = async (content) => {
    setSaving(true)
    try {
      const { data } = await updateWeeklyReport(weekStart, content)
      setReport(data)
      toast.success('周报已保存')
      return true
    } catch (err) {
      toast.error(err.response?.data?.detail || '保存失败')
      return false
    } finally {
      setSaving(false)
    }
  }

  const isThisWeek = weekStart === formatDate(getMonday(new Date()))

  return (
    <div className="page">
      <PageHeader
        title="周报管理"
        subtitle="把一周的日报汇总成一份可以直接发出去的周报；生成后仍可编辑、复制。"
      />
      <ReportWorkspace
        cadence="weekly"
        periodLabel={formatWeekRange(monday)}
        periodNode={
          <PeriodBar
            label={formatWeekRange(monday)}
            onPrev={() => setMonday(addDays(monday, -7))}
            onNext={() => setMonday(addDays(monday, 7))}
            onToday={() => setMonday(getMonday(new Date()))}
            todayLabel="回到本周"
            todayDisabled={isThisWeek}
            prevLabel="上一周"
            nextLabel="下一周"
          />
        }
        report={report}
        loading={loading}
        generating={generating}
        saving={saving}
        onGenerate={handleGenerate}
        onSave={handleSave}
        emptyHint="周报由本周的日报自动汇总。先在「日报管理」里补几条记录，再回来生成。"
      />
    </div>
  )
}
