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
  const [unrecoverableMemTooltip, setUnrecoverableMemTooltip] = useState<string | null>(null)
  const [recoverableMemTooltip, setRecoverableMemTooltip] = useState<string | null>(null)
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
  const [cpuPercentOfMax, setCpuPercentOfMax] = useState<number | null>(null)
  const [cpuPercentPerCore, setCpuPercentPerCore] = useState<number | null>(null)

  useEffect(() => {
    const prev = prevRef.current
    if (prev && container.uptime > prev.uptime) {
      const deltaCpu = container.cpu_current - prev.cpu
      const deltaTime = container.uptime - prev.uptime
      if (deltaTime > 0 && container.cpu_max > 0) {
        const cpuMaxPerSecond = container.cpu_max
        const percentOfMax = (deltaCpu / (deltaTime * 1_000_000)) / (cpuMaxPerSecond / 100_000) * 100
        const percentPerCore = (deltaCpu / (deltaTime * 1_000_000)) * 100
        setCpuPercentOfMax(percentOfMax)
        setCpuPercentPerCore(percentPerCore)
      }
    }
    prevRef.current = { cpu: container.cpu_current, uptime: container.uptime }
  }, [container.cpu_current, container.uptime, container.cpu_max])

  const showMemoryUsageInCompactStatus = useAppSelector(state => state.home.showMemoryUsageInCompactStatus)
  const unrecoverableMemory = calculateUnrecoverableMemory()

  return (
    <div className={styles.containerItem}>
      <div className={styles.containerName}>{name}</div>
      <div className={styles.metrics}>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>Mem:</span>
          <div 
            className={styles.progressWrapper}
            onMouseEnter={() => setUnrecoverableMemTooltip(formatBytes(unrecoverableMemory))}
            onMouseLeave={() => setUnrecoverableMemTooltip(null)}
            title={`Unrecoverable Memory: ${formatBytes(unrecoverableMemory)}`}
          >
            <Progress 
              count={unrecoverableMemory} 
              total={container.memory_max} 
              width="100px" 
              rounded={true} 
            />
            {unrecoverableMemTooltip && <div className={styles.tooltip}>{unrecoverableMemTooltip}</div>}
          </div>
          <span className={styles.metricValue}>{(unrecoverableMemory / container.memory_max * 100).toFixed(0)}%</span>
        </div>
        {showMemoryUsageInCompactStatus && (
          <div className={styles.metricRow}>
            <span className={styles.metricLabel}>Mem:</span>
            <div 
              className={styles.progressWrapper}
              onMouseEnter={() => setRecoverableMemTooltip(formatBytes(container.memory_current))}
              onMouseLeave={() => setRecoverableMemTooltip(null)}
              title={`Recoverable Memory: ${formatBytes(container.memory_current)}`}
            >
              <Progress 
                count={container.memory_current} 
                total={container.memory_max} 
                width="100px" 
                rounded={true} 
              />
              {recoverableMemTooltip && <div className={styles.tooltip}>{recoverableMemTooltip}</div>}
            </div>
            <span className={styles.metricValue}>{(container.memory_current / container.memory_max * 100).toFixed(0)}%</span>
          </div>
        )}
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>CPU:</span>
          <div 
            className={styles.progressWrapper}
            onMouseEnter={() => setCpuTooltip(cpuPercentOfMax !== null ? `CPU usage: ${cpuPercentOfMax.toFixed(1)}% of max` : '---')}
            onMouseLeave={() => setCpuTooltip(null)}
            title={cpuPercentOfMax !== null ? `CPU usage: ${cpuPercentOfMax.toFixed(1)}% of max` : '---'}
          >
            <Progress 
              count={cpuPercentOfMax ?? 0} 
              total={100} 
              width="100px" 
              rounded={true} 
            />
            {cpuTooltip && <div className={styles.tooltip}>{cpuTooltip}</div>}
          </div>
          <span className={styles.metricValue}>
            {cpuPercentPerCore !== null ? `${cpuPercentPerCore.toFixed(0)}%` : '---'}
          </span>
        </div>
      </div>
    </div>
  )
}
