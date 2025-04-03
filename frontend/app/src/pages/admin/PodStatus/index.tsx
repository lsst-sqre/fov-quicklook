import { DiskInfo, PodStatus, useGetPodStatusQuery } from "../../../store/api/openapi"
import { Progress } from "../../../components/Progress"
import styles from './styles.module.scss'


export function PodsStatus() {
  const { data: podStatus, isLoading, error } = useGetPodStatusQuery()

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error loading pod status</div>
  if (!podStatus) return null

  return (
    <div className={styles.podStatus}>
      <PodStatusView status={podStatus.frontend} title="Frontend" />
      <PodStatusView status={podStatus.coordinator} title="Coordinator" />
      {podStatus.generators.map((generator, i) => (
        <PodStatusView key={i} status={generator} title={`Generator ${i + 1}`} />
      ))}
    </div>
  )
}

function formatBytes(bytes: number) {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex++
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`
}

function DiskInfoView({ disk }: { disk: DiskInfo }) {
  const usagePercent = (disk.used / disk.total) * 100
  return (
    <div>
      <div>
        {disk.mount_point} ({formatBytes(disk.used)} / {formatBytes(disk.total)}, {usagePercent.toFixed(0)}%)
        <Progress count={disk.used} total={disk.total} width="200px" />
      </div>
    </div>
  )
}

function PodStatusView({ status, title }: { status: PodStatus, title: string }) {
  return (
    <div className={styles.podStatusView}>
      <span>{title}</span>
      <div>Hostname: {status.hostname}</div>
      <div>
        Memory: {formatBytes(status.memory_used)} / {formatBytes(status.memory_total)}
        <Progress count={status.memory_used} total={status.memory_total} width="200px" />
      </div>
      <details open>
        <summary>Disks ({status.disks.length})</summary>
        <div>
          {status.disks.map((disk, i) => (
            <DiskInfoView key={i} disk={disk} />
          ))}
        </div>
      </details>
    </div>
  )
}
