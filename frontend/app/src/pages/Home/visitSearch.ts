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


export function isValidMonthValue(value: string): boolean {
  return /^\d{4}-\d{2}$/.test(value)
}


export function monthValueToYearMonth(value: string): { year: number, month: number } | undefined {
  if (!isValidMonthValue(value)) {
    return undefined
  }

  const [year, month] = value.split("-")
  return {
    year: Number(year),
    month: Number(month),
  }
}


export function getCurrentMonthValue(now: Date = new Date()): string {
  const year = now.getFullYear()
  const month = `${now.getMonth() + 1}`.padStart(2, "0")
  return `${year}-${month}`
}


export function buildVisitMonthlyCountsQuery(
  monthValue: string,
  dataType: ListVisitMonthlyCountsApiArg["dataType"],
  repositoryName: ListVisitMonthlyCountsApiArg["repositoryName"],
): ListVisitMonthlyCountsApiArg | undefined {
  const yearMonth = monthValueToYearMonth(monthValue)
  if (yearMonth === undefined) {
    return undefined
  }

  return {
    ...yearMonth,
    dataType,
    repositoryName,
  }
}


export function buildMonthDayCounts(monthValue: string, counts: VisitDayCount[]): Array<VisitDayCount & { day: number }> {
  const yearMonth = monthValueToYearMonth(monthValue)
  if (yearMonth === undefined) {
    return []
  }

  const daysInMonth = new Date(yearMonth.year, yearMonth.month, 0).getDate()
  const countsByDayObs = new Map(counts.map((count) => [count.day_obs, count.count]))

  return Array.from({ length: daysInMonth }, (_, index) => {
    const day = index + 1
    const dayObs = yearMonth.year * 10000 + yearMonth.month * 100 + day

    return {
      day,
      day_obs: dayObs,
      count: countsByDayObs.get(dayObs) ?? 0,
    }
  })
}


export function extractSearchDateFromVisitId(visitId: string): string {
  const parts = visitId.split(":")
  const last = parts[parts.length - 1]

  if (!last?.match(/^\d{13}$/)) {
    return ""
  }

  return `${last.slice(0, 4)}-${last.slice(4, 6)}-${last.slice(6, 8)}`
}
