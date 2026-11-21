export const DAY = 1000 * 60 * 60 * 24

export const startOfToday = () => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return today
}

export const deadlineState = (deadline) => {
  if (!deadline) return 'none'
  const date = new Date(`${deadline}T00:00:00`)
  const today = startOfToday()
  if (date < today) return 'overdue'
  if ((date - today) / DAY < 3) return 'urgent'
  return 'later'
}

export const todayInput = () => {
  const today = new Date()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${today.getFullYear()}-${month}-${day}`
}
