/**
 * Shared date utility functions.
 */

/**
 * Get Monday of the week containing the given date.
 * @param {Date} d
 * @returns {Date}
 */
export function getMonday(d) {
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  return new Date(d.getFullYear(), d.getMonth(), diff)
}

/**
 * Format date as YYYY-MM-DD.
 * @param {Date} d
 * @returns {string}
 */
export function formatDate(d) {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Add days to a date (returns new Date).
 * @param {Date} d
 * @param {number} days
 * @returns {Date}
 */
export function addDays(d, days) {
  const result = new Date(d)
  result.setDate(result.getDate() + days)
  return result
}

/**
 * Format week range as "M月D日 - M月D日".
 * @param {Date} monday
 * @returns {string}
 */
export function formatWeekRange(monday) {
  const sunday = addDays(monday, 6)
  const start = `${monday.getMonth() + 1}月${monday.getDate()}日`
  const end = `${sunday.getMonth() + 1}月${sunday.getDate()}日`
  return `${start} - ${end}`
}

/**
 * Add months to a date (returns new Date).
 * @param {Date} d
 * @param {number} months
 * @returns {Date}
 */
export function addMonths(d, months) {
  const result = new Date(d)
  result.setMonth(result.getMonth() + months)
  return result
}

/**
 * Format month as "YYYY年M月".
 * @param {number} year
 * @param {number} month
 * @returns {string}
 */
export function formatMonth(year, month) {
  return `${year}年${month}月`
}

/**
 * Timestamps arrive from the API as UTC without an offset
 * ("2026-11-01T09:15:02"), which JS would read as local time.
 * Treat a zone-less value as UTC so the clock shown is the user's own.
 * @param {string|Date|null} value
 * @returns {Date|null}
 */
export function parseServerDate(value) {
  if (!value) return null
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  // A bare calendar date has no timezone to correct; keep it on its own day.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const local = new Date(`${value}T00:00:00`)
    return Number.isNaN(local.getTime()) ? null : local
  }
  const hasZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(value)
  const parsed = new Date(hasZone ? value : `${value}Z`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

/**
 * Format a timestamp as "YYYY-MM-DD HH:mm" in the user's timezone.
 * @param {string|Date|null} value
 * @param {string} [fallback]
 * @returns {string}
 */
export function formatDateTime(value, fallback = '—') {
  const date = parseServerDate(value)
  if (!date) return fallback
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
}

/**
 * Format a timestamp as "YYYY-MM-DD" in the user's timezone.
 * @param {string|Date|null} value
 * @param {string} [fallback]
 * @returns {string}
 */
export function formatDateOnly(value, fallback = '—') {
  const date = parseServerDate(value)
  if (!date) return fallback
  return formatDate(date)
}
