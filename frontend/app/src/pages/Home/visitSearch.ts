import { ListVisitMonthlyCountsApiArg, ListVisitsApiArg, VisitDayCount } from "../../store/api/openapi"

export function isValidSearchDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value)
}

export function searchDateToDayObs(value: string): number | undefined {
  if (!isValidSearchDate(value)) {
    return undefined
  }

  return Number(value.split("-").join(""))
}

export function buildVisitListQuery(
  searchDate: string,
  dataType: ListVisitsApiArg["dataType"],
  repositoryName: ListVisitsApiArg["repositoryName"],
): ListVisitsApiArg {
  const dayObs = searchDateToDayObs(searchDate)

  if (dayObs === undefined) {
    return { dataType, repositoryName }
  }

  return { dayObs, dataType, repositoryName }
}


export function dayObsToSearchDate(dayObs: number): string {
  const value = String(dayObs)
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
}


export function getCurrentYearMonth(now: Date = new Date()): { year: number, month: number } {
  return {
    year: now.getFullYear(),
    month: now.getMonth() + 1,
  }
}


export function buildVisitMonthlyCountsQuery(
  year: number,
  month: number,
  dataType: ListVisitMonthlyCountsApiArg["dataType"],
  repositoryName: ListVisitMonthlyCountsApiArg["repositoryName"],
): ListVisitMonthlyCountsApiArg {
  return {
    year,
    month,
    dataType,
    repositoryName,
  }
}


export function buildMonthDayCounts(year: number, month: number, counts: VisitDayCount[]): Array<VisitDayCount & { day: number }> {
  const daysInMonth = new Date(year, month, 0).getDate()
  const countsByDayObs = new Map(counts.map((count) => [count.day_obs, count.count]))

  return Array.from({ length: daysInMonth }, (_, index) => {
    const day = index + 1
    const dayObs = year * 10000 + month * 100 + day

    return {
      day,
      day_obs: dayObs,
      count: countsByDayObs.get(dayObs) ?? 0,
    }
  })
}


export function buildCalendarDayCounts(
  year: number,
  month: number,
  counts: VisitDayCount[],
): Array<(VisitDayCount & { day: number }) | null> {
  const dayCounts = buildMonthDayCounts(year, month, counts)
  const firstWeekday = new Date(year, month - 1, 1).getDay()
  const calendarDays: Array<(VisitDayCount & { day: number }) | null> = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...dayCounts,
  ]

  while (calendarDays.length % 7 !== 0) {
    calendarDays.push(null)
  }

  return calendarDays
}


export function extractSearchDateFromVisitId(visitId: string): string {
  const parts = visitId.split(":")
  const last = parts[parts.length - 1]

  if (!last?.match(/^\d{13}$/)) {
    return ""
  }

  return `${last.slice(0, 4)}-${last.slice(4, 6)}-${last.slice(6, 8)}`
}
