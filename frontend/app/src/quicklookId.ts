export function escapeVisitPathPart(value: string): string {
  return value.replace(/!/g, "!!").replace(/\//g, "!-")
}

export function unescapeVisitPathPart(value: string): string {
  let result = ""
  for (let i = 0; i < value.length; i += 1) {
    const char = value[i]
    if (char !== "!") {
      result += char
      continue
    }
    const next = value[i + 1]
    if (next === "!") {
      result += "!"
      i += 1
      continue
    }
    if (next === "-") {
      result += "/"
      i += 1
      continue
    }
    throw new Error(`Invalid escaped value: ${value}`)
  }
  return result
}

export type ScopeIdParts = {
  repositoryName: string
  collection: string
  datasetType: string
}

export type VisitIdParts = ScopeIdParts & {
  dimensions: Record<string, string>
  isByUuid: boolean
}

export function buildScopeId(parts: ScopeIdParts): string {
  return `${parts.repositoryName}:${escapeVisitPathPart(parts.collection)}:${parts.datasetType}`
}

export function buildVisitId(parts: ScopeIdParts & { dimensions: Record<string, string | number> }): string {
  const dimensions = Object.entries(parts.dimensions)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join(",")
  return `${parts.repositoryName}:${escapeVisitPathPart(parts.collection)}:${parts.datasetType}:${dimensions}`
}

export function parseScopeId(scopeId: string): ScopeIdParts {
  const [repositoryName, escapedCollection, datasetType] = scopeId.split(":", 3)
  if (!repositoryName || !escapedCollection || !datasetType) {
    throw new Error(`Invalid scope id: ${scopeId}`)
  }
  return {
    repositoryName,
    collection: unescapeVisitPathPart(escapedCollection),
    datasetType,
  }
}

export function parseVisitId(visitId: string): VisitIdParts {
  const parts = visitId.split(":")
  if (parts.length === 3 && parts[1] === "by_uuid") {
    return {
      repositoryName: parts[0],
      collection: "by_uuid",
      datasetType: "by_uuid",
      dimensions: { uuid: parts[2] },
      isByUuid: true,
    }
  }
  if (parts.length !== 4) {
    throw new Error(`Invalid visit id: ${visitId}`)
  }
  const [repositoryName, escapedCollection, datasetType, dimensionsText] = parts
  const dimensions = Object.fromEntries(
    dimensionsText.split(",").map((pair) => {
      const [key, value] = pair.split("=", 2)
      return [key, value]
    }),
  )
  return {
    repositoryName,
    collection: unescapeVisitPathPart(escapedCollection),
    datasetType,
    dimensions,
    isByUuid: false,
  }
}

export function extractScopeIdFromVisitId(visitId: string): string | undefined {
  try {
    const parsed = parseVisitId(visitId)
    if (parsed.isByUuid) {
      return undefined
    }
    return buildScopeId(parsed)
  } catch {
    return undefined
  }
}

export function getSingleDimensionValue(visitId: string): string | undefined {
  try {
    const values = Object.values(parseVisitId(visitId).dimensions)
    return values.length === 1 ? values[0] : undefined
  } catch {
    return undefined
  }
}

export function getSingleDimensionName(visitId: string): string | undefined {
  try {
    const keys = Object.keys(parseVisitId(visitId).dimensions)
    return keys.length === 1 ? keys[0] : undefined
  } catch {
    return undefined
  }
}

export function buildByUuidVisitName(visitId: string, uuid: string): string {
  const { repositoryName } = parseVisitId(visitId)
  return `${repositoryName}:by_uuid:${uuid}`
}
