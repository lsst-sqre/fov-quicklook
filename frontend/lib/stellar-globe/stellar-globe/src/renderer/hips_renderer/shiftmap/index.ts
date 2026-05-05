import { EventManager } from '~/utils/EventManager'
import { setWorkerErrorHandler as withWorkerErrorHandler } from '~/utils/setWorkerErrorHandler'
import { encode_id, shiftmapId } from "../healpix"
import { Shiftmap, ShiftmapRequest, ShiftmapResponse } from './interface'
import ShiftmapWorker from './shiftmap-worker?worker&inline'
export { DELTA_MAP_N as size } from './interface'


export function fetch(order: number, index: number, then: (array: Uint8Array) => void) {
  const id = shiftmapId(order, index)
  if (workerManager.cache.has(id)) {
    then(workerManager.cache.get(id)!)
  } else {
    workerManager.enqueue(id).then(then)
  }
}


class ShitmapWorkerManager {
  cache = new Map<number, Uint8Array>()
  private worker?: Worker
  private resolve = new Map<number, Array<(array: Uint8Array) => void>>()
  private processing: number | undefined
  private queue: number[] = []

  enqueue(id: number): Promise<Uint8Array> {
    if (this.cache.has(id)) {
      return Promise.resolve(this.cache.get(id)!)
    }
    if (this.processing !== id && this.queue.indexOf(id) < 0) {
      this.queue.push(id)
      this.doNextJob()
    }
    return new Promise((resolve) => {
      if (!this.resolve.has(id)) {
        this.resolve.set(id, [])
      }
      this.resolve.get(id)!.push(resolve)
    })
  }

  private receiveShiftmap({ id, arraybuffer }: Shiftmap) {
    const array = new Uint8Array(arraybuffer)
    const i = this.queue.indexOf(id)
    if (i >= 0) { this.queue.splice(i, 1) }
    this.cache.set(id, array)
    if (this.resolve.has(id)) {
      for (const r of this.resolve.get(id)!) {
        r(array)
      }
      this.resolve.delete(id)
    }
  }

  private async doNextJob() {
    if (this.processing === undefined) {
      const id = this.queue.shift()
      if (id !== undefined) {
        const req: ShiftmapRequest = { id }
        await this.startWorker()
        this.processing = id
        this.worker!.postMessage(req)
      } else {
        this.requestQuitWorker()
      }
    }
  }

  private async startWorker() {
    if (!this.worker) {
      this.eventManager.emit('hips-shiftmap-worker-start', {})
      this.cancelQuit()
      this.worker = withWorkerErrorHandler(new ShiftmapWorker())
      this.worker.addEventListener('message', (e) => {
        const res: ShiftmapResponse = e.data
        for (const shiftmap of res) {
          this.receiveShiftmap(shiftmap)
        }
        this.processing = undefined
        this.doNextJob()
      })
    }
  }

  private quitTimer: ReturnType<typeof setTimeout> | undefined

  private cancelQuit() {
    if (this.quitTimer !== undefined) {
      clearTimeout(this.quitTimer)
      this.quitTimer = undefined
    }
  }

  private requestQuitWorker() {
    this.cancelQuit()
    this.quitTimer = setTimeout(() => {
      this.eventManager.emit('hips-shiftmap-worker-end', {})
      this.quitTimer = undefined
      this.worker!.terminate()
      this.worker = undefined
    }, 5000)
  }

  eventManager = EventManager<EventMap>()
}


const workerManager = new ShitmapWorkerManager()


export const on = workerManager.eventManager.on


type EventMap = {
  'hips-shiftmap-worker-start': {}
  'hips-shiftmap-worker-end': {}
}


// true for polar caps
export function needShiftMap(order: number, index: number) {
  const nside = 1 << order
  const nside2 = nside * nside
  const f = Math.floor(index / nside2)
  if (4 <= f && f < 8) {
    return false
  }
  const i = f >= 8 ? index % nside2 : nside2 - (index % nside2) - 1
  return [0, 1, 2, 3].indexOf(i) >= 0
}


export function preload(order: number) {
  if (order === 0) {
    workerManager.enqueue(encode_id(0, 0))
    workerManager.enqueue(encode_id(0, 8))
  } else {
    const n2 = 1 << (2 * order)
    for (let i = 0; i < 4; ++i) {
      workerManager.enqueue(shiftmapId(order, n2 - i - 1)) // north cap
      workerManager.enqueue(shiftmapId(order, 8 * n2 + i)) // south cap
    }
  }
}


export function uploadZeroShiftmap(gl: WebGL2RenderingContext) {
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, 1, 1, 0, gl.LUMINANCE, gl.UNSIGNED_BYTE, new Uint8Array([128]))
}
