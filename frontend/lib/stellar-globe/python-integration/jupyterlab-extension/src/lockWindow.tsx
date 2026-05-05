import { Globe } from '@stellar-globe/stellar-globe'
import { widgetEnvs } from './StellarGlobeWidget'
import { EventEmitter } from './eventemitter'

export const lockFrame = Object.assign((windowIds: string[]) => {
  const key = idsKey(windowIds)
  unlocks.set(key, lock(windowIds))

  // 2番目以降のwindowのカメラを1番目のカメラに合わせる
  const baseEnv = widgetEnvs.get(windowIds[0])
  if (baseEnv) {
    const bg = baseEnv.appHandle.globe()
    for (const wid of windowIds.slice(1)) {
      const otherEnv = widgetEnvs.get(wid)
      if (otherEnv) {
        const og = otherEnv.appHandle.globe()
        Object.assign(og.camera, extractCameraParams(bg.camera))
        og.requestRefresh()
      }
    }
  }
}, {
  unlock: (windowIds: string[]) => {
    const key = idsKey(windowIds)
    if (unlocks.has(key)) {
      unlocks.get(key)!()
    }
    unlocks.delete(key)
  }
})


const lock = (windowIds: string[]) => {
  const cameraMove = EventEmitter<Globe['camera']>({ once: false })
  const unlock = EventEmitter({ once: true })

  for (const id of windowIds) {
    if (widgetEnvs.has(id)) {
      const unlock1 = EventEmitter({ once: true })
      const { appHandle, onWidgetClose } = widgetEnvs.get(id)!
      const globe = appHandle.globe()

      // storeChange.on(state => {
      //   state.tractTileLayers.colorParams
      // })

      unlock1.on(globe.on('camera-move', e => {
        cameraMove.emit(e.camera)
      }))
      unlock1.on(cameraMove.on(camera => {
        Object.assign(globe.camera, extractCameraParams(camera))
        globe.requestRefresh()
      }))
      onWidgetClose(() => {
        unlock1.emit()
      })
      unlock.on(() => {
        unlock1.emit()
      })
    }
  }

  return () => {
    unlock.emit()
  }
}


const unlocks = new Map<string, () => void>()


function idsKey(ids: string[]) {
  return ids.slice().sort().join(',')
}

function extractCameraParams(camera: Globe['camera']) {
  const { theta, phi, za, zd, zp, fovy, roll } = camera
  return { theta, phi, za, zd, zp, fovy, roll }
}
