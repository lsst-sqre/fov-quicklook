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
    where: "",
  })
  return params.toString()
}

export function buildQueryPythonSnippet(queryInput: string): string {
  const normalizedQuery = normalizeQueryInput(queryInput)

  return [
    "from itertools import islice",
    "from urllib.parse import parse_qs",
    "",
    "from lsst.daf.butler import Butler",
    "",
    "def quicklook_dimension(dataset_type: str) -> str:",
    "    if dataset_type in {'difference_image', 'preliminary_visit_image'}:",
    "        return 'visit'",
    "    return 'exposure'",
    "",
    "def default_order_by(dataset_type: str) -> str:",
    "    return {",
    "        'raw': '-day_obs',",
    "        'post_isr_image': '-exposure',",
    "        'difference_image': '-visit',",
    "        'preliminary_visit_image': '-visit',",
    "        'calexp': '-exposure',",
    "    }.get(dataset_type, '-exposure')",
    "",
    "def normalize_order_by(dataset_type: str, order_by: str | None, reverse: bool | None) -> list[str]:",
    "    default = default_order_by(dataset_type)",
    "    selected_field = order_by or default.removeprefix('-')",
    "    selected_reverse = default.startswith('-') if selected_field == default.removeprefix('-') else False",
    "    if reverse:",
    "        selected_reverse = not selected_reverse",
    "    prefix = '-' if selected_reverse else ''",
    "    return [f'{prefix}{selected_field}']",
    "",
    `query_string = ${pythonStringLiteral(normalizedQuery)}`,
    "params = {key: values[-1] for key, values in parse_qs(query_string, keep_blank_values=True).items()}",
    "",
    "repository_name = params['repository_name']",
    "collection = params.get('collection')",
    "dataset_type = params['dataset_type']",
    "where = params.get('where')",
    "order_by = params.get('order_by')",
    "reverse = None if 'reverse' not in params else params['reverse'].lower() == 'true'",
    "limit = int(params['limit']) if 'limit' in params else 100",
    "offset = int(params['offset']) if 'offset' in params else 0",
    "",
    "butler_kwargs = {'instrument': 'LSSTCam'}",
    "if collection:",
    "    butler_kwargs['collections'] = [collection]",
    "butler = Butler(repository_name, **butler_kwargs)",
    "dimension = quicklook_dimension(dataset_type)",
    "query_kwargs = {'datasets': dataset_type}",
    "if dataset_type == 'difference_image' and collection:",
    "    query_kwargs['collections'] = ...",
    "if where is None:",
    "    latest_records = list(",
    "        butler.registry.queryDimensionRecords(dimension, **query_kwargs).order_by('-day_obs').limit(1)",
    "    )",
    "    if latest_records:",
    "        query_kwargs['where'] = f\"day_obs={int(latest_records[0].day_obs)}\"",
    "elif where:",
    "    query_kwargs['where'] = where",
    "",
    "records = butler.registry.queryDimensionRecords(dimension, **query_kwargs).order_by(",
    "    *normalize_order_by(dataset_type, order_by, reverse)",
    ")",
    "if offset > 0:",
    "    records = islice(records, offset, offset + limit)",
    "else:",
    "    records = records.limit(limit)",
    "",
    "for record in records:",
    "    print(record)",
  ].join("\n")
}

export function buildVisitListArgs(searchParams: URLSearchParams): QueryBuildResult {
  const repositoryName = searchParams.get("repository_name")
  const datasetType = searchParams.get("dataset_type")
  if (!repositoryName || !datasetType) {
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
      datasetType,
      ...(searchParams.get("collection") !== null ? { collection: searchParams.get("collection")! } : {}),
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
