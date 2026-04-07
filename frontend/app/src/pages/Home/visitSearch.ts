import { ListVisitsApiArg } from "../../store/api/openapi"

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

export function extractSearchDateFromVisitId(visitId: string): string {
  const parts = visitId.split(":")
  const last = parts[parts.length - 1]

  if (!last?.match(/^\d{13}$/)) {
    return ""
  }

  return `${last.slice(0, 4)}-${last.slice(4, 6)}-${last.slice(6, 8)}`
}
