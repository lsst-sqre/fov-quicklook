import { setWorkerErrorHandler } from '~/utils/setWorkerErrorHandler'
import EchoWorker from './echo-worker?worker&inline'


export function testEchoWorker(message: unknown) {
  return new Promise(resolve => {
    const worker = setWorkerErrorHandler(new EchoWorker())
    worker.postMessage(message)
    worker.addEventListener('message', e => {
      worker.terminate()
      resolve(e.data)
    })
  })
}
