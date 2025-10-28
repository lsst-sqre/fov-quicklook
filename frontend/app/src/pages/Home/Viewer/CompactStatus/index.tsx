import { useEffect, useRef, useState } from 'react'
import { ContainerStatus } from '../../../../store/api/openapi'
import { useGetSystemStatus_WS_Query } from '../../../../store/api/base'
import { Progress } from '../../../../components/Progress'
import { useAppSelector } from '../../../../store/hooks'
import styles from './styles.module.scss'

export function CompactStatus() {
  const { data: status } = useGetSystemStatus_WS_Query()
  const showCompactStatus = useAppSelector(state => state.home.showCompactStatus)

  if (!status || !showCompactStatus) {
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
  const [memTooltip, setMemTooltip] = useState<string | null>(null)
  const [cpuTooltip, setCpuTooltip] = useState<string | null>(null)

  const calculateUnrecoverableMemory = (): number => {
    if (!container.memory_stats) return 0
    const { anon, shmem, kernel, slab } = container.memory_stats
    return anon + shmem + kernel + slab
  }

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  const prevRef = useRef<{ cpu: number; uptime: number } | null>(null)
  const [cpuPercent, setCpuPercent] = useState<number | null>(null)

  useEffect(() => {
    const prev = prevRef.current
    if (prev && container.uptime > prev.uptime) {
      const deltaCpu = container.cpu_current - prev.cpu
      const deltaTime = container.uptime - prev.uptime
      let percent: number | null = null
      if (deltaTime > 0 && container.cpu_max > 0) {
        const cpuMaxPerSecond = container.cpu_max
        percent = (deltaCpu / (deltaTime * 1_000_000)) / (cpuMaxPerSecond / 100_000) * 100
      }
      setCpuPercent(percent)
    }
    prevRef.current = { cpu: container.cpu_current, uptime: container.uptime }
  }, [container.cpu_current, container.uptime, container.cpu_max])

  const showMemoryUsageInCompactStatus = useAppSelector(state => state.home.showMemoryUsageInCompactStatus)
  const unrecoverableMemory = calculateUnrecoverableMemory()
  const memoryRatio = showMemoryUsageInCompactStatus 
    ? container.memory_current / container.memory_max 
    : unrecoverableMemory / container.memory_max
  const displayMemory = showMemoryUsageInCompactStatus 
    ? container.memory_current 
    : unrecoverableMemory

  return (
    <div className={styles.containerItem}>
      <div className={styles.containerName}>{name}</div>
      <div className={styles.metrics}>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>Mem:</span>
          <div 
            className={styles.progressWrapper}
            onMouseEnter={() => setMemTooltip(formatBytes(displayMemory))}
            onMouseLeave={() => setMemTooltip(null)}
            title={formatBytes(displayMemory)}
          >
            <Progress 
              count={displayMemory} 
              total={container.memory_max} 
              width="100px" 
              rounded={true} 
            />
            {memTooltip && <div className={styles.tooltip}>{memTooltip}</div>}
          </div>
          <span className={styles.metricValue}>{(memoryRatio * 100).toFixed(0)}%</span>
        </div>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>CPU:</span>
          <div 
            className={styles.progressWrapper}
            onMouseEnter={() => setCpuTooltip(cpuPercent !== null ? `${cpuPercent.toFixed(1)}%` : '---')}
            onMouseLeave={() => setCpuTooltip(null)}
            title={cpuPercent !== null ? `${cpuPercent.toFixed(1)}%` : '---'}
          >
            <Progress 
              count={cpuPercent ?? 0} 
              total={100} 
              width="100px" 
              rounded={true} 
            />
            {cpuTooltip && <div className={styles.tooltip}>{cpuTooltip}</div>}
          </div>
          <span className={styles.metricValue}>
            {cpuPercent !== null ? `${cpuPercent.toFixed(0)}%` : '---'}
          </span>
        </div>
      </div>
    </div>
  )
}
