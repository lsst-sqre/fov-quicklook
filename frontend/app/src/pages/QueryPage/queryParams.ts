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

function pythonStringLiteral(value: string): string {
  return `'${value
    .replace(/\\/g, "\\\\")
    .replace(/'/g, "\\'")
    .replace(/\n/g, "\\n")}'`
}

export function buildDefaultQueryInput(dataSource: string | null | undefined, limit = 100): string {
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

export function buildQueryPythonSnippet(queryInput: string, baseUrl: string): string {
  const searchParams = new URLSearchParams(normalizeQueryInput(queryInput))
  const paramsEntries = Array.from(searchParams.entries())
  const paramsLiteral = paramsEntries.length === 0
    ? "{}"
    : `{\n${paramsEntries.map(([key, value]) => `    ${pythonStringLiteral(key)}: ${pythonStringLiteral(value)},`).join("\n")}\n}`

  return [
    "import requests",
    "",
    `BASE_URL = ${pythonStringLiteral(baseUrl)}`,
    "GAFAELFAWR_TOKEN = '<set gafaelfawr token here>'",
    "",
    `params = ${paramsLiteral}`,
    "",
    "response = requests.get(",
    "    f\"{BASE_URL}/api/visits\",",
    "    params=params,",
    "    cookies={'gafaelfawr': GAFAELFAWR_TOKEN},",
    "    timeout=30,",
    ")",
    "response.raise_for_status()",
    "",
    "for visit in response.json():",
    "    print(visit['display_id'])",
  ].join("\n")
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
      reverse: searchParams.get("reverse") === null ? undefined : searchParams.get("reverse") === "true",
      ...(searchParams.get("where") !== null ? { where: searchParams.get("where")! } : {}),
      ...(searchParams.get("order_by") !== null ? { orderBy: searchParams.get("order_by")! } : {}),
      ...(limit.value !== undefined ? { limit: limit.value } : {}),
      ...(offset.value !== undefined ? { offset: offset.value } : {}),
    },
    error: null,
  }
}

export function buildByUuidVisitName(visitName: string, uuid: string): string {
  return buildByUuidVisitNameInternal(visitName, uuid)
}
