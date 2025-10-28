import { useEffect, useRef, useState } from 'react'
import { useRouteGetStatusQuery, ContainerStatus } from '../../../../store/api/openapi'
import { Progress } from '../../../../components/Progress'
import styles from './styles.module.scss'

export function CompactStatus() {
  const { data: status } = useRouteGetStatusQuery(undefined, { 
    refetchOnMountOrArgChange: true, 
    pollingInterval: 1000 
  })

  if (!status) {
    return null
  }

  const allContainers: Array<{ name: string; container: ContainerStatus }> = [
    { name: 'coordinator', container: status.coordinator },
    { name: 'frontend', container: status.frontend },
    ...Object.entries(status.generators).map(([name, container]) => ({
      name: name.substring(0, 6),
      container
    }))
  ]

  return (
    <div className={styles.compactStatus}>
      <div className={styles.containerList}>
        {allContainers.map(({ name, container }) => (
          <CompactContainerStatus key={name} name={name} container={container} />
        ))}
      </div>
    </div>
  )
}

interface CompactContainerStatusProps {
  name: string
  container: ContainerStatus
}

function CompactContainerStatus({ name, container }: CompactContainerStatusProps) {
  const calculateUnrecoverableMemory = (): number => {
    if (!container.memory_stats) return 0
    const { anon, shmem, kernel, slab } = container.memory_stats
    return anon + shmem + kernel + slab
  }

  const prevRef = useRef<{ cpu: number; uptime: number } | null>(null)
  const [cpuPercent, setCpuPercent] = useState<number | null>(null)

  useEffect(() => {
    const prev = prevRef.current
    if (prev && container.uptime > prev.uptime) {
      const deltaCpu = container.cpu_current - prev.cpu
      const deltaTime = container.uptime - prev.uptime
      let percent: number | null = null
      if (deltaTime > 0) {
        percent = (deltaCpu / (deltaTime * 1_000_000)) * 100
      }
      setCpuPercent(percent)
    }
    prevRef.current = { cpu: container.cpu_current, uptime: container.uptime }
  }, [container.cpu_current, container.uptime])

  const unrecoverableMemory = calculateUnrecoverableMemory()
  const memoryRatio = unrecoverableMemory / container.memory_max

  return (
    <div className={styles.containerItem}>
      <div className={styles.containerName}>{name}</div>
      <div className={styles.metrics}>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>Mem:</span>
          <Progress 
            count={unrecoverableMemory} 
            total={container.memory_max} 
            width="100px" 
            rounded={true} 
          />
          <span className={styles.metricValue}>{(memoryRatio * 100).toFixed(0)}%</span>
        </div>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>CPU:</span>
          <Progress 
            count={cpuPercent ?? 0} 
            total={100} 
            width="100px" 
            rounded={true} 
          />
          <span className={styles.metricValue}>
            {cpuPercent !== null ? `${cpuPercent.toFixed(0)}%` : '---'}
          </span>
        </div>
      </div>
    </div>
  )
}
