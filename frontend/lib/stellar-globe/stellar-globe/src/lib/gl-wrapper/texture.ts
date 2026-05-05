import * as glUtils from './utils'

export type ImageLike = ImageBitmap

export class Texture {
  readonly name: WebGLTexture

  constructor(readonly gl: WebGL2RenderingContext, parameterSetter?: (gl: WebGL2RenderingContext) => void) {
    this.name = glUtils.nonNull(gl.createTexture())
    this.bind(() => (parameterSetter || defaultParameterSetter)(this.gl))
  }

  release() {
    this.gl.deleteTexture(this.name)
  }

  bind(cb: () => void) {
    this.gl.bindTexture(this.gl.TEXTURE_2D, this.name)
    cb()
    this.gl.bindTexture(this.gl.TEXTURE_2D, null)
  }

  setImage(img: ImageLike) {
    const gl = this.gl
    this.bind(() => {
      this.gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img)
    })
  }

  setImageArrayBuffer(ab: Uint8Array, width: number, height: number) {
    const gl = this.gl
    this.bind(() => {
      this.gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, ab)
    })
  }
}


function defaultParameterSetter(gl: WebGL2RenderingContext) {
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
}