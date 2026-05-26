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

function parseOptionalNumber(value: string | null, name: string): { value?: number, error?: string } {
  if (!value) {
    return {}
  }
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return { error: `${name} must be a number.` }
  }
  return { value: parsed }
}

export function normalizeQueryInput(input: string): string {
  return input.trim().replace(/^\/query\?/, "").replace(/^\?/, "")
}

export function buildDefaultQueryInput(dataSource: string | null | undefined, limit = 100): string {
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
  const raDeg = parseOptionalNumber(searchParams.get("ra_deg"), "ra_deg")
  if (raDeg.error) {
    return { args: null, error: raDeg.error }
  }
  const decDeg = parseOptionalNumber(searchParams.get("dec_deg"), "dec_deg")
  if (decDeg.error) {
    return { args: null, error: decDeg.error }
  }
  const radiusDeg = parseOptionalNumber(searchParams.get("radius_deg"), "radius_deg")
  if (radiusDeg.error) {
    return { args: null, error: radiusDeg.error }
  }
  const order = searchParams.get("order")?.trim()
  if (order === "") {
    return { args: null, error: "order must not be empty." }
  }

  const spatialValues = [raDeg.value, decDeg.value, radiusDeg.value]
  const spatialCount = spatialValues.filter((value) => value !== undefined).length
  if (spatialCount !== 0 && spatialCount !== 3) {
    return { args: null, error: "ra_deg, dec_deg, and radius_deg must be specified together." }
  }
  if (raDeg.value !== undefined && (raDeg.value < 0 || raDeg.value >= 360)) {
    return { args: null, error: "ra_deg must be in [0, 360)." }
  }
  if (decDeg.value !== undefined && (decDeg.value < -90 || decDeg.value > 90)) {
    return { args: null, error: "dec_deg must be in [-90, 90]." }
  }
  if (radiusDeg.value !== undefined && radiusDeg.value < 0) {
    return { args: null, error: "radius_deg must be >= 0." }
  }

  return {
    args: {
      dataType,
      repositoryName,
      ...(limit.value !== undefined ? { limit: limit.value } : {}),
      ...(exposure.value !== undefined ? { exposure: exposure.value } : {}),
      ...(offset.value !== undefined ? { offset: offset.value } : {}),
      ...(dayObs.value !== undefined ? { dayObs: dayObs.value } : {}),
      ...(order ? { order } : {}),
      ...(raDeg.value !== undefined ? { raDeg: raDeg.value } : {}),
      ...(decDeg.value !== undefined ? { decDeg: decDeg.value } : {}),
      ...(radiusDeg.value !== undefined ? { radiusDeg: radiusDeg.value } : {}),
    },
    error: null,
  }
}
