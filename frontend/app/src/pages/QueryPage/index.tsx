import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { env } from "../../env"
import { useListVisitsQuery, VisitEntry } from "../../store/api/openapi"
import { buildByUuidVisitName, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

export function QueryPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentQuery = searchParams.toString()
  const [queryInput, setQueryInput] = useState(currentQuery)
  const [openError, setOpenError] = useState<string | null>(null)
  const [openingVisit, setOpeningVisit] = useState<string | null>(null)

  useEffect(() => {
    setQueryInput(currentQuery)
  }, [currentQuery])

  const parsedQuery = useMemo(() => buildVisitListArgs(searchParams), [searchParams])
  const { data, error, isFetching, isLoading } = useListVisitsQuery(parsedQuery.args!, {
    skip: parsedQuery.args === null || parsedQuery.error !== null,
    refetchOnMountOrArgChange: true,
  })

  const commitQuery = useCallback(() => {
    const normalized = normalizeQueryInput(queryInput)
    if (normalized === currentQuery) {
      return
    }
    navigate(normalized ? `/query?${normalized}` : "/query")
  }, [currentQuery, navigate, queryInput])

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
          Enter the query string after <code>/query?</code>. The query runs when the field loses focus or when you press Enter.
        </p>
        <form onSubmit={handleSubmit} style={formStyle}>
          <input
            aria-label="Query string"
            onBlur={commitQuery}
            onChange={(event) => setQueryInput(event.target.value)}
            spellCheck={false}
            style={inputStyle}
            type="text"
            value={queryInput}
          />
          <button type="submit">Search</button>
        </form>
      </div>

      {parsedQuery.error && <p role="alert">{parsedQuery.error}</p>}
      {openError && <p role="alert">{openError}</p>}
      {parsedQuery.args === null && parsedQuery.error === null && (
        <p>Set <code>data_type</code> and <code>repository_name</code> to run a query.</p>
      )}
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

function VisitRow(
  { entry, isOpening, onOpenByUuid }:
  { entry: VisitEntry, isOpening: boolean, onOpenByUuid: (visitName: string) => Promise<void> }
) {
  return (
    <tr>
      <td>
        <button aria-label={`Open ${entry.id} by UUID`} disabled={isOpening} onClick={() => void onOpenByUuid(entry.id)}>
          {isOpening ? "Opening..." : "Open by UUID"}
        </button>
      </td>
      <td>
        <Link to={`/visits/${encodeURIComponent(entry.id)}`}>{entry.id}</Link>
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

const formStyle = {
  display: "flex",
  gap: "8px",
  alignItems: "center",
} as const

const inputStyle = {
  flexGrow: 1,
  fontFamily: "ui-monospace, SFMono-Regular, SFMono, Menlo, Consolas, Liberation Mono, monospace",
  padding: "8px 10px",
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
