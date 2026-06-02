import type { ListVisitsApiArg } from "../../store/api/openapi"
import { buildByUuidVisitName as buildByUuidVisitNameInternal, parseScopeId } from "../../quicklookId"

type QueryBuildResult = {
  args: ListVisitsApiArg | null
  error: string | null
}

function parseOptionalInteger(value: string | null, name: string): { value?: number, error?: string } {
  if (!value) {
    return {}
  }
  if (!/^\d+$/.test(value)) {
    return { error: `${name} must be an integer.` }
  }
  return { value: Number(value) }
}

export function normalizeQueryInput(input: string): string {
  return input.trim().replace(/^\/query\?/, "").replace(/^\?/, "")
}

export function buildDefaultQueryInput(dataSource: string | null | undefined, limit = 2): string {
  if (!dataSource) {
    return ""
  }
  let scope
  try {
    scope = parseScopeId(dataSource)
  } catch {
    return ""
  }
  const params = new URLSearchParams({
    repository_name: scope.repositoryName,
    collection: scope.collection,
    dataset_type: scope.datasetType,
    limit: String(limit),
  })
  return params.toString()
}

export function buildVisitListArgs(searchParams: URLSearchParams): QueryBuildResult {
  const repositoryName = searchParams.get("repository_name")
  const collection = searchParams.get("collection")
  const datasetType = searchParams.get("dataset_type")
  if (!repositoryName || !collection || !datasetType) {
    return { args: null, error: null }
  }

  const limit = parseOptionalInteger(searchParams.get("limit"), "limit")
  if (limit.error) {
    return { args: null, error: limit.error }
  }
  const offset = parseOptionalInteger(searchParams.get("offset"), "offset")
  if (offset.error) {
    return { args: null, error: offset.error }
  }

  return {
    args: {
      repositoryName,
      collection,
      datasetType,
      where: searchParams.get("where"),
      orderBy: searchParams.get("order_by"),
      reverse: searchParams.get("reverse") === null ? undefined : searchParams.get("reverse") === "true",
      ...(limit.value !== undefined ? { limit: limit.value } : {}),
      ...(offset.value !== undefined ? { offset: offset.value } : {}),
    },
    error: null,
  }
}

export function buildByUuidVisitName(visitName: string, uuid: string): string {
  return buildByUuidVisitNameInternal(visitName, uuid)
}
