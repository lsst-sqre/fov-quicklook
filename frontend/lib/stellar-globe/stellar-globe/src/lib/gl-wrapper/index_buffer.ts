import * as glUtils from './utils'

type DataOption = {
  usage?: number,
  array: Int16Array,
}

export class IndexBuffer {
  private name: WebGLBuffer
  private usage!: number
  private _length!: number

  constructor(readonly gl: WebGL2RenderingContext, dataOption?: DataOption) {
    this.name = glUtils.nonNull(this.gl.createBuffer())
    if (dataOption)
      this.setData(dataOption)
  }

  release() {
    this.gl.deleteBuffer(this.name)
  }

  bind(cb: () => void) {
    this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, this.name)
    cb()
    this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, null)
  }

  setData({ usage, array }: DataOption) {
    this.usage = usage || this.gl.STATIC_DRAW
    this._length = array.length
    this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, this.name)
    this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER, array, this.usage)
    this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, null)
  }

  get length() {
    return this._length
  }
}