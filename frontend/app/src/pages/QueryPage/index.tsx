import { CSSProperties, useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { LoadingSpinner } from "../../components/Loading"
import { env } from "../../env"
import { ButlerDatasetTypeDimensions, ButlerDatasetTypeInfo, ButlerQueryResult } from "../../store/api/openapi"
import {
  buildButlerDatasetTypesApiUrl,
  buildButlerDimensionsApiUrl,
  buildButlerQueryApiUrl,
  formatQueryCellValue,
} from "./queryApi"

const sectionStyle: CSSProperties = {
  padding: "16px 20px",
  border: "1px solid rgba(255, 255, 255, 0.15)",
  borderRadius: "12px",
  background: "rgba(255, 255, 255, 0.04)",
}

const tableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
}

const cellStyle: CSSProperties = {
  borderBottom: "1px solid rgba(255, 255, 255, 0.12)",
  padding: "8px 10px",
  textAlign: "left",
  verticalAlign: "top",
}

async function fetchJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) {
    throw new Error(await response.text() || `Request failed with status ${response.status}`)
  }
  return await response.json() as T
}


export function QueryPage() {
  const [searchParams] = useSearchParams()
  const [result, setResult] = useState<ButlerQueryResult | null>(null)
  const [resultError, setResultError] = useState<string | null>(null)
  const [datasetTypes, setDatasetTypes] = useState<ButlerDatasetTypeInfo[]>([])
  const [datasetTypesError, setDatasetTypesError] = useState<string | null>(null)
  const [dimensions, setDimensions] = useState<ButlerDatasetTypeDimensions | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const dataType = searchParams.get("data_type")
  const repositoryName = searchParams.get("repository_name")
  const queryEntries = useMemo(() => Array.from(searchParams.entries()), [searchParams])
  const searchString = searchParams.toString()

  useEffect(() => {
    const controller = new AbortController()

    fetchJson<ButlerDatasetTypeInfo[]>(
      buildButlerDatasetTypesApiUrl(env.baseUrl, repositoryName),
      controller.signal,
    )
      .then((next) => {
        setDatasetTypes(next)
        setDatasetTypesError(null)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        setDatasetTypes([])
        setDatasetTypesError(error instanceof Error ? error.message : "Failed to load supported dataset types.")
      })

    return () => controller.abort()
  }, [repositoryName])

  useEffect(() => {
    if (!dataType) {
      setIsLoading(false)
      setResult(null)
      setDimensions(null)
      setResultError(null)
      return
    }

    const controller = new AbortController()
    setIsLoading(true)

    fetchJson<ButlerQueryResult>(
      buildButlerQueryApiUrl(env.baseUrl, searchParams),
      controller.signal,
    )
      .then(async (next) => {
        setResult(next)
        setResultError(null)
        try {
          const nextDimensions = await fetchJson<ButlerDatasetTypeDimensions>(
            buildButlerDimensionsApiUrl(env.baseUrl, next.data_type, next.repository_name),
            controller.signal,
          )
          setDimensions(nextDimensions)
        } catch (error: unknown) {
          if (controller.signal.aborted) {
            return
          }
          setDimensions(null)
          setResultError(error instanceof Error ? error.message : "Failed to load dataset dimensions.")
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        setResult(null)
        setDimensions(null)
        setResultError(error instanceof Error ? error.message : "Failed to run Butler query.")
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      })

    return () => controller.abort()
  }, [dataType, searchParams, searchString])

  return (
    <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
      <section style={sectionStyle}>
        <h1 style={{ marginTop: 0 }}>Butler Query</h1>
        <p style={{ marginBottom: 0 }}>
          Drive this page from the URL only. Example:
          {" "}
          <code>/query?data_type=raw&amp;day_obs=20260503&amp;limit=10</code>
        </p>
      </section>

      <section style={sectionStyle}>
        <h2 style={{ marginTop: 0 }}>Current URL parameters</h2>
        {queryEntries.length === 0 ? (
          <p style={{ marginBottom: 0 }}>No parameters are set yet.</p>
        ) : (
          <table style={tableStyle}>
            <tbody>
              {queryEntries.map(([key, value], index) => (
                <tr key={`${key}-${value}-${index}`}>
                  <th style={{ ...cellStyle, width: "220px" }}>{key}</th>
                  <td style={cellStyle}><code>{value}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {!dataType && (
        <section style={sectionStyle}>
          <p style={{ margin: 0 }}>
            Add a <code>data_type</code> query parameter to execute a search.
          </p>
        </section>
      )}

      {isLoading && (
        <section style={{ ...sectionStyle, display: "flex", justifyContent: "center" }}>
          <LoadingSpinner size="48px" width="6px" />
        </section>
      )}

      {resultError && (
        <section style={{ ...sectionStyle, borderColor: "rgba(255, 120, 120, 0.5)" }}>
          <strong>Query error:</strong> {resultError}
        </section>
      )}

      {result && (
        <>
          <section style={sectionStyle}>
            <h2 style={{ marginTop: 0 }}>Query summary</h2>
            <table style={tableStyle}>
              <tbody>
                <SummaryRow label="Repository" value={result.repository_name} />
                <SummaryRow label="Data type" value={result.data_type} />
                <SummaryRow label="Data ID dimension" value={result.data_id_dimension} />
                <SummaryRow label="Limit" value={String(result.limit)} />
                <SummaryRow label="Offset" value={String(result.offset)} />
                <SummaryRow label="Returned rows" value={String(result.returned_count)} />
                <SummaryRow label="More rows available" value={result.has_more ? "Yes" : "No"} />
                <SummaryRow label="Order" value={result.order.join(", ")} />
                <SummaryRow
                  label="Collections"
                  value={result.applied_collections?.join(", ") ?? "Configured/default selection"}
                />
                <SummaryRow
                  label="Filters"
                  value={Object.entries(result.applied_filters).map(([key, value]) => `${key}=${value}`).join(", ") || "None"}
                />
              </tbody>
            </table>
          </section>

          {dimensions && (
            <section style={sectionStyle}>
              <h2 style={{ marginTop: 0 }}>Dataset dimensions</h2>
              <p><strong>Dimensions:</strong> {dimensions.dimensions.join(", ") || "None"}</p>
              <p style={{ marginBottom: 0 }}>
                <strong>Filter aliases:</strong>
                {" "}
                {Object.entries(dimensions.filter_aliases).map(([key, value]) => `${key} → ${value}`).join(", ") || "None"}
              </p>
            </section>
          )}

          <section style={sectionStyle}>
            <h2 style={{ marginTop: 0 }}>Results</h2>
            {result.rows.length === 0 ? (
              <p style={{ marginBottom: 0 }}>No records matched the current query.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={cellStyle}>Visit</th>
                      {result.columns.map((column) => (
                        <th key={column} style={cellStyle}>{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row) => (
                      <tr key={row.visit_name}>
                        <td style={cellStyle}>
                          <Link to={`/visits/${encodeURIComponent(row.visit_name)}`}>{row.visit_name}</Link>
                        </td>
                        {result.columns.map((column) => (
                          <td key={`${row.visit_name}-${column}`} style={cellStyle}>
                            <code>{formatQueryCellValue(row.record[column])}</code>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      <section style={sectionStyle}>
        <h2 style={{ marginTop: 0 }}>Supported dataset types</h2>
        {datasetTypesError ? (
          <p style={{ marginBottom: 0 }}><strong>Error:</strong> {datasetTypesError}</p>
        ) : datasetTypes.length === 0 ? (
          <p style={{ marginBottom: 0 }}>No Butler dataset types are configured.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={cellStyle}>Repository</th>
                  <th style={cellStyle}>Data type</th>
                  <th style={cellStyle}>Display name</th>
                  <th style={cellStyle}>Data ID dimension</th>
                  <th style={cellStyle}>Default order</th>
                  <th style={cellStyle}>Default collections</th>
                </tr>
              </thead>
              <tbody>
                {datasetTypes.map((item) => (
                  <tr key={`${item.repository_name}:${item.data_type}`}>
                    <td style={cellStyle}>{item.repository_name}</td>
                    <td style={cellStyle}><code>{item.data_type}</code></td>
                    <td style={cellStyle}>{item.display_name}</td>
                    <td style={cellStyle}><code>{item.data_id_dimension}</code></td>
                    <td style={cellStyle}><code>{item.default_order.join(", ")}</code></td>
                    <td style={cellStyle}><code>{item.default_collections.join(", ")}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}


function SummaryRow({ label, value }: { label: string, value: string }) {
  return (
    <tr>
      <th style={{ ...cellStyle, width: "220px" }}>{label}</th>
      <td style={cellStyle}>{value || "-"}</td>
    </tr>
  )
}
