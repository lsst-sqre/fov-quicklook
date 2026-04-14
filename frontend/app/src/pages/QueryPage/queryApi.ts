export function buildButlerQueryApiUrl(baseUrl: string, searchParams: URLSearchParams): string {
  const query = searchParams.toString()
  return `${baseUrl}/api/butler/query${query ? `?${query}` : ""}`
}


export function buildButlerDatasetTypesApiUrl(baseUrl: string, repositoryName?: string | null): string {
  if (!repositoryName) {
    return `${baseUrl}/api/butler/dataset_types`
  }

  const params = new URLSearchParams({ repository_name: repositoryName })
  return `${baseUrl}/api/butler/dataset_types?${params.toString()}`
}


export function buildButlerDimensionsApiUrl(baseUrl: string, dataType: string, repositoryName?: string | null): string {
  const params = new URLSearchParams()
  if (repositoryName) {
    params.set("repository_name", repositoryName)
  }
  const query = params.toString()
  return `${baseUrl}/api/butler/dataset_types/${encodeURIComponent(dataType)}/dimensions${query ? `?${query}` : ""}`
}


export function formatQueryCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return ""
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value)
  }
  return JSON.stringify(value)
}
