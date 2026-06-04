import { ListVisitsApiArg } from "../../store/api/openapi"
import { getSingleDimensionValue, parseScopeId } from "../../quicklookId"

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
  scopeId: string,
): ListVisitsApiArg {
  const { repositoryName, collection, datasetType } = parseScopeId(scopeId)
  const dayObs = searchDateToDayObs(searchDate)

  if (dayObs === undefined) {
    return { repositoryName, collection, datasetType }
  }

  return { repositoryName, collection, datasetType, where: `day_obs=${dayObs}` }
}

export function extractSearchDateFromVisitId(visitId: string): string {
  const last = getSingleDimensionValue(visitId)

  if (!last?.match(/^\d{13}$/)) {
    return ""
  }

  return `${last.slice(0, 4)}-${last.slice(4, 6)}-${last.slice(6, 8)}`
}
