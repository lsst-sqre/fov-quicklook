import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSelector } from "react-redux"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { env } from "../../env"
import { buildScopeId } from "../../quicklookId"
import { AppState } from "../../store"
import { ButlerScopeConfig, useListVisitsQuery, VisitEntry } from "../../store/api/openapi"
import { copyTextToClipboard } from "../../utils/copyTextToClipboard"
import { buildDefaultQueryInput, buildQueryPythonSnippet, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

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
  const butlerScopes = useSelector((state: AppState) => state.copyTemplate.butlerScopes)
  const currentQuery = searchParams.toString()
  const effectiveSearchParams = useMemo(() => new URLSearchParams(currentQuery), [currentQuery])
  const [queryInput, setQueryInput] = useState(() => normalizeQueryInput(currentQuery))
  const [form, setForm] = useState<QueryFormState>(createEmptyForm)
  const [options, setOptions] = useState<QueryBuilderOptions>(EMPTY_OPTIONS)
  const [optionsError, setOptionsError] = useState<string | null>(null)
  const [loadingOptions, setLoadingOptions] = useState(false)
  const appliedDefaultScope = useRef(false)
  const parsedQuery = useMemo(() => buildVisitListArgs(effectiveSearchParams), [effectiveSearchParams])
  const { data, error, isFetching, isLoading } = useListVisitsQuery(parsedQuery.args!, {
    skip: parsedQuery.args === null || parsedQuery.error !== null,
    refetchOnMountOrArgChange: true,
  })
  const orderByOptions = useMemo(() => getDatasetOrderFields(form.datasetType), [form.datasetType])
  const queryApiBaseUrl = useMemo(() => (
    /^https?:\/\//.test(env.baseUrl) ? env.baseUrl : `${window.location.origin}${env.baseUrl}`
  ), [])

  useEffect(() => {
    const normalizedQuery = normalizeQueryInput(currentQuery)
    setQueryInput(normalizedQuery)
    setForm((current) => mergeFormWithSearchParams(current, new URLSearchParams(normalizedQuery)))
  }, [currentQuery])

  useEffect(() => {
    if (currentQuery || appliedDefaultScope.current) {
      return
    }
    const scope = findDefaultScope(butlerScopes)
    if (!scope || hasQueryBuilderSelection(form)) {
      return
    }
    const nextForm = buildFormFromScope(scope)
    setForm(nextForm)
    setQueryInput(buildQueryInput(nextForm))
    appliedDefaultScope.current = true
  }, [butlerScopes, currentQuery, form])

  useEffect(() => {
    if (!form.repositoryName) {
      setOptions(EMPTY_OPTIONS)
      setOptionsError(null)
      setLoadingOptions(false)
      return
    }
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
    const defaultScope = findDefaultScope(butlerScopes, repositoryName)
    const datasetType = defaultScope?.dataset_type ?? ""
    const collection = defaultScope?.collection ?? ""
    const orderBy = getDatasetOrderFields(datasetType)[0] ?? "day_obs"
    applyForm({
      ...form,
      repositoryName,
      collection,
      datasetType,
      orderBy,
      where: "",
    })
  }, [applyForm, butlerScopes, form])

  const updateCollection = useCallback((collection: string) => {
    applyForm({
      ...form,
      collection,
      datasetType: "",
      orderBy: "day_obs",
      where: "",
    })
  }, [applyForm, form])

  const updateDatasetType = useCallback((datasetType: string) => {
    const nextOrderBy = getDatasetOrderFields(datasetType)[0] ?? "day_obs"
    applyForm({
      ...form,
      datasetType,
      orderBy: nextOrderBy,
      where: "",
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

  const handleCopyPython = useCallback(async () => {
    await copyTextToClipboard(buildQueryPythonSnippet(queryInput, queryApiBaseUrl))
  }, [queryApiBaseUrl, queryInput])

  return (
    <div style={pageStyle}>
      <div style={sectionStyle}>
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Data Query</h1>
        <p style={hintStyle}>
          Build a query string for arbitrary `repository` / `collection` / `dataset_type`, or edit the query string directly. Type in the comboboxes to narrow large option lists.
        </p>
        <form onSubmit={handleSubmit} style={formStyle}>
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
              <input
                list="query-page-collections"
                spellCheck={false}
                type="text"
                value={form.collection}
                onChange={(event) => updateCollection(event.target.value)}
                placeholder="Type to filter collections"
              />
              <datalist id="query-page-collections">
                {options.collections.map((option) => <option key={option} value={option} />)}
              </datalist>
            </label>
            <label style={fieldStyle}>
              <span>Dataset Type</span>
              <input
                list="query-page-dataset-types"
                spellCheck={false}
                type="text"
                value={form.datasetType}
                onChange={(event) => updateDatasetType(event.target.value)}
                placeholder="Type to filter dataset types"
              />
              <datalist id="query-page-dataset-types">
                {options.dataset_types.map((option) => <option key={option} value={option} />)}
              </datalist>
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
            <button type="button" onClick={() => void handleCopyPython()}>Copy Python</button>
            {loadingOptions && <span>Loading query options...</span>}
          </div>
        </form>
      </div>

      {optionsError && <p role="alert">{optionsError}</p>}
      {parsedQuery.error && <p role="alert">{parsedQuery.error}</p>}
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
                    <VisitRow entry={entry} key={entry.id} />
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

function hasQueryBuilderSelection(form: QueryFormState): boolean {
  return Boolean(form.repositoryName || form.collection || form.datasetType)
}

function scopeIdFromConfig(scope: ButlerScopeConfig): string {
  return scope.id ?? buildScopeId({
    repositoryName: scope.repository_name ?? "",
    collection: scope.collection ?? "",
    datasetType: scope.dataset_type ?? "",
  })
}

function findDefaultScope(
  scopes: ButlerScopeConfig[],
  repositoryName?: string,
): ButlerScopeConfig | undefined {
  if (repositoryName) {
    return scopes.find((scope) => scope.repository_name === repositoryName)
  }
  return scopes[0]
}

function buildFormFromScope(scope: ButlerScopeConfig): QueryFormState {
  const queryInput = buildDefaultQueryInput(scopeIdFromConfig(scope), Number(DEFAULT_LIMIT))
  return mergeFormWithSearchParams(createEmptyForm(), new URLSearchParams(queryInput))
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
  const hasParams = Array.from(searchParams.keys()).length > 0
  return {
    repositoryName: searchParams.get("repository_name") ?? (hasParams ? "" : form.repositoryName),
    collection: searchParams.get("collection") ?? (hasParams ? "" : form.collection),
    datasetType: searchParams.get("dataset_type") ?? (hasParams ? "" : form.datasetType),
    orderBy: searchParams.get("order_by") ?? (hasParams ? "day_obs" : form.orderBy),
    reverse: searchParams.has("reverse") ? searchParams.get("reverse") === "true" : (hasParams ? false : form.reverse),
    limit: searchParams.get("limit") ?? (hasParams ? DEFAULT_LIMIT : form.limit),
    where: searchParams.get("where") ?? (hasParams ? "" : form.where),
  }
}

function normalizeFormState(form: QueryFormState, options: QueryBuilderOptions): QueryFormState {
  const repositoryName = options.repositories.includes(form.repositoryName)
    ? form.repositoryName
    : (options.repositories[0] ?? "")
  const orderByFields = getDatasetOrderFields(form.datasetType)
  const orderBy = orderByFields.includes(form.orderBy) ? form.orderBy : (orderByFields[0] ?? "day_obs")
  return {
    ...form,
    repositoryName,
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

function VisitRow({ entry }: { entry: VisitEntry }) {
  return (
    <tr>
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

const formStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
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
  display: "flex",
  flexDirection: "column",
  gap: "4px",
  width: "100%",
  minWidth: 0,
  flex: "0 0 auto",
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
