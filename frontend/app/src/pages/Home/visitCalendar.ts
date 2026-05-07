import { extractSearchDateFromVisitId, isValidSearchDate } from "./visitSearch"

type VisitDayCountLike = {
  day_obs: number
  count: number
}

export type CalendarDayCell = {
  date: string
  day: number
  inCurrentMonth: boolean
}

function zeroPad(value: number): string {
  return `${value}`.padStart(2, "0")
}

function isValidCalendarMonth(value: string): boolean {
  return /^\d{4}-\d{2}$/.test(value)
}

export function dayObsToSearchDate(dayObs: number): string {
  const normalized = `${dayObs}`
  if (!/^\d{8}$/.test(normalized)) {
    return ""
  }

  return `${normalized.slice(0, 4)}-${normalized.slice(4, 6)}-${normalized.slice(6, 8)}`
}

export function getTodaySearchDate(today: Date = new Date()): string {
  return `${today.getFullYear()}-${zeroPad(today.getMonth() + 1)}-${zeroPad(today.getDate())}`
}

export function searchDateToCalendarMonth(value: string): string | undefined {
  if (!isValidSearchDate(value)) {
    return undefined
  }
  return value.slice(0, 7)
}

export function getInitialCalendarMonth(currentVisitId: string | undefined, today: Date = new Date()): string {
  const searchDate = extractSearchDateFromVisitId(currentVisitId ?? "")
  return searchDateToCalendarMonth(searchDate) ?? searchDateToCalendarMonth(getTodaySearchDate(today))!
}

export function getSelectedCalendarDate(searchDate: string, currentVisitId: string | undefined): string | undefined {
  if (isValidSearchDate(searchDate)) {
    return searchDate
  }

  const currentVisitSearchDate = extractSearchDateFromVisitId(currentVisitId ?? "")
  if (isValidSearchDate(currentVisitSearchDate)) {
    return currentVisitSearchDate
  }

  return undefined
}

export function shiftCalendarMonth(month: string, offset: number): string {
  const fallback = searchDateToCalendarMonth(getTodaySearchDate())!
  const source = isValidCalendarMonth(month) ? month : fallback
  const [yearText, monthText] = source.split("-")
  const base = new Date(Number(yearText), Number(monthText) - 1 + offset, 1)
  return `${base.getFullYear()}-${zeroPad(base.getMonth() + 1)}`
}

export function formatCalendarMonthLabel(month: string): string {
  const fallback = searchDateToCalendarMonth(getTodaySearchDate())!
  const source = isValidCalendarMonth(month) ? month : fallback
  const [yearText, monthText] = source.split("-")
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(new Date(Number(yearText), Number(monthText) - 1, 1))
}

export function buildCalendarDayCells(month: string): CalendarDayCell[] {
  const fallback = searchDateToCalendarMonth(getTodaySearchDate())!
  const source = isValidCalendarMonth(month) ? month : fallback
  const [yearText, monthText] = source.split("-")
  const year = Number(yearText)
  const monthIndex = Number(monthText) - 1
  const firstDay = new Date(year, monthIndex, 1)
  const firstDayOfWeek = firstDay.getDay()
  const firstVisibleDate = new Date(year, monthIndex, 1 - firstDayOfWeek)

  return Array.from({ length: 42 }, (_, index) => {
    const current = new Date(firstVisibleDate)
    current.setDate(firstVisibleDate.getDate() + index)
    return {
      date: `${current.getFullYear()}-${zeroPad(current.getMonth() + 1)}-${zeroPad(current.getDate())}`,
      day: current.getDate(),
      inCurrentMonth: current.getMonth() === monthIndex,
    }
  })
}

export function buildVisitCountsByDate(visitDayCounts: VisitDayCountLike[] | undefined, month: string): Record<string, number> {
  if (!visitDayCounts?.length || !isValidCalendarMonth(month)) {
    return {}
  }

  const monthPrefix = `${month}-`
  return visitDayCounts.reduce<Record<string, number>>((counts, visitDayCount) => {
    const date = dayObsToSearchDate(visitDayCount.day_obs)
    if (!date.startsWith(monthPrefix)) {
      return counts
    }
    counts[date] = visitDayCount.count
    return counts
  }, {})
}
