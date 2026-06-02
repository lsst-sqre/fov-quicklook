import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { env } from "../../env"
import { ButlerScopeConfig, useListVisitsQuery, VisitEntry } from "../../store/api/openapi"
import { useAppSelector } from "../../store/hooks"
import { buildByUuidVisitName, buildDefaultQueryInput, buildVisitListArgs } from "./queryParams"

type QueryFormState = {
  repositoryName: string
  collection: string
  datasetType: string
  orderBy: string
  reverse: boolean
  limit: string
  where: string
}

export function QueryPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentQuery = searchParams.toString()
  const currentDataSource = useAppSelector((state) => state.home.dataSource)
  const butlerScopes = useAppSelector((state) => state.copyTemplate.butlerScopes)
  const defaultQuery = useMemo(() => buildDefaultQueryInput(currentDataSource), [currentDataSource])
  const effectiveQuery = currentQuery || defaultQuery
  const effectiveSearchParams = useMemo(() => new URLSearchParams(effectiveQuery), [effectiveQuery])
  const [openError, setOpenError] = useState<string | null>(null)
  const [openingVisit, setOpeningVisit] = useState<string | null>(null)
  const [form, setForm] = useState<QueryFormState>(() => buildFormState(effectiveSearchParams, butlerScopes))

  useEffect(() => {
    setForm(buildFormState(effectiveSearchParams, butlerScopes))
  }, [butlerScopes, effectiveSearchParams])

  useEffect(() => {
    if (!currentQuery && defaultQuery) {
      navigate(`/query?${defaultQuery}`, { replace: true })
    }
  }, [currentQuery, defaultQuery, navigate])

  const parsedQuery = useMemo(() => buildVisitListArgs(effectiveSearchParams), [effectiveSearchParams])
  const { data, error, isFetching, isLoading } = useListVisitsQuery(parsedQuery.args!, {
    skip: parsedQuery.args === null || parsedQuery.error !== null,
    refetchOnMountOrArgChange: true,
  })

  const repositoryOptions = useMemo(
    () => [...new Set(butlerScopes.map((scope) => scope.repository_name ?? "embargo"))],
    [butlerScopes],
  )
  const collectionOptions = useMemo(
    () => [...new Set(
      butlerScopes
        .filter((scope) => (scope.repository_name ?? "embargo") === form.repositoryName)
        .map((scope) => scope.collection),
    )],
    [butlerScopes, form.repositoryName],
  )
  const datasetTypeOptions = useMemo(
    () => butlerScopes
      .filter((scope) =>
        (scope.repository_name ?? "embargo") === form.repositoryName &&
        scope.collection === form.collection,
      )
      .map((scope) => scope.dataset_type),
    [butlerScopes, form.collection, form.repositoryName],
  )
  const orderByOptions = useMemo(
    () => getDatasetOrderFields(form.datasetType, butlerScopes),
    [butlerScopes, form.datasetType],
  )

  const updateRepository = useCallback((repositoryName: string) => {
    setForm((current) => normalizeFormState({
      ...current,
      repositoryName,
    }, butlerScopes))
  }, [butlerScopes])

  const updateCollection = useCallback((collection: string) => {
    setForm((current) => normalizeFormState({
      ...current,
      collection,
    }, butlerScopes))
  }, [butlerScopes])

  const updateDatasetType = useCallback((datasetType: string) => {
    setForm((current) => normalizeFormState({
      ...current,
      datasetType,
    }, butlerScopes))
  }, [butlerScopes])

  const commitQuery = useCallback(() => {
    const params = new URLSearchParams()
    params.set("repository_name", form.repositoryName)
    params.set("collection", form.collection)
    params.set("dataset_type", form.datasetType)
    if (form.orderBy) params.set("order_by", form.orderBy)
    if (form.reverse) params.set("reverse", "true")
    if (form.limit) params.set("limit", form.limit)
    if (form.where) params.set("where", form.where)
    const query = params.toString()
    navigate(query ? `/query?${query}` : "/query")
  }, [form, navigate])

  const handleSubmit = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    commitQuery()
  }, [commitQuery])

  const openByUuid = useCallback(async (visitName: string) => {
    setOpenError(null)
    setOpeningVisit(visitName)
    try {
      const representativeUuid = await fetchRepresentativeUuid(visitName)
      navigate(`/visits/${encodeURIComponent(buildByUuidVisitName(visitName, representativeUuid))}`)
    } catch (e) {
      setOpenError(e instanceof Error ? e.message : "Failed to open the selected dataset.")
    } finally {
      setOpeningVisit((current) => current === visitName ? null : current)
    }
  }, [navigate])

  return (
    <div style={pageStyle}>
      <div style={sectionStyle}>
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Data Query</h1>
        <p style={hintStyle}>
          Choose a Butler scope and query options, then run the query.
        </p>
        <form onSubmit={handleSubmit} style={formGridStyle}>
          <label style={fieldStyle}>
            <span>Repository</span>
            <select value={form.repositoryName} onChange={(event) => updateRepository(event.target.value)}>
              {repositoryOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label style={fieldStyle}>
            <span>Collection</span>
            <select value={form.collection} onChange={(event) => updateCollection(event.target.value)}>
              {collectionOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label style={fieldStyle}>
            <span>Dataset Type</span>
            <select value={form.datasetType} onChange={(event) => updateDatasetType(event.target.value)}>
              {datasetTypeOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label style={fieldStyle}>
            <span>Order By</span>
            <select value={form.orderBy} onChange={(event) => setForm((current) => ({ ...current, orderBy: event.target.value }))}>
              {orderByOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label style={fieldStyle}>
            <span>Limit</span>
            <input
              inputMode="numeric"
              type="text"
              value={form.limit}
              onChange={(event) => setForm((current) => ({ ...current, limit: event.target.value }))}
            />
          </label>
          <label style={checkboxStyle}>
            <input
              checked={form.reverse}
              onChange={(event) => setForm((current) => ({ ...current, reverse: event.target.checked }))}
              type="checkbox"
            />
            <span>Reverse</span>
          </label>
          <label style={{ ...fieldStyle, gridColumn: "1 / -1" }}>
            <span>Where</span>
            <input
              spellCheck={false}
              type="text"
              value={form.where}
              onChange={(event) => setForm((current) => ({ ...current, where: event.target.value }))}
            />
          </label>
          <div style={{ gridColumn: "1 / -1", display: "flex", gap: "8px" }}>
            <button type="submit">Search</button>
          </div>
        </form>
      </div>

      {parsedQuery.error && <p role="alert">{parsedQuery.error}</p>}
      {openError && <p role="alert">{openError}</p>}
      {parsedQuery.args !== null && (
        <>
          <div style={summaryStyle}>
            <span>Results: {data?.length ?? 0}</span>
            {(isLoading || isFetching) && <span>Loading...</span>}
          </div>
          {error && <p role="alert">{formatQueryError(error)}</p>}
          {!isLoading && !error && data?.length === 0 && <p>No visits matched the query.</p>}
          {data && data.length > 0 && (
            <div style={tableContainerStyle}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th>Open</th>
                    <th>Visit</th>
                    <th>Day Obs</th>
                    <th>Filter</th>
                    <th>Exposure Time</th>
                    <th>Observation Type</th>
                    <th>Observation Reason</th>
                    <th>Science Program</th>
                    <th>Target</th>
                    <th>Obs ID</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((entry) => (
                    <VisitRow
                      entry={entry}
                      isOpening={openingVisit === entry.id}
                      key={entry.id}
                      onOpenByUuid={openByUuid}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function buildFormState(searchParams: URLSearchParams, scopes: ButlerScopeConfig[]): QueryFormState {
  return normalizeFormState({
    repositoryName: searchParams.get("repository_name") ?? scopes[0]?.repository_name ?? "embargo",
    collection: searchParams.get("collection") ?? scopes[0]?.collection ?? "",
    datasetType: searchParams.get("dataset_type") ?? scopes[0]?.dataset_type ?? "",
    orderBy: searchParams.get("order_by") ?? "day_obs",
    reverse: searchParams.get("reverse") === "true",
    limit: searchParams.get("limit") ?? "2",
    where: searchParams.get("where") ?? "",
  }, scopes)
}

function normalizeFormState(form: QueryFormState, scopes: ButlerScopeConfig[]): QueryFormState {
  const repositoryName = scopes.some((scope) => (scope.repository_name ?? "embargo") === form.repositoryName)
    ? form.repositoryName
    : (scopes[0]?.repository_name ?? "embargo")
  const repositoryScopes = scopes.filter((scope) => (scope.repository_name ?? "embargo") === repositoryName)
  const collection = repositoryScopes.some((scope) => scope.collection === form.collection)
    ? form.collection
    : (repositoryScopes[0]?.collection ?? "")
  const datasetType = repositoryScopes.some((scope) => scope.collection === collection && scope.dataset_type === form.datasetType)
    ? form.datasetType
    : (repositoryScopes.find((scope) => scope.collection === collection)?.dataset_type ?? "")
  const orderByFields = getDatasetOrderFields(datasetType, scopes)
  const orderBy = orderByFields.includes(form.orderBy) ? form.orderBy : (orderByFields[0] ?? "day_obs")
  return {
    ...form,
    repositoryName,
    collection,
    datasetType,
    orderBy,
  }
}

function getDatasetOrderFields(datasetType: string, scopes: ButlerScopeConfig[]): string[] {
  const defaultFields = ["day_obs", "exposure", "visit", "obs_id", "physical_filter", "exposure_time"]
  if (!datasetType) {
    return defaultFields
  }
  if (datasetType === "difference_image" || datasetType === "preliminary_visit_image") {
    return ["visit", ...defaultFields.filter((field) => field !== "visit")]
  }
  return defaultFields
}

function VisitRow(
  { entry, isOpening, onOpenByUuid }:
  { entry: VisitEntry, isOpening: boolean, onOpenByUuid: (visitName: string) => Promise<void> }
) {
  return (
    <tr>
      <td>
        <button aria-label={`Open ${entry.display_id} by UUID`} disabled={isOpening} onClick={() => void onOpenByUuid(entry.id)}>
          {isOpening ? "Opening..." : "Open by UUID"}
        </button>
      </td>
      <td>
        <Link to={`/visits/${encodeURIComponent(entry.id)}`}>{entry.display_id}</Link>
      </td>
      <td>{entry.day_obs}</td>
      <td>{entry.physical_filter}</td>
      <td>{entry.exposure_time}</td>
      <td>{entry.observation_type}</td>
      <td>{entry.observation_reason}</td>
      <td>{entry.science_program}</td>
      <td>{entry.target_name}</td>
      <td>{entry.obs_id}</td>
    </tr>
  )
}

async function fetchRepresentativeUuid(visitName: string): Promise<string> {
  const response = await fetch(
    `${env.baseUrl}/api/visits/${encodeURIComponent(visitName)}/representative_uuid`,
  )
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail ?? `Failed to resolve a dataset UUID for ${visitName}.`)
  }
  const payload: unknown = await response.json()
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("uuid" in payload) ||
    typeof payload.uuid !== "string"
  ) {
    throw new Error(`Failed to resolve a dataset UUID for ${visitName}.`)
  }
  return payload.uuid
}

async function readErrorDetail(response: Response): Promise<string | null> {
  const payload: unknown = await response.json().catch(() => null)
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail
  }
  return null
}

function formatQueryError(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "data" in error &&
    typeof error.data === "object" &&
    error.data !== null &&
    "detail" in error.data &&
    typeof error.data.detail === "string"
  ) {
    return error.data.detail
  }
  if (
    typeof error === "object" &&
    error !== null &&
    "status" in error
  ) {
    return `The query failed (${String(error.status)}).`
  }
  return "The query failed."
}

const pageStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
  height: "100%",
  overflow: "auto",
  padding: "16px",
  boxSizing: "border-box",
} as const

const sectionStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
} as const

const hintStyle = {
  margin: 0,
  lineHeight: 1.5,
} as const

const formGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
  gap: "12px",
  alignItems: "end",
} as const

const fieldStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
} as const

const checkboxStyle = {
  display: "flex",
  gap: "8px",
  alignItems: "center",
  minHeight: "38px",
} as const

const summaryStyle = {
  display: "flex",
  gap: "16px",
  alignItems: "center",
} as const

const tableContainerStyle = {
  overflow: "auto",
} as const

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
} as const
