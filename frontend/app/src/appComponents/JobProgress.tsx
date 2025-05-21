import { LoadingSpinner } from '../components/Loading'
import { Progress } from "../components/Progress"
import { QuicklookStatus } from "../store/api/openapi"
import styles from './styles.module.scss'

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
  return function PhaseProgress({ s, compact = false }: { s: QuicklookStatus | null, compact?: boolean }) {
    if (!s || !s[pName] || Object.keys(s[pName]).length === 0) {
      return compact ? null : <LoadingSpinner />
    }
    return (
      <table className={styles.progressTable}>
        <tbody>
          {Object.entries(s[pName]).map(([nodeName, ps]) => (
            <ProgressRow
              key={nodeName}
              nodeName={nodeName}
              progress={ps}
              enumProgress={enumProgress}
            />
          ))}
        </tbody>
      </table >
    )
  }
}


function ProgressRow<P extends PhaseName>({
  nodeName,
  progress,
  enumProgress,
}: {
  nodeName: string
  progress: PhaseProgressType<P>
  enumProgress: (p: PhaseProgressType<P>) => ProgressItem[]
}) {
  // const { data: podStatus } = useGetPodStatusQuery()
  // const podName = useMemo(() => {
  //   const nodeIp = nodeName.split(':')[0]
  //   const pod = podStatus?.generators.find(p => p.ip_addr === nodeIp)
  //   return pod?.hostname ?? nodeName
  // }, [nodeName, podStatus])
  const podName = nodeName

  return (
    <tr key={nodeName}>
      <th>{podName}</th>
      <td>
        <NodeProgress
          ps={enumProgress(progress)} />
      </td>
    </tr>
  )
}


function NodeProgress({
  ps,
}: {
  ps: ProgressItem[]
}) {
  return (
    <div className={styles.progressGroup}>
      {ps.map((p, index) => (
        <Progress key={index} count={p.count} total={p.total} />
      ))}
    </div>
  )
}

export const GenerateProgress = createPhaseComponent("generate_progress", p => [p.download, p.preprocess, p.maketile])
export const MergeProgress = createPhaseComponent("merge_progress", p => [p.merge])
export const TransferProgress = createPhaseComponent("transfer_progress", p => [p.transfer])
