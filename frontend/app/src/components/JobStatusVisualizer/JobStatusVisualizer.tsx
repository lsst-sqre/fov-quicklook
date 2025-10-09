import classNames from 'classnames'
import { Progress } from '../Progress'
import { JobStatus, Progress as ProgressType } from '../../store/api/openapi'
import styles from './styles.module.scss'

export function JobStatusVisualizer({ status }: { status: JobStatus} ) {
  return (
    <div className={styles.jobStatus}>
      <h2>Job: {status.job.visit} - Stage: {status.stage}</h2>
      {status.generate_single_fits_tiles && (
        <GenerateSingleFitsTilesVisualizer tiles={status.generate_single_fits_tiles} />
      )}
      {status.merge_tiles && (
        <WorkerNodesVisualizer title="Merge Tiles" workers={status.merge_tiles} />
      )}
      {status.transfer_tiles && (
        <WorkerNodesVisualizer title="Transfer Tiles" workers={status.transfer_tiles} />
      )}
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

export function GenerateSingleFitsTilesVisualizer({ tiles }: { tiles: Record<string, ProgressType>} ) {
  const tileData: Array<{ key: string; pos: TilePosition; ratio: number} > = []

  for (const [key, progress] of Object.entries(tiles)) {
    const pos = parseTileKey(key)
    if (pos) {
      tileData.push({ key, pos, ratio: progressToRatio(progress) })
    }
  }

  return (
    <div className={styles.generateSingleFitsTiles}>
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
                          <div key={sensorX} className={classNames(styles.sensor, isSpecial && styles.hidden)} title={tile?.key}>
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
function WorkerNodesVisualizer({ title, workers }: { title: string; workers: Record<string, ProgressType>} ) {
  return (
    <div className={styles.workerNodes}>
      <h3>{title}</h3>
      <div className={styles.workerList}>
        {Object.entries(workers).map(([workerName, progress]) => (
          <div key={workerName} className={styles.workerItem}>
            <div className={styles.workerName}>{workerName}</div>
            <Progress count={progress.count ?? 0} total={progress.total} width="100%" />
            <div className={styles.workerProgress}>
              {progress.count ?? 0} / {progress.total}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
