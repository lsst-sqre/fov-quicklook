import styles from './styles.module.scss'
import { Progress } from "../components/Progress"
import { QuicklookStatus } from "../store/api/openapi"
import { LoadingSpinner } from '../components/Loading'

type ProgressItem = {
  count: number
  total: number
}

type PhaseName = "generate_progress" | "merge_progress" | "transfer_progress"
type PhaseProgressType<P extends PhaseName> = NonNullable<QuicklookStatus[P]>[string]

function createPhaseComponent<P1 extends PhaseName>(
  pName: P1,
  enumProgress: (p: PhaseProgressType<P1>) => ProgressItem[]
) {
  return function PhaseProgress({ s }: { s: QuicklookStatus | null }) {
    if (!s) {
      return <LoadingSpinner />
    }
    if (!s[pName]) {
      return null
    }
    return (
      <>
        {Object.keys(s[pName]).length === 0 ? (
          <LoadingSpinner />
        ) : (
          <table className={styles.progressTable}>
            <tbody>
              {Object.entries(s[pName]).map(([nodeName, ps]) => (
                <tr key={nodeName}>
                  <th>{nodeName}</th>
                  <td>
                    <NodeProgress
                      nodeName={nodeName}
                      ps={enumProgress(ps)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table >
        )}
      </>
    )
  }
}

function NodeProgress({
  nodeName, ps,
}: {
  nodeName: string
  ps: ProgressItem[]
}) {
  return (
    <>
      {ps.map((p, index) => (
        <Progress key={index} count={p.count} total={p.total} />
      ))}
    </>
  )
}

export const GenerateProgress = createPhaseComponent("generate_progress", p => [p.download, p.preprocess, p.maketile])
export const MergeProgress = createPhaseComponent("merge_progress", p => [p.merge])
export const TransferProgress = createPhaseComponent("transfer_progress", p => [p.transfer])
