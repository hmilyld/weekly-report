import { describe, it, expect } from 'vitest'

import {
  addDays,
  addMonths,
  formatDate,
  formatDateOnly,
  formatDateTime,
  formatMonth,
  formatWeekRange,
  getMonday,
  parseServerDate,
} from '../date'

describe('getMonday', () => {
  it('returns the same day for a Monday', () => {
    const monday = getMonday(new Date(2026, 10, 2)) // 2026-11-02 是周一
    expect(formatDate(monday)).toBe('2026-11-02')
  })

  it('walks back to Monday from mid-week', () => {
    const monday = getMonday(new Date(2026, 10, 4)) // 周三
    expect(formatDate(monday)).toBe('2026-11-02')
  })

  it('treats Sunday as the end of the previous week', () => {
    const monday = getMonday(new Date(2026, 10, 8)) // 周日
    expect(formatDate(monday)).toBe('2026-11-02')
  })
})

describe('formatDate', () => {
  it('pads month and day to two digits', () => {
    expect(formatDate(new Date(2026, 0, 5))).toBe('2026-01-05')
    expect(formatDate(new Date(2026, 11, 31))).toBe('2026-12-31')
  })
})

describe('addDays / addMonths', () => {
  it('crosses month and year boundaries without mutating the input', () => {
    const start = new Date(2026, 11, 31)
    expect(formatDate(addDays(start, 1))).toBe('2027-01-01')
    expect(formatDate(start)).toBe('2026-12-31')
  })

  it('adds months keeping the day of month', () => {
    expect(formatDate(addMonths(new Date(2026, 0, 15), 2))).toBe('2026-03-15')
  })
})

describe('formatWeekRange', () => {
  it('renders Monday through Sunday in Chinese', () => {
    expect(formatWeekRange(new Date(2026, 10, 2))).toBe('11月2日 - 11月8日')
  })

  it('handles a range that crosses into the next month', () => {
    expect(formatWeekRange(new Date(2026, 10, 30))).toBe('11月30日 - 12月6日')
  })
})

describe('formatMonth', () => {
  it('renders year and month in Chinese', () => {
    expect(formatMonth(2026, 11)).toBe('2026年11月')
  })
})

describe('parseServerDate', () => {
  it('returns null for empty or invalid input', () => {
    expect(parseServerDate(null)).toBeNull()
    expect(parseServerDate('')).toBeNull()
    expect(parseServerDate('not-a-date')).toBeNull()
    expect(parseServerDate(new Date('nope'))).toBeNull()
  })

  it('passes a valid Date through', () => {
    const date = new Date(2026, 10, 1, 9, 15)
    expect(parseServerDate(date)).toBe(date)
  })

  it('reads a zone-less server timestamp as UTC', () => {
    const parsed = parseServerDate('2026-11-01T09:15:02')
    expect(parsed.getTime()).toBe(Date.UTC(2026, 10, 1, 9, 15, 2))
  })

  it('respects an explicit timezone or Z suffix', () => {
    expect(parseServerDate('2026-11-01T09:15:02Z').getTime()).toBe(Date.UTC(2026, 10, 1, 9, 15, 2))
    expect(parseServerDate('2026-11-01T09:15:02+08:00').getTime()).toBe(
      Date.UTC(2026, 10, 1, 1, 15, 2),
    )
  })

  it('keeps a bare calendar date on its own day', () => {
    const parsed = parseServerDate('2026-11-01')
    expect(parsed.getHours()).toBe(0)
    expect(formatDate(parsed)).toBe('2026-11-01')
  })
})

describe('formatDateTime / formatDateOnly', () => {
  it('formats a local date with padded clock digits', () => {
    expect(formatDateTime(new Date(2026, 10, 1, 9, 5))).toBe('2026-11-01 09:05')
  })

  it('uses the fallback for missing values', () => {
    expect(formatDateTime(null)).toBe('—')
    expect(formatDateTime(null, '未知')).toBe('未知')
    expect(formatDateOnly(null)).toBe('—')
  })

  it('formats a UTC timestamp in the local timezone', () => {
    const value = '2026-11-01T09:15:02'
    const expected = new Date(Date.UTC(2026, 10, 1, 9, 15, 2))
    expect(formatDateOnly(value)).toBe(formatDate(expected))
  })
})
