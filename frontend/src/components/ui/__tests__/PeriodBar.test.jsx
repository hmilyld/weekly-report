import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import PeriodBar from '../PeriodBar'

function renderBar(overrides = {}) {
  const handlers = { onPrev: vi.fn(), onNext: vi.fn(), onToday: vi.fn() }
  render(<PeriodBar label="2026年11月" range="11月2日 - 11月8日" {...handlers} {...overrides} />)
  return handlers
}

describe('PeriodBar', () => {
  it('shows the label and range', () => {
    renderBar()

    expect(screen.getByText('2026年11月')).toBeInTheDocument()
    expect(screen.getByText('11月2日 - 11月8日')).toBeInTheDocument()
  })

  it('omits the range when there is none', () => {
    renderBar({ range: undefined })

    expect(screen.queryByText('11月2日 - 11月8日')).not.toBeInTheDocument()
  })

  it('calls the navigation and reset handlers', async () => {
    const user = userEvent.setup()
    const handlers = renderBar()

    await user.click(screen.getByRole('button', { name: '上一周期' }))
    await user.click(screen.getByRole('button', { name: '下一周期' }))
    await user.click(screen.getByRole('button', { name: '本周' }))

    expect(handlers.onPrev).toHaveBeenCalledTimes(1)
    expect(handlers.onNext).toHaveBeenCalledTimes(1)
    expect(handlers.onToday).toHaveBeenCalledTimes(1)
  })

  it('honours custom labels and a disabled reset', async () => {
    const user = userEvent.setup()
    const handlers = renderBar({
      todayLabel: '本月',
      todayDisabled: true,
      prevLabel: '上个月',
      nextLabel: '下个月',
    })

    const reset = screen.getByRole('button', { name: '本月' })
    expect(reset).toBeDisabled()
    await user.click(reset)
    expect(handlers.onToday).not.toHaveBeenCalled()

    expect(screen.getByRole('button', { name: '上个月' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '下个月' })).toBeInTheDocument()
  })
})
