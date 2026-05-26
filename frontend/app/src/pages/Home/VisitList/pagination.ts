import type { ListVisitsApiArg, ListVisitsApiResponse } from "../../../store/api/openapi"

export const VISIT_LIST_PAGE_SIZE = 1000
const VISIT_LIST_QUERY_LIMIT = VISIT_LIST_PAGE_SIZE + 1

export function buildVisitListPageQuery(query: ListVisitsApiArg, page: number): ListVisitsApiArg {
  const normalizedPage = Math.max(page, 0)
  return {
    ...query,
    limit: VISIT_LIST_QUERY_LIMIT,
    offset: normalizedPage * VISIT_LIST_PAGE_SIZE,
  }
}

export function getVisibleVisitEntries(entries: ListVisitsApiResponse | undefined): ListVisitsApiResponse {
  return entries?.slice(0, VISIT_LIST_PAGE_SIZE) ?? []
}

export function hasNextVisitPage(entries: ListVisitsApiResponse | undefined): boolean {
  return (entries?.length ?? 0) > VISIT_LIST_PAGE_SIZE
}

export function shouldShowVisitPagination(page: number, hasNextPage: boolean): boolean {
  return page > 0 || hasNextPage
}
