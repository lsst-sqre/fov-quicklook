import { sprintf } from '~/utils/sprintf'


export function enable(gl: WebGL2RenderingContext, fs: number[], callback: () => void) {
  for (let f of fs) {
    gl.enable(f)
  }
  callback()
  for (let f of fs) {
    gl.disable(f)
  }
}


export function withLineNumber(body: string) {
  return body.split("\n")
    .map((line, n) => sprintf('%4d | %s', n + 1, line))
    .join("\n")
}


export function nonNull<T1>(v: T1) {
  if (!v) {
    throw new Error(`non-null check error: ${v}`)
  }
  return v
}