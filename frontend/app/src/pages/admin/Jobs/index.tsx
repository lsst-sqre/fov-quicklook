import { GenerateProgress, MergeProgress, TransferProgress } from "../../../appComponents/JobProgress"
import { QuicklookJobPhase, QuicklookStatus } from "../../../store/api/openapi"
import { useJobs } from "./useJobs"


export function Jobs() {
  const jobs = useJobs()

  return (
    <div>
      {jobs?.map((job) => (
        <Job key={job.id} status={job} />
      ))}
    </div>
  )
}


function Job({ status }: { status: QuicklookStatus }) {
  return (
    <div>
      <h2>{status.id}</h2>
      <p>Phase: {phaseName(status.phase)}</p>
      <GenerateProgress compact s={status} />
      <MergeProgress compact s={status} />
      <TransferProgress compact s={status} />
    </div>
  )
}


function phaseName(phase: QuicklookJobPhase) {
  switch (phase) {
    case 0: return 'QUEUED'
    case 1: return 'GENERATE_RUNNING'
    case 2: return 'GENERATE_DONE'
    case 3: return 'MERGE_RUNNING'
    case 4: return 'MERGE_DONE'
    case 5: return 'TRANSFER_RUNNING'
    case 6: return 'TRANSFER_DONE'
    case 7: return 'READY'
    case -1: return 'FAILED'
    default: return 'UNKNOWN'
  }
}
