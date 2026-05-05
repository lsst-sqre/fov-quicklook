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
