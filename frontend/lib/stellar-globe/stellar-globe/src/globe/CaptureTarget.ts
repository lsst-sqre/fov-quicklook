import { mat2 } from 'gl-matrix'
import { Texture } from '../lib/gl-wrapper'
import { nonNull } from '~/lib/gl-wrapper/utils'


export class CaptureTarget {
  readonly gl: WebGL2RenderingContext
  readonly frameBuffer: WebGLFramebuffer
  readonly rawOutput: Texture
  private canvasWidth!: number
  private targetWidth!: number
  private canvasHeight!: number
  private targetHeight!: number

  constructor(gl: WebGL2RenderingContext) {
    this.gl = gl
    this.frameBuffer = nonNull(gl.createFramebuffer())
    this.rawOutput = new Texture(gl)
    this.refreshDimensions()
  }

  release() {
    this.rawOutput.release()
    this.gl.deleteFramebuffer(this.frameBuffer)
  }

  private refreshDimensions() {
    const gl = this.gl
    const canvasWidth = gl.drawingBufferWidth
    const canvasHeight = gl.drawingBufferHeight
    const targetWidth = getPowerOfTwo(canvasWidth)
    const targetHeight = getPowerOfTwo(canvasHeight)
    this.canvasWidth = canvasWidth
    this.targetWidth = targetWidth
    this.canvasHeight = canvasHeight
    this.targetHeight = targetHeight
  }

  capture(callback: () => void) {
    const gl = this.gl
    const texture = this.rawOutput
    this.refreshDimensions()
    const {
      canvasWidth, targetWidth, canvasHeight, targetHeight,
    } = this

    gl.bindTexture(gl.TEXTURE_2D, texture.name)
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      targetWidth,
      targetHeight,
      0,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      null
    )
    gl.bindTexture(gl.TEXTURE_2D, null)
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.frameBuffer)
    gl.framebufferTexture2D(
      gl.FRAMEBUFFER,
      gl.COLOR_ATTACHMENT0,
      gl.TEXTURE_2D,
      texture.name,
      0
    )
    gl.viewport(0, 0, gl.canvas.width, gl.canvas.height)
    try {
      callback()
    } finally {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null)
      gl.activeTexture(gl.TEXTURE0)
      gl.viewport(0, 0, canvasWidth, canvasHeight)
    }
  }

  texMatrix() {
    const {
      canvasWidth, targetWidth, canvasHeight, targetHeight,
    } = this
    const matrix = mat2.create()
    return mat2.scale(matrix, matrix, [canvasWidth / targetWidth, canvasHeight / targetHeight])
  }
}


function getPowerOfTwo(n: number) {
  let i = 1
  while (i < n)
    i <<= 1
  return i
}
