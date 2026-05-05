import { SinglePointerEvent } from "./SinglePointerEvent"

const isClickDefaultOptions = {
  maxMove: 4, //pixel
  maxDuration: 200 //ms
}


export function isClick(
  e1: SinglePointerEvent,
  e2: SinglePointerEvent,
  options: Partial<typeof isClickDefaultOptions> = {},
) {
  const { maxDuration, maxMove } = { ...options, ...isClickDefaultOptions }
  return (
    Math.abs(e1.clientX - e2.clientX) < maxMove &&
    Math.abs(e1.clientY - e2.clientY) < maxMove &&
    (e2.timeStamp - e1.timeStamp) < maxDuration
  )
}


export function on<Target extends HTMLElement, K extends keyof HTMLElementEventMap>(
  target: Target,
  type: K,
  callback: (ev: HTMLElementEventMap[K]) => any,
  options?: AddEventListenerOptions
): () => void


export function on<Target extends EventTarget>(
  target: Target,
  type: string,
  callback: EventListener,
  options?: AddEventListenerOptions,
): () => void {
  target.addEventListener(type, callback, options)
  return () => {
    target.removeEventListener(type, callback)
  }
}
