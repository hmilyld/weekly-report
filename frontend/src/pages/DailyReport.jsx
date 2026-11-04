import { useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { deleteDailyReport, saveDailyReport } from '../api'
import useMediaQuery from '../hooks/useMediaQuery'
import { useConfirm } from '../components/ui/ConfirmProvider'
import PageHeader from '../components/ui/PageHeader'
import CalendarView from '../components/CalendarView'
import DailyEditModal from '../components/DailyEditModal'
import WeekList from '../components/WeekList'

const CLOSED = { open: false, date: null, content: '', hasReport: false }

export default function DailyReport() {
  const confirm = useConfirm()
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const [modal, setModal] = useState(CLOSED)
  const [deleting, setDeleting] = useState(false)
  const refreshRef = useRef(null)

  const handleSave = async (date, content) => {
    try {
      await saveDailyReport(date, content)
      toast.success(content.trim() ? '日报已保存' : '日报已清空')
      setModal(CLOSED)
      refreshRef.current?.()
    } catch (err) {
      toast.error(err.response?.data?.detail || '保存失败')
    }
  }

  const openEdit = (date, content, hasReport) => {
    setModal({ open: true, date, content: content || '', hasReport: Boolean(hasReport) })
  }

  const handleDelete = async (date) => {
    const ok = await confirm({
      title: '删除这条日报？',
      body: `${date} 的记录将被移除，删除后无法恢复。`,
      confirmLabel: '删除',
      tone: 'danger',
    })
    if (!ok) return
    setDeleting(true)
    try {
      await deleteDailyReport(date)
      toast.success('已删除')
      setModal(CLOSED)
      refreshRef.current?.()
    } catch {
      toast.error('删除失败')
    } finally {
      setDeleting(false)
    }
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
          hasReport={modal.hasReport}
          deleting={deleting}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => setModal(CLOSED)}
        />
      )}
    </div>
  )
}
