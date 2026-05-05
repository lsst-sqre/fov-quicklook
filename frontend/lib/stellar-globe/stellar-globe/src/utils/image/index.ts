import { ImageLike } from '~/lib/gl-wrapper'

import { setWorkerErrorHandler } from '../setWorkerErrorHandler'
import type { DecodeRequest, DecodeResponse } from './background_image_decoder'
import DecodeWorker from './background_image_decoder?worker&inline'


type LoadImageOptions = {
  failover?: ImageLike
  flipY?: boolean
}


export async function loadImage(
  url: string,
  {
    failover,
    flipY = true,
  }: LoadImageOptions = {},
): Promise<ImageLike> {
  try {
    return await backgroundDecoder.load(url, { flipY })
  }
  catch (e) {
    if (failover) {
      return failover
    }
    throw e
  }
}


class BackgroundImageDecoder {
  private deferreds = new Map<number, Deferred<ImageBitmap, unknown>>()
  private seq = 0

  private _worker?: Worker

  private get worker() {
    if (!this._worker) {
      // constructorで↓をしないのはjsdomTestができなくなるから
      const worker = setWorkerErrorHandler(new DecodeWorker())
      worker.addEventListener('message', this.workerOnMessage)
      this._worker = worker
    }
    return this._worker
  }

  load(url: string, { flipY = true }: { flipY?: boolean } = {}) {
    const id = ++this.seq
    const d = deferred<ImageBitmap, unknown>()
    this.deferreds.set(id, d)
    const msg: DecodeRequest = { id, url: (new URL(url, location.href)).href, flipY }
    this.worker.postMessage(msg)
    return d.promise
  }

  private workerOnMessage = async (e: MessageEvent) => {
    const msg: DecodeResponse = e.data
    const { id } = msg
    const { resolve, reject } = this.deferreds.get(id)!
    this.deferreds.delete(id)
    if (msg.type === 'error') {
      reject(msg.message)
    }
    if (msg.type === 'ok') {
      resolve(msg.imageBitmap)
    }
  }
}


const backgroundDecoder = new BackgroundImageDecoder()


type Deferred<T, U> = {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (error: U) => void
}


function deferred<T, U>() {
  let resolve: (value: T) => void
  let reject: (value: U) => void
  const promise = new Promise<T>((_resolve, _reject) => {
    resolve = _resolve
    reject = _reject
  })
  return {
    promise,
    // @ts-ignore
    resolve,
    // @ts-ignore
    reject,
  }
}
