import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { generateMonthlyReport, getMonthlyReport, updateMonthlyReport } from '../api'
import { addMonths, formatMonth } from '../utils/date'
import PageHeader from '../components/ui/PageHeader'
import PeriodBar from '../components/ui/PeriodBar'
import ReportWorkspace from '../components/ReportWorkspace'

export default function MonthlyReport() {
  const [current, setCurrent] = useState(() => new Date())
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)

  const year = current.getFullYear()
  const month = current.getMonth() + 1
  const label = formatMonth(year, month)

  const loadReport = useCallback(async () => {
    setLoading(true)
    setReport(null)
    try {
      const { data } = await getMonthlyReport(year, month)
      setReport(data.reports ? data.reports[0] || null : data)
    } catch (err) {
      if (err.response?.status !== 404) {
        toast.error(err.response?.data?.detail || '加载月报失败')
      }
      setReport(null)
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => {
    loadReport()
  }, [loadReport])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const { data } = await generateMonthlyReport(year, month)
      setReport(data)
      toast.success('月报已生成')
    } catch (err) {
      toast.error(err.response?.data?.detail || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleSave = async (content) => {
    setSaving(true)
    try {
      const { data } = await updateMonthlyReport(year, month, content)
      setReport(data)
      toast.success('月报已保存')
      return true
    } catch (err) {
      toast.error(err.response?.data?.detail || '保存失败')
      return false
    } finally {
      setSaving(false)
    }
  }

  const now = new Date()
  const isThisMonth = year === now.getFullYear() && month === now.getMonth() + 1

  return (
    <div className="page">
      <PageHeader
        title="月报管理"
        subtitle="把一个月的日报汇总成月度总结；跨月回看时直接切换周期即可。"
      />
      <ReportWorkspace
        cadence="monthly"
        periodLabel={label}
        periodNode={
          <PeriodBar
            label={label}
            onPrev={() => setCurrent(addMonths(current, -1))}
            onNext={() => setCurrent(addMonths(current, 1))}
            onToday={() => setCurrent(new Date())}
            todayLabel="回到本月"
            todayDisabled={isThisMonth}
            prevLabel="上个月"
            nextLabel="下个月"
          />
        }
        report={report}
        loading={loading}
        generating={generating}
        saving={saving}
        onGenerate={handleGenerate}
        onSave={handleSave}
        emptyHint="月报由本月所有日报汇总。先在「日报管理」里补全记录，再回来生成。"
      />
    </div>
  )
}
