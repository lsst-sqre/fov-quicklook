import { echo } from "./worker-body"

// @ts-ignore
self.addEventListener('message', e => {
  setTimeout(() => {
    self.postMessage(echo(e.data))
  }, 1000)
})
