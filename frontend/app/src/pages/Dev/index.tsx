import React from 'react'
import { useGetQuicklooksStatusQuery } from "../../store/api/base"
import { JobStatus, Progress as ProgressType, useCreateQuicklookMutation, useGetAllQuicklookJobsQuery } from "../../store/api/openapi"
import styles from './styles.module.scss'
import classNames from 'classnames'
import { Progress } from '../../components/Progress'

export function Dev() {
  const jobs = useGetAllQuicklookJobsQuery()
  const [createQuicklook] = useCreateQuicklookMutation()

  const handleCreateQuicklook = async () => {
    await createQuicklook({ createQuicklookRequest: { visit: 'raw:broccoli' } })
  }

  const { data: statusList } = useGetQuicklooksStatusQuery()

  return (
    <div className={styles.container}>
      <h1>Dev</h1>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
        <button onClick={handleCreateQuicklook}>Create Quicklook</button>
      </div>
      {statusList && Object.entries(statusList).map(([key, status]) => (
        <JobStatusVisualizer key={key} status={status} />
      ))}
    </div>
  )
}

function JobStatusVisualizer({ status }: { status: JobStatus }) {
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

function GenerateSingleFitsTilesVisualizer({ tiles }: { tiles: Record<string, ProgressType> }) {
  const tileData: Array<{ key: string; pos: TilePosition; ratio: number }> = []

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
                          (t) =>
                            t.pos.raftX === raftX &&
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
                                style={{ height: `${ratio * 100}%` }}
                              />
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

/*
statusを可視化してください。
以下の情報や型情報を参照してください。

Raftは`R{y}{x}`の名前がついていてx: 0~4, y: 0~4の範囲で配置されている。
左下が`R00`、右下が`R04`、左上が`R40`、右上が`R44`である。

Raftの中にSensorが3x3並んでいる。
Sensorには`S{y}{x}`の名前がついていてx: 0~2, y: 0~2の範囲で配置されている。
左下が`S00`、右下が`S02`、左上が`S20`、右上が`S22`である。
稀に`/S[GW][0-9]/`の形式の特殊なものがある。

SensorとRaftの名前を`R{Ry}{Rx}_S{Sy}{Sx}`のように組み合わせることでRaftとSensor両方の位置が決まる。
このようにして特定される対象をここでは「タイル」と呼ぶことにする。
この形式がJobStatus["generate_single_fits_tiles"]のキーとなる。
値はProgressという型で型情報を参照のこと。１つの[0, 1]の進捗を表す数値に対応づけることができる。
`R[0-2]{2}_S[GW][0-1]`の形式については以下のように読み替える。
R00_
  SW0: S22
  SG0: S12
  SG1: S21
R40
  SW0: S02
  SG0: S01
  SG1: S12
R04
  SW0: S20
  SG0: S21
  SG1: S10
R44
  SW0: S00
  SG0: S10
  SG1: S01

JobStatus["generate_single_fits_tiles"]の可視化ではタイルを2次元的に配置する。
それぞれのタイルに対応する数値を縦方向のプログレスバーで示す。
それぞれのタイルは正方形に描画する。

JobStatus["merge_tiles"], JobStatus["transfer_tiles"]の型はgenerate_single_fits_tilesと同じだが、2次元的な意味はない。
それぞれ単なる値がProgressの辞書でありキーはワーカーノードの名前である。
これはそれぞれの値をプログレスバーとして描画する。

描画コンポーネントの作成にあたってはgenerate_single_fits_tiles, merge_tiles, transfer_tilesに対して別々のコンポーネントを作ると良いだろう。

 */
