import { useRouteGetStatusQuery, ContainerStatus, useKillCoordinatorMutation } from "../../../store/api/openapi"
import { useGetSystemStatus_WS_Query } from "../../../store/api/base"
import { Progress } from "../../../components/Progress"
import styles from './styles.module.scss'
import { useEffect, useRef, useState } from "react"

export function Status() {
  const { data: status, isLoading, error } = useRouteGetStatusQuery(undefined, { refetchOnMountOrArgChange: true })
  const { data: wsStatus } = useGetSystemStatus_WS_Query()
  const [killCoordinator, { isLoading: isKilling }] = useKillCoordinatorMutation()

  const displayStatus = wsStatus || status

  const handleRestartSystem = async () => {
    if (window.confirm('Restart the system?\nThis will restart all components (coordinator, generators, frontend).')) {
      try {
        await killCoordinator().unwrap()
      } catch (e) {
        console.error('Failed to restart system:', e)
      }
    }
  }

  if (isLoading) {
    return <div className={styles.statusPage}>Loading...</div>
  }

  if (error || !displayStatus) {
    return <div className={styles.statusPage}>Failed to load status</div>
  }

  return (
    <div className={styles.statusPage}>
      <h1>System Status</h1>

      <section className={styles.section}>
        <h2>Actions</h2>
        <div className={styles.actionsCard}>
          <button
            className={styles.restartButton}
            onClick={handleRestartSystem}
            disabled={isKilling}
          >
            {isKilling ? 'Restarting...' : 'Restart System'}
          </button>
          <p className={styles.restartDescription}>
            Restarts all components (coordinator, generators, frontend).
          </p>
        </div>
      </section>
      
      <section className={styles.section}>
        <h2>Frontend</h2>
        <div className={styles.statusCard}>
          <ContainerStatusCard container={displayStatus.frontend} />
        </div>
      </section>

      <section className={styles.section}>
        <h2>Coordinator</h2>
        <div className={styles.statusCard}>
          <ContainerStatusCard container={displayStatus.coordinator} />
        </div>
      </section>

      <section className={styles.section}>
        <h2>Generators</h2>
        <div className={styles.generatorsList}>
          {Object.entries(displayStatus.generators).map(([name, container]) => (
            <div key={name} className={styles.generatorCard}>
              <h3>{name}</h3>
              <ContainerStatusCard container={container} />
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

interface ContainerStatusCardProps {
  container: ContainerStatus
}

function ContainerStatusCard({ container }: ContainerStatusCardProps) {
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
  }

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days}d ${hours}h ${minutes}m`
  }

  const calculateUnrecoverableMemory = (): number => {
    if (!container.memory_stats) return 0
    const { anon, shmem, kernel, slab } = container.memory_stats
    return anon + shmem + kernel + slab
  }

  const prevRef = useRef<{cpu: number, uptime: number} | null>(null)
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

  return (
    <table className={styles.statusTable}>
      <tbody>
        <tr>
          <th>Container Name</th>
          <td>{container.container_name}</td>
        </tr>
        <tr>
          <th>Memory Usage</th>
          <td>
            {formatBytes(container.memory_current)} / {formatBytes(container.memory_max)}
            <Progress count={container.memory_current} total={container.memory_max} width="100%" rounded={true} />
          </td>
        </tr>
        <tr>
          <th>Unrecoverable Memory</th>
          <td>
            {formatBytes(calculateUnrecoverableMemory())} / {formatBytes(container.memory_max)}
            <Progress count={calculateUnrecoverableMemory()} total={container.memory_max} width="100%" rounded={true} />
          </td>
        </tr>
        <tr>
          <th>CPU Usage</th>
          <td>
            {cpuPercent !== null ? `${(cpuPercent * 1).toFixed(2)}%` : '---'}
          </td>
        </tr>
        <tr>
          <th>Uptime</th>
          <td>{formatUptime(container.uptime)}</td>
        </tr>
      </tbody>
    </table>
  )
}