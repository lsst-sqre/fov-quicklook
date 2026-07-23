import { memo } from "react"
import { Link } from "react-router-dom"
import { LoadingSpinner } from "../../components/Loading"
import { parseVisitId, type VisitIdParts } from "../../quicklookId"
import { VisitEntry } from "../../store/api/openapi"

type VisitResultsTableProps = {
  data: VisitEntry[]
  isFetching: boolean
  isLoading: boolean
  onOpenHeader: (visitId: string) => Promise<void>
  openingHeaderVisitId: string | null
  showCollectionColumn: boolean
}

export const VisitResultsTable = memo(({
  data,
  isFetching,
  isLoading,
  onOpenHeader,
  openingHeaderVisitId,
  showCollectionColumn,
}: VisitResultsTableProps) => {
  return (
    <div style={tableContainerStyle}>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th>Visit</th>
            <th>Header</th>
            {showCollectionColumn && <th>Collection</th>}
            <th>Day Obs</th>
            <th>UTC</th>
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
              onOpenHeader={onOpenHeader}
              openingHeaderVisitId={openingHeaderVisitId}
              showCollectionColumn={showCollectionColumn}
            />
          ))}
        </tbody>
      </table>
      {(isLoading || isFetching) && (
        <div style={loadingOverlayStyle}>
          <LoadingSpinner size="100px" />
        </div>
      )}
    </div>
  )
})

function VisitRow(
  { entry, onOpenHeader, openingHeaderVisitId, showCollectionColumn }: {
    entry: VisitEntry
    onOpenHeader: (visitId: string) => Promise<void>
    openingHeaderVisitId: string | null
    showCollectionColumn: boolean
  },
) {
  const collection = getVisitCollection(entry.id)
  return (
    <tr>
      <td>
        <Link to={`/visits/${encodeURIComponent(entry.id)}`}>{formatVisitTail(entry.id)}</Link>
      </td>
      <td>
        <button
          disabled={openingHeaderVisitId === entry.id}
          onClick={() => void onOpenHeader(entry.id)}
          title="Show the Header of the first CCD"
          type="button"
        >
          Header
        </button>
      </td>
      {showCollectionColumn && <td>{collection}</td>}
      <td>{entry.day_obs}</td>
      <td>{entry.utc_start ?? ""}</td>
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

function formatVisitTail(visitId: string): string {
  try {
    const parsed = parseVisitId(visitId)
    if (parsed.isByUuid) {
      return parsed.dimensions.uuid
    }
    return formatVisitDimensions(parsed)
  } catch {
    return visitId
  }
}

function formatVisitDimensions(parsed: VisitIdParts): string {
  return Object.entries(parsed.dimensions)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join(",")
}

function getVisitCollection(visitId: string): string {
  try {
    return parseVisitId(visitId).collection
  } catch {
    return ""
  }
}

const tableContainerStyle = {
  position: "relative",
  overflow: "auto",
  border: "1px solid rgba(255, 255, 255, 0.12)",
  borderRadius: "8px",
} as const

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  minWidth: "960px",
} as const

const loadingOverlayStyle = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "rgba(0, 0, 0, 0.35)",
  pointerEvents: "none",
} as const
