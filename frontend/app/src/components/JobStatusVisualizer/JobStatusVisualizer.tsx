import classNames from 'classnames'
import { Link } from 'react-router-dom'
import { Progress } from '../Progress'
import { JobStatus, Progress as ProgressType } from '../../store/api/openapi'
import styles from './styles.module.scss'

export function JobStatusVisualizer({ status, isHighlighted = false }: { status: JobStatus; isHighlighted?: boolean }) {
  return (
    <div className={classNames(styles.jobStatus, isHighlighted && styles.highlighted)}>
      <h2>
        Job: <Link to={`/visits/${encodeURIComponent(status.job.visit)}`}>{status.job.visit}</Link>
      </h2>
      <div className={styles.container}>
        {status.generate_single_fits_tiles && (
          <div className={styles.section}>
            <GenerateSingleFitsTilesVisualizer tiles={status.generate_single_fits_tiles} height="20px" gap={false} />
          </div>
        )}
        {status.merge_tiles && (
          <div className={styles.section}>
            <WorkerNodesVisualizer title="Merge Tiles" workers={status.merge_tiles} />
          </div>
        )}
        {status.transfer_tiles && (
          <div className={styles.section}>
            <WorkerNodesVisualizer title="Transfer Tiles" workers={status.transfer_tiles} />
          </div>
        )}
      </div>
    </div>
  )
}

function progressToRatio(progress: ProgressType): number {
  if (progress.total === 0) return 0
  return (progress.count ?? 0) / progress.total
}

type TilePosition = {
  raftX: number
  raftY: number
  sensorX: number
  sensorY: number
}

const SPECIAL_SENSOR_MAP: Record<string, string> = {
  R00_SW0: 'R00_S22',
  R00_SG0: 'R00_S12',
  R00_SG1: 'R00_S21',
  R40_SW0: 'R40_S02',
  R40_SG0: 'R40_S01',
  R40_SG1: 'R40_S12',
  R04_SW0: 'R04_S20',
  R04_SG0: 'R04_S21',
  R04_SG1: 'R04_S10',
  R44_SW0: 'R44_S00',
  R44_SG0: 'R44_S10',
  R44_SG1: 'R44_S01',
}
const SPECIAL_SENSOR_POSITIONS = new Set<string>(Object.values(SPECIAL_SENSOR_MAP))
function parseTileKey(key: string): TilePosition | null {
  key = SPECIAL_SENSOR_MAP[key] ?? key
  const match = key.match(/^R(\d)(\d)_S(\d)(\d)$/)
  if (!match) return null
  const [, raftY, raftX, sensorYRaw, sensorXRaw] = match
  return {
    raftX: parseInt(raftX, 10),
    raftY: parseInt(raftY, 10),
    sensorX: parseInt(sensorXRaw, 10),
    sensorY: parseInt(sensorYRaw, 10),
  }
}

type GenerateSingleFitsTilesVisualizerProps = {
  tiles: Record<string, ProgressType>
  height?: string
  gap?: boolean
}

export function GenerateSingleFitsTilesVisualizer({ tiles, height = '100px', gap = false }: GenerateSingleFitsTilesVisualizerProps) {
  const tileData: Array<{ key: string; pos: TilePosition; ratio: number }> = []

  for (const [key, progress] of Object.entries(tiles)) {
    const pos = parseTileKey(key)
    if (pos) {
      tileData.push({ key, pos, ratio: progressToRatio(progress) })
    }
  }

  return (
    <div className={styles.generateSingleFitsTiles} style={{ '--tile-height': height, '--tile-gap': gap ? '2px' : '0px' } as React.CSSProperties} data-gap={gap}>
      <h3>Generate Single FITS Tiles</h3>
      <div className={styles.tileGrid}>
        {Array.from({ length: 5 }, (_, raftY) => (
          <div key={raftY} className={styles.raftRow}>
            {Array.from({ length: 5 }, (_, raftX) => (
              <div key={raftX} className={styles.raft}>
                <div className={styles.sensorGrid}>
                  {Array.from({ length: 3 }, (_, sensorY) => (
                    <div key={sensorY} className={styles.sensorRow}>
                      {Array.from({ length: 3 }, (_, sensorX) => {
                        const tile = tileData.find(
                          (t) => t.pos.raftX === raftX &&
                            t.pos.raftY === raftY &&
                            t.pos.sensorX === sensorX &&
                            t.pos.sensorY === sensorY
                        )
                        const ratio = tile?.ratio ?? 0
                        const raftKey = `R${raftY}${raftX}`
                        const sensorKey = `S${sensorY}${sensorX}`
                        const isSpecial = ['R00', 'R40', 'R04', 'R44'].includes(raftKey) && !SPECIAL_SENSOR_POSITIONS.has(`${raftKey}_${sensorKey}`)
                        const isCompleted = tile && tile.ratio === 1
                        return (
                          <div key={sensorX} className={classNames(styles.sensor, isSpecial && styles.hidden, !gap && styles.gapless)} title={tile?.key}>
                            <div className={styles.progressBar}>
                              <div
                                className={classNames(styles.progressFill, isCompleted && styles.completed)}
                                style={{ height: `${ratio * 100}%` }} />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
function WorkerNodesVisualizer({ title, workers }: { title: string; workers: Record<string, ProgressType> }) {
  return (
    <div className={styles.workerNodes}>
      <h3>{title}</h3>
      <div className={styles.workerStack}>
        {Object.entries(workers).map(([workerName, progress]) => (
          <div key={workerName} className={styles.workerBar} title={workerName}>
            <Progress count={progress.count ?? 0} total={progress.total} width="100%" />
          </div>
        ))}
      </div>
    </div>
  )
}
