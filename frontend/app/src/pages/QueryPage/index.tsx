import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { env } from "../../env"
import { useListVisitsQuery, VisitEntry } from "../../store/api/openapi"
import { buildByUuidVisitName, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

const DEFAULT_LIMIT = "100"

type QueryFormState = {
  repositoryName: string
  collection: string
  datasetType: string
  orderBy: string
  reverse: boolean
  limit: string
  where: string
}

type QueryWhereExample = {
  label: string
  where: string
}

type QueryBuilderOptions = {
  repositories: string[]
  collections: string[]
  dataset_types: string[]
  where_examples: QueryWhereExample[]
}

const EMPTY_OPTIONS: QueryBuilderOptions = {
  repositories: [],
  collections: [],
  dataset_types: [],
  where_examples: [],
}

export function QueryPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentQuery = searchParams.toString()
  const effectiveSearchParams = useMemo(() => new URLSearchParams(currentQuery), [currentQuery])
  const [queryInput, setQueryInput] = useState(() => normalizeQueryInput(currentQuery))
  const [form, setForm] = useState<QueryFormState>(createEmptyForm)
  const [options, setOptions] = useState<QueryBuilderOptions>(EMPTY_OPTIONS)
  const [optionsError, setOptionsError] = useState<string | null>(null)
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [openError, setOpenError] = useState<string | null>(null)
  const [openingVisit, setOpeningVisit] = useState<string | null>(null)
  const parsedQuery = useMemo(() => buildVisitListArgs(effectiveSearchParams), [effectiveSearchParams])
  const { data, error, isFetching, isLoading } = useListVisitsQuery(parsedQuery.args!, {
    skip: parsedQuery.args === null || parsedQuery.error !== null,
    refetchOnMountOrArgChange: true,
  })
  const orderByOptions = useMemo(() => getDatasetOrderFields(form.datasetType), [form.datasetType])

  useEffect(() => {
    const normalizedQuery = normalizeQueryInput(currentQuery)
    setQueryInput(normalizedQuery)
    setForm((current) => mergeFormWithSearchParams(current, new URLSearchParams(normalizedQuery)))
  }, [currentQuery])

  useEffect(() => {
    const controller = new AbortController()
    setLoadingOptions(true)
    setOptionsError(null)
    void fetchQueryBuilderOptions(
      {
        repositoryName: form.repositoryName,
        collection: form.collection,
        datasetType: form.datasetType,
      },
      controller.signal,
    ).then((nextOptions) => {
      setOptions(nextOptions)
      setForm((current) => normalizeFormState(current, nextOptions))
    }).catch((fetchError) => {
      if (controller.signal.aborted) {
        return
      }
      setOptions(EMPTY_OPTIONS)
      setOptionsError(fetchError instanceof Error ? fetchError.message : "Failed to load query options.")
    }).finally(() => {
      if (!controller.signal.aborted) {
        setLoadingOptions(false)
      }
    })
    return () => controller.abort()
  }, [form.collection, form.datasetType, form.repositoryName])

  const applyForm = useCallback((nextForm: QueryFormState) => {
    setForm(nextForm)
    setQueryInput(buildQueryInput(nextForm))
  }, [])

  const updateRepository = useCallback((repositoryName: string) => {
    applyForm({
      ...form,
      repositoryName,
      collection: "",
      datasetType: "",
      orderBy: "day_obs",
    })
  }, [applyForm, form])

  const updateCollection = useCallback((collection: string) => {
    applyForm({
      ...form,
      collection,
      datasetType: "",
      orderBy: "day_obs",
    })
  }, [applyForm, form])

  const updateDatasetType = useCallback((datasetType: string) => {
    const nextOrderBy = getDatasetOrderFields(datasetType)[0] ?? "day_obs"
    applyForm({
      ...form,
      datasetType,
      orderBy: nextOrderBy,
    })
  }, [applyForm, form])

  const updateWhereExample = useCallback((where: string) => {
    applyForm({
      ...form,
      where,
    })
  }, [applyForm, form])

  const handleRawQueryChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const nextQuery = normalizeQueryInput(event.target.value)
    setQueryInput(nextQuery)
    setForm((current) => mergeFormWithSearchParams(current, new URLSearchParams(nextQuery)))
  }, [])

  const commitQuery = useCallback(() => {
    const normalized = normalizeQueryInput(queryInput)
    navigate(normalized ? `/query?${normalized}` : "/query")
  }, [navigate, queryInput])

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
          Build a query string for arbitrary `repository` / `collection` / `dataset_type`, or edit the query string directly.
        </p>
        <form onSubmit={handleSubmit} style={sectionStyle}>
          <label style={fullWidthFieldStyle}>
            <span>Query string</span>
            <input
              spellCheck={false}
              type="text"
              value={queryInput}
              onChange={handleRawQueryChange}
              placeholder="repository_name=embargo&collection=LSSTCam/raw/all&dataset_type=raw&limit=100"
            />
          </label>
          <div style={helperFieldsStyle}>
            <label style={fieldStyle}>
              <span>Repository</span>
              <select value={form.repositoryName} onChange={(event) => updateRepository(event.target.value)}>
                <option value="">Select repository</option>
                {options.repositories.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label style={fieldStyle}>
              <span>Collection</span>
              <select value={form.collection} onChange={(event) => updateCollection(event.target.value)}>
                <option value="">Select collection</option>
                {options.collections.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label style={fieldStyle}>
              <span>Dataset Type</span>
              <select value={form.datasetType} onChange={(event) => updateDatasetType(event.target.value)}>
                <option value="">Select dataset type</option>
                {options.dataset_types.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label style={fieldStyle}>
              <span>Order By</span>
              <select value={form.orderBy} onChange={(event) => applyForm({ ...form, orderBy: event.target.value })}>
                {orderByOptions.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label style={fieldStyle}>
              <span>Limit</span>
              <input
                inputMode="numeric"
                type="text"
                value={form.limit}
                onChange={(event) => applyForm({ ...form, limit: event.target.value })}
              />
            </label>
            <label style={checkboxStyle}>
              <input
                checked={form.reverse}
                onChange={(event) => applyForm({ ...form, reverse: event.target.checked })}
                type="checkbox"
              />
              <span>Reverse</span>
            </label>
            <label style={fieldStyle}>
              <span>Where examples</span>
              <select value="" onChange={(event) => updateWhereExample(event.target.value)}>
                <option value="">Select example</option>
                {options.where_examples.map((example) => (
                  <option key={`${example.label}:${example.where}`} value={example.where}>{example.label}</option>
                ))}
              </select>
            </label>
            <label style={wideFieldStyle}>
              <span>Where</span>
              <input
                spellCheck={false}
                type="text"
                value={form.where}
                onChange={(event) => applyForm({ ...form, where: event.target.value })}
              />
            </label>
          </div>
          <div style={buttonRowStyle}>
            <button type="submit">Search</button>
            {loadingOptions && <span>Loading query options...</span>}
          </div>
        </form>
      </div>

      {optionsError && <p role="alert">{optionsError}</p>}
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

function createEmptyForm(): QueryFormState {
  return {
    repositoryName: "",
    collection: "",
    datasetType: "",
    orderBy: "day_obs",
    reverse: false,
    limit: DEFAULT_LIMIT,
    where: "",
  }
}

function buildQueryInput(form: QueryFormState): string {
  const params = new URLSearchParams()
  if (form.repositoryName) params.set("repository_name", form.repositoryName)
  if (form.collection) params.set("collection", form.collection)
  if (form.datasetType) params.set("dataset_type", form.datasetType)
  if (form.orderBy) params.set("order_by", form.orderBy)
  if (form.reverse) params.set("reverse", "true")
  if (form.limit) params.set("limit", form.limit)
  if (form.where) params.set("where", form.where)
  return params.toString()
}

function mergeFormWithSearchParams(form: QueryFormState, searchParams: URLSearchParams): QueryFormState {
  return {
    repositoryName: searchParams.get("repository_name") ?? form.repositoryName,
    collection: searchParams.get("collection") ?? form.collection,
    datasetType: searchParams.get("dataset_type") ?? form.datasetType,
    orderBy: searchParams.get("order_by") ?? form.orderBy,
    reverse: searchParams.has("reverse") ? searchParams.get("reverse") === "true" : form.reverse,
    limit: searchParams.get("limit") ?? form.limit,
    where: searchParams.get("where") ?? form.where,
  }
}

function normalizeFormState(form: QueryFormState, options: QueryBuilderOptions): QueryFormState {
  const repositoryName = options.repositories.includes(form.repositoryName)
    ? form.repositoryName
    : (options.repositories[0] ?? "")
  const collection = options.collections.includes(form.collection)
    ? form.collection
    : (options.collections[0] ?? "")
  const datasetType = options.dataset_types.includes(form.datasetType)
    ? form.datasetType
    : (options.dataset_types[0] ?? "")
  const orderByFields = getDatasetOrderFields(datasetType)
  const orderBy = orderByFields.includes(form.orderBy) ? form.orderBy : (orderByFields[0] ?? "day_obs")
  return {
    ...form,
    repositoryName,
    collection,
    datasetType,
    orderBy,
    limit: form.limit || DEFAULT_LIMIT,
  }
}

function getDatasetOrderFields(datasetType: string): string[] {
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

async function fetchQueryBuilderOptions(
  input: { repositoryName: string, collection: string, datasetType: string },
  signal: AbortSignal,
): Promise<QueryBuilderOptions> {
  const params = new URLSearchParams()
  if (input.repositoryName) params.set("repository_name", input.repositoryName)
  if (input.collection) params.set("collection", input.collection)
  if (input.datasetType) params.set("dataset_type", input.datasetType)
  const url = `${env.baseUrl}/api/visits/query_builder_options${params.size > 0 ? `?${params}` : ""}`
  const response = await fetch(url, { signal })
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail ?? "Failed to load query options.")
  }
  const payload: unknown = await response.json()
  if (
    typeof payload !== "object" ||
    payload === null ||
    !Array.isArray((payload as { repositories?: unknown }).repositories) ||
    !Array.isArray((payload as { collections?: unknown }).collections) ||
    !Array.isArray((payload as { dataset_types?: unknown }).dataset_types) ||
    !Array.isArray((payload as { where_examples?: unknown }).where_examples)
  ) {
    throw new Error("Failed to load query options.")
  }
  return payload as QueryBuilderOptions
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

const helperFieldsStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "12px",
  alignItems: "flex-end",
} as const

const fieldStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
  minWidth: "180px",
  flex: "1 1 180px",
} as const

const wideFieldStyle = {
  ...fieldStyle,
  minWidth: "280px",
  flex: "999 1 320px",
} as const

const fullWidthFieldStyle = {
  ...fieldStyle,
  minWidth: "100%",
} as const

const checkboxStyle = {
  display: "flex",
  gap: "8px",
  alignItems: "center",
  minHeight: "38px",
  flex: "0 0 auto",
} as const

const buttonRowStyle = {
  display: "flex",
  gap: "12px",
  alignItems: "center",
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
