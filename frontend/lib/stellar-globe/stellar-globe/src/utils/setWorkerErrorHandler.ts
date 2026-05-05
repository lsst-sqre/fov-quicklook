export function setWorkerErrorHandler(w: Worker) {
  w.addEventListener('error', e => {
    console.error(e)
    w.terminate()
  })
  return w
}
