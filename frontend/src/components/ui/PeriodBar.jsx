import { ChevronLeft, ChevronRight } from 'lucide-react'

/**
 * Period navigation shared by the calendar, weekly and monthly views:
 * the label is the headline, the arrows are the only way to move,
 * and "回到今天/本周/本月" is always one click away.
 */
export default function PeriodBar({
  label,
  range,
  onPrev,
  onNext,
  onToday,
  todayLabel = '本周',
  todayDisabled = false,
  prevLabel = '上一周期',
  nextLabel = '下一周期',
}) {
  return (
    <div className="period-bar">
      <button className="period-nav" onClick={onPrev} aria-label={prevLabel}>
        <ChevronLeft size={18} />
      </button>
      <div className="period-label">
        <span>{label}</span>
        {range && <span className="range">{range}</span>}
      </div>
      <button className="period-nav" onClick={onNext} aria-label={nextLabel}>
        <ChevronRight size={18} />
      </button>
      <button className="btn btn-outline btn-sm" onClick={onToday} disabled={todayDisabled}>
        {todayLabel}
      </button>
    </div>
  )
}
