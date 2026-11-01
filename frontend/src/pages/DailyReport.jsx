import { useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { deleteDailyReport, saveDailyReport } from '../api'
import useMediaQuery from '../hooks/useMediaQuery'
import PageHeader from '../components/ui/PageHeader'
import CalendarView from '../components/CalendarView'
import DailyEditModal from '../components/DailyEditModal'
import WeekList from '../components/WeekList'

export default function DailyReport() {
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const [modal, setModal] = useState({ open: false, date: null, content: '' })
  const refreshRef = useRef(null)

  const handleSave = async (date, content) => {
    try {
      await saveDailyReport(date, content)
      toast.success(content.trim() ? '日报已保存' : '日报已清空')
      setModal({ open: false, date: null, content: '' })
      refreshRef.current?.()
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
    refreshRef.current?.()
  }

  return (
    <div className="page">
      <PageHeader
        title="日报管理"
        subtitle={
          isDesktop
            ? '点日历上的任意一天记录当天进展；周报和月报都会从这里汇总。'
            : '按周查看与补记当天进展；周报和月报都会从这里汇总。'
        }
      />

      {isDesktop ? (
        <CalendarView onEditDate={openEdit} onDeleteDate={handleDelete} refreshRef={refreshRef} />
      ) : (
        <WeekList onEditDate={openEdit} refreshRef={refreshRef} />
      )}

      {modal.open && (
        <DailyEditModal
          date={modal.date}
          content={modal.content}
          onSave={handleSave}
          onClose={() => setModal({ open: false, date: null, content: '' })}
        />
      )}
    </div>
  )
}
