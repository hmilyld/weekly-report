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
