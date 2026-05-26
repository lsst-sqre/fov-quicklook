import type { ListVisitsApiArg } from "../../store/api/openapi"

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

  const separatorIndex = dataSource.indexOf(":")
  if (separatorIndex <= 0 || separatorIndex >= dataSource.length - 1) {
    return ""
  }

  const repositoryName = dataSource.slice(0, separatorIndex)
  const dataType = dataSource.slice(separatorIndex + 1)
  const params = new URLSearchParams({
    data_type: dataType,
    repository_name: repositoryName,
    limit: String(limit),
  })
  return params.toString()
}

export function buildVisitListArgs(searchParams: URLSearchParams): QueryBuildResult {
  const dataType = searchParams.get("data_type")
  const repositoryName = searchParams.get("repository_name")
  if (!dataType || !repositoryName) {
    return { args: null, error: null }
  }

  const limit = parseOptionalInteger(searchParams.get("limit"), "limit")
  if (limit.error) {
    return { args: null, error: limit.error }
  }
  const exposure = parseOptionalInteger(searchParams.get("exposure"), "exposure")
  if (exposure.error) {
    return { args: null, error: exposure.error }
  }
  const offset = parseOptionalInteger(searchParams.get("offset"), "offset")
  if (offset.error) {
    return { args: null, error: offset.error }
  }
  const dayObs = parseOptionalInteger(searchParams.get("day_obs"), "day_obs")
  if (dayObs.error) {
    return { args: null, error: dayObs.error }
  }

  return {
    args: {
      dataType,
      repositoryName,
      ...(limit.value !== undefined ? { limit: limit.value } : {}),
      ...(exposure.value !== undefined ? { exposure: exposure.value } : {}),
      ...(offset.value !== undefined ? { offset: offset.value } : {}),
      ...(dayObs.value !== undefined ? { dayObs: dayObs.value } : {}),
    },
    error: null,
  }
}

export function buildByUuidVisitName(visitName: string, uuid: string): string {
  const repositoryName = visitName.split(":", 1)[0]
  return `${repositoryName}:by_uuid:${uuid}`
}
