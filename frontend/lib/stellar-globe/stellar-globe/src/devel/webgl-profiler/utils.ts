import { WebGLProfiler } from "./figma-webgl-profiler"


const instances = new WeakMap<WebGL2RenderingContext, WebGLProfiler>()


export function enableWebglProfiler(gl: WebGL2RenderingContext) {
  if (!webglProfileSupported()) {
    throw new Error(`WebGL Profiling is not supported.`)
  }

  const profiler = (() => {
    if (!instances.has(gl)) {
      instances.set(gl, new WebGLProfiler(gl))
    }
    return instances.get(gl)!
  })()

  const start = () => {
    profiler.start()
  }

  const stop = async () => {
    await profiler.stopAndDownload()
  }

  const disable = () => {
    instances.delete(gl)
  }

  return {
    start,
    stop,
    disable,
  }
}


export function wegblProfile(gl: WebGL2RenderingContext, name: string, cb: () => void) {
  const profiler = instances.get(gl)
  if (profiler && profiler.isProfilerRunning()) {
    profiler.pushContext(name)
    try {
      cb()
    }
    finally {
      profiler.popContext(name)
    }
  }
  else {
    cb()
  }
}


export function webglProfileSupported() {
  return false
  // figma-webgl-profilerはWebGL2では動かない
  // see https://ics.media/web3d-maniacs/webgl2_ext_disjoint_timer_query_webgl2/
  // return isChromeVersionAtLeast70()
}


// function isChromeVersionAtLeast70(): boolean {
//   const userAgent: string = navigator.userAgent
//   const chromeRegex: RegExp = /Chrome\/(\d+)/
//   const match: RegExpExecArray | null = chromeRegex.exec(userAgent)

//   if (match && match.length >= 2) {
//     const version: number = parseInt(match[1], 10)
//     return version >= 70
//   }

//   return false
// }
