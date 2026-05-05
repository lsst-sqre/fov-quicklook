import { Program } from './program'
import * as glUtils from './utils'


type Member = {
  name: string
  dataType?: number
  normalize?: boolean
  nComponents: number
}


type TypedArray = Float32Array
type DataOption = { members?: Member[], array?: TypedArray, usage?: number }


export class AttribList {
  private bufferName: WebGLBuffer
  private stride!: number
  private offset!: number[]
  private members!: Member[]
  private usage = -1
  private bufferSize = -1
  vertexCount = 0

  constructor(readonly gl: WebGL2RenderingContext, data?: DataOption) {
    this.bufferName = glUtils.nonNull(gl.createBuffer())
    if (data) {
      this.setData(data)
    }
  }

  release() {
    this.gl.deleteBuffer(this.bufferName)
  }

  setData({ members, array, usage = this.gl.STATIC_DRAW }: DataOption) {
    if (members) {
      this.members = members
      this.stride = 0
      this.offset = []
      for (const m of members) {
        if (m.dataType == undefined) m.dataType = this.gl.FLOAT
        if (m.normalize == undefined) m.normalize = false
        this.offset.push(this.stride)
        this.stride += m.nComponents * sizeof(this.gl, m.dataType)
      }
    }
    if (array) {
      this.vertexCount = byteLength(array) / this.stride
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.bufferName)
      if (usage != this.usage || this.bufferSize < this.vertexCount) {
        this.usage = usage
        this.bufferSize = this.vertexCount
        this.gl.bufferData(this.gl.ARRAY_BUFFER, array, usage)
      }
      else {
        this.gl.bufferSubData(this.gl.ARRAY_BUFFER, 0, array)
      }
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, null)
      if (this.vertexCount % 1 !== 0) {
        throw "nComponents may be invalid"
      }
    }
  }

  enable(program: Program, f: () => void) {
    const gl = this.gl
    gl.bindBuffer(gl.ARRAY_BUFFER, this.bufferName)
    for (const i in this.members) {
      const m = this.members[i]
      gl.enableVertexAttribArray(program.attribLocation(m.name))
      gl.vertexAttribPointer(program.attribLocation(m.name), m.nComponents, m.dataType!, m.normalize!, this.stride, this.offset[i])
    }
    f()
    for (const m of this.members) {
      gl.disableVertexAttribArray(program.attribLocation(m.name))
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, null)
  }

}


function sizeof(gl: WebGL2RenderingContext, dataType: number) {
  switch (dataType) {
    case gl.FLOAT:
      return 4
    default:
      throw `unknown type: ${dataType}`
  }
}


function byteLength(array: TypedArray) {
  return array.length * array.BYTES_PER_ELEMENT
}