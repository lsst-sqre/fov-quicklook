import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { useListVisitsQuery, VisitEntry } from "../../store/api/openapi"
import { useAppSelector } from "../../store/hooks"
import { buildDefaultQueryInput, buildVisitListArgs, normalizeQueryInput } from "./queryParams"

export function QueryPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentQuery = searchParams.toString()
  const currentDataSource = useAppSelector((state) => state.home.dataSource)
  const defaultQuery = useMemo(() => buildDefaultQueryInput(currentDataSource), [currentDataSource])
  const effectiveQuery = currentQuery || defaultQuery
  const effectiveSearchParams = useMemo(() => new URLSearchParams(effectiveQuery), [effectiveQuery])
  const [queryInput, setQueryInput] = useState(effectiveQuery)

  useEffect(() => {
    setQueryInput(effectiveQuery)
  }, [effectiveQuery])

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

  return (
    <div style={pageStyle}>
      <div style={sectionStyle}>
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Data Query</h1>
        <p style={hintStyle}>
          Enter the query string after <code>/query?</code>. The query runs when the field loses focus or when you press Enter.
          Supported parameters include <code>exposure</code>, <code>day_obs</code>, <code>limit</code>, <code>offset</code>, <code>order</code>,
          <code>ra_deg</code>, <code>dec_deg</code>, and <code>radius_deg</code>.
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
                    <th>Visit / Exposure</th>
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
                      key={entry.id}
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

function VisitRow({ entry }: { entry: VisitEntry }) {
  return (
    <tr>
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
