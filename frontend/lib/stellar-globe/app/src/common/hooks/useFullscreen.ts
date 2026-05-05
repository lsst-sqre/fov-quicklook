import { RefObject, useCallback, useEffect, useState } from "react"


export function useIsFullscreen() {
  const [isFullscreen, setIsFullscreen] = useState(!!document.fullscreenElement)

  useEffect(() => {
    const cb = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', cb)
    return () => {
      document.removeEventListener('fullscreenchange', cb)
    }
  }, [])

  return {
    isFullscreen,
  }
}


export function useFullscreen(ref: RefObject<HTMLDivElement>) {
  const { isFullscreen } = useIsFullscreen()

  const enterFullscreen = useCallback(() => {
    ref.current?.requestFullscreen()
  }, [ref])

  const exitFullscreen = useCallback(() => {
    document.exitFullscreen()
  }, [])

  const toggleFullscreen = useCallback(() => {
    (isFullscreen ? exitFullscreen : enterFullscreen)()
  }, [enterFullscreen, exitFullscreen, isFullscreen])

  return {
    enterFullscreen,
    exitFullscreen,
    toggleFullscreen,
    isFullscreen,
  }
}
