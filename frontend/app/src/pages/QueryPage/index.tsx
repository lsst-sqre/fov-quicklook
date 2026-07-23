import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSelector } from "react-redux"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Combobox } from "../../components/Combobox"
import { env } from "../../env"
import { buildScopeId } from "../../quicklookId"
import { AppState } from "../../store"
import { ButlerScopeConfig, useListVisitsQuery } from "../../store/api/openapi"
import { copyTextToClipboard } from "../../utils/copyTextToClipboard"
import { makeSessionStorageAccessor } from "../../utils/localStorage"
import { buildDefaultQueryInput, buildQueryPythonSnippet, buildVisitListArgs, normalizeQueryInput } from "./queryParams"
import { VisitResultsTable } from "./VisitResultsTable"

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
  collections_truncated: boolean
  dataset_types: string[]
  dataset_types_truncated: boolean
  where_examples: QueryWhereExample[]
}

const EMPTY_OPTIONS: QueryBuilderOptions = {
  repositories: [],
  collections: [],
  collections_truncated: false,
  dataset_types: [],
  dataset_types_truncated: false,
  where_examples: [],
}
const querySessionStorage = makeSessionStorageAccessor<string>("queryPageSearch", "")

export function QueryPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const butlerScopes = useSelector((state: AppState) => state.copyTemplate.butlerScopes)
  const queryBuilderInputMode = useSelector((state: AppState) => state.copyTemplate.queryBuilderInputMode)
  const currentQuery = searchParams.toString()
  const restoredQuery = useMemo(
    () => currentQuery ? "" : normalizeQueryInput(querySessionStorage.get()),
    [currentQuery],
  )
  const effectiveQuery = currentQuery || restoredQuery
  const effectiveSearchParams = useMemo(() => new URLSearchParams(effectiveQuery), [effectiveQuery])
  const [queryInput, setQueryInput] = useState(() => normalizeQueryInput(effectiveQuery))
  const [form, setForm] = useState<QueryFormState>(createEmptyForm)
  const [options, setOptions] = useState<QueryBuilderOptions>(EMPTY_OPTIONS)
  const [optionsError, setOptionsError] = useState<string | null>(null)
  const [headerError, setHeaderError] = useState<string | null>(null)
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [openingHeaderVisitId, setOpeningHeaderVisitId] = useState<string | null>(null)
  const appliedDefaultScope = useRef(false)
  const parsedQuery = useMemo(() => buildVisitListArgs(effectiveSearchParams), [effectiveSearchParams])
  const { data, error, isFetching, isLoading } = useListVisitsQuery(parsedQuery.args!, {
    skip: parsedQuery.args === null || parsedQuery.error !== null,
    refetchOnMountOrArgChange: true,
  })
  const orderByOptions = useMemo(() => getDatasetOrderFields(form.datasetType), [form.datasetType])
  const repositoryOptions = useMemo(() => getConfiguredRepositories(butlerScopes), [butlerScopes])
  const configuredCollections = useMemo(
    () => getConfiguredCollections(butlerScopes, form.repositoryName),
    [butlerScopes, form.repositoryName],
  )
  const configuredDatasetTypes = useMemo(
    () => getConfiguredDatasetTypes(butlerScopes, form.repositoryName, form.collection),
    [butlerScopes, form.collection, form.repositoryName],
  )
  const collectionOptions = queryBuilderInputMode === "select" ? configuredCollections : options.collections
  const datasetTypeOptions = queryBuilderInputMode === "select" ? configuredDatasetTypes : options.dataset_types
  const showCollectionColumn = !parsedQuery.args?.collection

  useEffect(() => {
    const normalizedQuery = normalizeQueryInput(effectiveQuery)
    setQueryInput(normalizedQuery)
    setForm((current) => mergeFormWithSearchParams(current, new URLSearchParams(normalizedQuery)))
  }, [effectiveQuery])

  useEffect(() => {
    if (!effectiveQuery) {
      return
    }
    querySessionStorage.set(effectiveQuery)
  }, [effectiveQuery])

  useEffect(() => {
    if (effectiveQuery || appliedDefaultScope.current) {
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
  }, [butlerScopes, effectiveQuery, form])

  useEffect(() => {
    if (queryBuilderInputMode !== "combobox") {
      setOptions(EMPTY_OPTIONS)
      setOptionsError(null)
      setLoadingOptions(false)
      return
    }
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
        setForm((current) => normalizeComboboxFormState(current, repositoryOptions))
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
  }, [form.collection, form.datasetType, form.repositoryName, queryBuilderInputMode, repositoryOptions])

  const applyForm = useCallback((nextForm: QueryFormState) => {
    setForm(nextForm)
    setQueryInput(buildQueryInput(nextForm))
  }, [])

  useEffect(() => {
    if (queryBuilderInputMode !== "select") {
      return
    }
    if (effectiveQuery && !hasQueryBuilderSelection(form)) {
      return
    }
    const nextForm = normalizeSelectFormState(form, butlerScopes)
    if (!areFormsEqual(form, nextForm)) {
      applyForm(nextForm)
    }
  }, [applyForm, butlerScopes, effectiveQuery, form, queryBuilderInputMode])

  const updateRepository = useCallback((repositoryName: string) => {
    const defaultScope = findDefaultScope(butlerScopes, repositoryName)
    const collection = defaultScope?.collection ?? (queryBuilderInputMode === "select"
      ? (getConfiguredCollections(butlerScopes, repositoryName)[0] ?? "")
      : "")
    const datasetType = defaultScope?.dataset_type ?? (queryBuilderInputMode === "select"
      ? (getConfiguredDatasetTypes(butlerScopes, repositoryName, collection)[0] ?? "")
      : "")
    const orderBy = getDatasetOrderFields(datasetType)[0] ?? "day_obs"
    applyForm({
      ...form,
      repositoryName,
      collection,
      datasetType,
      orderBy,
      where: "",
    })
  }, [applyForm, butlerScopes, form, queryBuilderInputMode])

  const updateCollection = useCallback((collection: string) => {
    const datasetType = queryBuilderInputMode === "select"
      ? (getConfiguredDatasetTypes(butlerScopes, form.repositoryName, collection)[0] ?? "")
      : form.datasetType
    applyForm({
      ...form,
      collection,
      datasetType,
      orderBy: getDatasetOrderFields(datasetType)[0] ?? "day_obs",
      where: "",
    })
  }, [applyForm, butlerScopes, form, queryBuilderInputMode])

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

  const commitQuery = useCallback(() => {
    const normalized = normalizeQueryInput(queryInput)
    if (normalized) {
      querySessionStorage.set(normalized)
    } else {
      querySessionStorage.remove()
    }
    navigate(normalized ? `/query?${normalized}` : "/query")
  }, [navigate, queryInput])

  const handleSubmit = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    commitQuery()
  }, [commitQuery])

  const handleCopyPython = useCallback(async () => {
    await copyTextToClipboard(buildQueryPythonSnippet(queryInput))
  }, [queryInput])

  const handleOpenHeader = useCallback(async (visitId: string) => {
    setHeaderError(null)
    setOpeningHeaderVisitId(visitId)
    const popup = window.open("", "_blank")
    try {
      const ccds = await fetchVisitCcds(visitId)
      const firstCcd = ccds[0]
      if (!firstCcd) {
        throw new Error("No CCDs found for this visit.")
      }
      const headerUrl = `${env.baseUrl}/header/${encodeURIComponent(visitId)}/${encodeURIComponent(firstCcd)}`
      if (popup) {
        popup.location.href = headerUrl
      } else if (window.open(headerUrl, "_blank") === null) {
        throw new Error("Failed to open the header.")
      }
    } catch (openError) {
      popup?.close()
      setHeaderError(openError instanceof Error ? openError.message : "Failed to open the header.")
    } finally {
      setOpeningHeaderVisitId((current) => current === visitId ? null : current)
    }
  }, [])

  return (
    <div style={pageStyle}>
      <div style={sectionStyle}>
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Data Query</h1>
        <form onSubmit={handleSubmit} style={formStyle}>
          <div style={helperFieldsStyle}>
            <label style={fieldStyle}>
              <span>Repository</span>
              <select value={form.repositoryName} onChange={(event) => updateRepository(event.target.value)}>
                <option value="">Select repository</option>
                {repositoryOptions.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label style={fieldStyle}>
              <span>Collection</span>
              {queryBuilderInputMode === "combobox" ? (
                <Combobox
                  value={form.collection}
                  options={collectionOptions}
                  truncated={options.collections_truncated}
                  onChange={updateCollection}
                  placeholder="Type to filter collections"
                />
              ) : (
                <select value={form.collection} onChange={(event) => updateCollection(event.target.value)}>
                  <option value="">Select collection</option>
                  {collectionOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              )}
            </label>
            <label style={fieldStyle}>
              <span>Dataset Type</span>
              {queryBuilderInputMode === "combobox" ? (
                <Combobox
                  value={form.datasetType}
                  options={datasetTypeOptions}
                  truncated={options.dataset_types_truncated}
                  onChange={updateDatasetType}
                  placeholder="Type to filter dataset types"
                />
              ) : (
                <select value={form.datasetType} onChange={(event) => updateDatasetType(event.target.value)}>
                  <option value="">Select dataset type</option>
                  {datasetTypeOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              )}
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
            {queryBuilderInputMode === "combobox" && loadingOptions && <span>Loading query options...</span>}
          </div>
        </form>
      </div>

      {queryBuilderInputMode === "combobox" && optionsError && <p role="alert">{optionsError}</p>}
      {parsedQuery.error && <p role="alert">{parsedQuery.error}</p>}
      {parsedQuery.args !== null && (
        <div style={resultsSectionStyle}>
          <div style={summaryStyle}>
            <span>Results: {data?.length ?? 0}</span>
          </div>
          {headerError && <p role="alert">{headerError}</p>}
          {error && <p role="alert">{formatQueryError(error)}</p>}
          {!isLoading && !isFetching && !error && data?.length === 0 && <p>No visits matched the query.</p>}
          {(data || isLoading || isFetching) && (
            <div style={resultsTableAreaStyle}>
              <VisitResultsTable
                data={data ?? []}
                isFetching={isFetching}
                isLoading={isLoading}
                onOpenHeader={handleOpenHeader}
                openingHeaderVisitId={openingHeaderVisitId}
                showCollectionColumn={showCollectionColumn}
              />
            </div>
          )}
        </div>
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
  const hasScopedSelection = Boolean(form.repositoryName || form.collection || form.datasetType)
  if (form.repositoryName) params.set("repository_name", form.repositoryName)
  if (form.collection) params.set("collection", form.collection)
  if (form.datasetType) params.set("dataset_type", form.datasetType)
  if (form.orderBy) params.set("order_by", form.orderBy)
  if (form.reverse) params.set("reverse", "true")
  if (form.limit) params.set("limit", form.limit)
  if (hasScopedSelection || form.where) params.set("where", form.where)
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

function normalizeComboboxFormState(
  form: QueryFormState,
  repositoryOptions: string[],
): QueryFormState {
  const repositoryName = repositoryOptions.includes(form.repositoryName)
    ? form.repositoryName
    : (repositoryOptions[0] ?? "")
  const orderByFields = getDatasetOrderFields(form.datasetType)
  const orderBy = orderByFields.includes(form.orderBy) ? form.orderBy : (orderByFields[0] ?? "day_obs")
  return {
    ...form,
    repositoryName,
    orderBy,
    limit: form.limit || DEFAULT_LIMIT,
  }
}

function normalizeSelectFormState(form: QueryFormState, scopes: ButlerScopeConfig[]): QueryFormState {
  const repositoryOptions = getConfiguredRepositories(scopes)
  const repositoryName = repositoryOptions.includes(form.repositoryName)
    ? form.repositoryName
    : (repositoryOptions[0] ?? "")
  const collections = getConfiguredCollections(scopes, repositoryName)
  const collection = collections.includes(form.collection) ? form.collection : (collections[0] ?? "")
  const datasetTypes = getConfiguredDatasetTypes(scopes, repositoryName, collection)
  const datasetType = datasetTypes.includes(form.datasetType) ? form.datasetType : (datasetTypes[0] ?? "")
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

function areFormsEqual(left: QueryFormState, right: QueryFormState): boolean {
  return (
    left.repositoryName === right.repositoryName
    && left.collection === right.collection
    && left.datasetType === right.datasetType
    && left.orderBy === right.orderBy
    && left.reverse === right.reverse
    && left.limit === right.limit
    && left.where === right.where
  )
}

function getConfiguredRepositories(scopes: ButlerScopeConfig[]): string[] {
  return uniqueValues(scopes.map((scope) => scope.repository_name ?? ""))
}

function getConfiguredCollections(scopes: ButlerScopeConfig[], repositoryName: string): string[] {
  return uniqueValues(
    scopes
      .filter((scope) => (scope.repository_name ?? "") === repositoryName)
      .map((scope) => scope.collection),
  )
}

function getConfiguredDatasetTypes(
  scopes: ButlerScopeConfig[],
  repositoryName: string,
  collection: string,
): string[] {
  return uniqueValues(
    scopes
      .filter((scope) => (scope.repository_name ?? "") === repositoryName)
      .filter((scope) => !collection || scope.collection === collection)
      .map((scope) => scope.dataset_type),
  )
}

function uniqueValues(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)))
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
  const collectionsTruncated = (payload as { collections_truncated?: unknown }).collections_truncated
  const datasetTypesTruncated = (payload as { dataset_types_truncated?: unknown }).dataset_types_truncated
  if (collectionsTruncated !== undefined && typeof collectionsTruncated !== "boolean") {
    throw new Error("Failed to load query options.")
  }
  if (datasetTypesTruncated !== undefined && typeof datasetTypesTruncated !== "boolean") {
    throw new Error("Failed to load query options.")
  }
  return {
    ...(payload as Omit<QueryBuilderOptions, "collections_truncated" | "dataset_types_truncated">),
    collections_truncated: collectionsTruncated === true,
    dataset_types_truncated: datasetTypesTruncated === true,
  }
}

async function fetchVisitCcds(visitId: string): Promise<string[]> {
  const response = await fetch(`${env.baseUrl}/api/visits/${encodeURIComponent(visitId)}/ccds`)
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail ?? "Failed to load CCDs.")
  }
  const payload: unknown = await response.json()
  if (!Array.isArray(payload) || payload.some((ccd) => typeof ccd !== "string")) {
    throw new Error("Failed to load CCDs.")
  }
  return payload
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
  minHeight: 0,
  overflow: "hidden",
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

const resultsSectionStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
  minHeight: 0,
  flex: "1 1 auto",
} as const

const resultsTableAreaStyle = {
  minHeight: 0,
  flex: "1 1 auto",
} as const
