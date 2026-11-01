import { ChevronLeft, ChevronRight } from 'lucide-react'

/**
 * Period navigation shared by the calendar, weekly and monthly views.
 * The arrows flank the label as one centred cluster; the reset sits
 * outside it so the label stays optically centred on desktop.
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
      <div className="period-group">
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
      </div>
      <button
        className="btn btn-outline btn-sm period-today"
        onClick={onToday}
        disabled={todayDisabled}
      >
        {todayLabel}
      </button>
    </div>
  )
}
