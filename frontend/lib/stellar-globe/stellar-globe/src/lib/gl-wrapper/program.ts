import { mat2, mat3, mat4 } from 'gl-matrix'
import { AttribList } from './attrib_list'
import * as glUtils from './utils'


export class Program {
  private vertShader: WebGLShader
  private fragShader: WebGLShader
  private name: WebGLProgram
  private attribLocationMemo = new Map<string, number>()
  private uniformLocationMemo = new Map<string, WebGLUniformLocation>()
  private refCount = 1

  private constructor(
    readonly gl: WebGL2RenderingContext,
    vertSource: string,
    fragSource: string,
  ) {
    this.vertShader = this.createShader(vertSource, this.gl.VERTEX_SHADER)
    this.fragShader = this.createShader(fragSource, this.gl.FRAGMENT_SHADER)
    this.name = glUtils.nonNull(this.gl.createProgram())
    this.gl.attachShader(this.name, this.vertShader)
    this.gl.attachShader(this.name, this.fragShader)
    this.gl.linkProgram(this.name)
    if (!this.gl.getProgramParameter(this.name, this.gl.LINK_STATUS)) {
      throw `WebGL link error: ${this.gl.getProgramInfoLog(this.name)}`
    }
  }

  static new(gl: WebGL2RenderingContext, vertSource: string, fragSource: string) {
    const cachedProgram = recallProgram(gl, { vertSource, fragSource })
    if (cachedProgram) {
      ++cachedProgram.refCount
      return cachedProgram
    }
    else {
      const program = new Program(gl, vertSource, fragSource)
      const forget = memoProgram(gl, { vertSource, fragSource }, program)
      program.forget = forget
      return program
    }
  }

  private forget?: () => void

  release() {
    --this.refCount
    if (this.refCount == 0) {
      this.gl.deleteShader(this.fragShader)
      this.gl.deleteShader(this.vertShader)
      this.gl.deleteProgram(this.name)
      this.forget!()
    }
  }

  use() {
    const p = activeProgram.get(this.gl)
    if (p !== this) {
      activeProgram.set(this.gl, this)
      this.gl.useProgram(this.name)
    }
  }

  attribLocation(varName: string) {
    let location = this.attribLocationMemo.get(varName)
    if (location == undefined)
      location = this.gl.getAttribLocation(this.name, varName)
    if (location == -1)
      throw `unknown attribute: ${varName}`
    this.attribLocationMemo.set(varName, location)
    return location
  }

  uniformLocation(varName: string) {
    let location: WebGLUniformLocation | null | undefined = this.uniformLocationMemo.get(varName)
    if (location == undefined)
      location = this.gl.getUniformLocation(this.name, varName)
    if (location == null)
      throw `unknown uniform: ${varName}`
    this.uniformLocationMemo.set(varName, location)
    return location
  }

  enableAttribList(attribList: AttribList, cb: () => void) {
    this.use()
    attribList.enable(this, cb)
  }

  uniformMatrix4fv(matrices: { [name: string]: Float32Array | mat4 }, transpose: boolean = false) {
    for (let name in matrices) {
      let matrix = matrices[name]
      this.gl.uniformMatrix4fv(this.uniformLocation(name), transpose, matrix)
    }
  }

  uniformMatrix3fv(matrices: { [name: string]: Float32Array | mat3 }, transpose: boolean = false) {
    for (let name in matrices) {
      let matrix = matrices[name]
      this.gl.uniformMatrix3fv(this.uniformLocation(name), transpose, matrix)
    }
  }

  uniformMatrix2fv(matrices: { [name: string]: Float32Array | mat2 }, transpose: boolean = false) {
    for (let name in matrices) {
      let matrix = matrices[name]
      this.gl.uniformMatrix2fv(this.uniformLocation(name), transpose, matrix)
    }
  }

  uniform1f(vars: { [name: string]: number }) {
    for (let name in vars) {
      this.gl.uniform1f(this.uniformLocation(name), vars[name])
    }
  }

  uniform1i(vars: { [name: string]: number }) {
    for (let name in vars) {
      this.gl.uniform1i(this.uniformLocation(name), vars[name])
    }
  }

  uniform2fv(vars: { [name: string]: number[] }) {
    for (let name in vars) {
      this.gl.uniform2fv(this.uniformLocation(name), vars[name])
    }
  }

  uniform3fv(vars: { [name: string]: number[] }) {
    for (let name in vars) {
      this.gl.uniform3fv(this.uniformLocation(name), vars[name])
    }
  }

  uniform4fv(vars: { [name: string]: number[] }) {
    for (let name in vars) {
      this.gl.uniform4fv(this.uniformLocation(name), vars[name])
    }
  }

  private createShader(source: string, type: number): WebGLShader {
    let shader = this.gl.createShader(type)
    if (!shader) {
      throw `WebGL createShader error: ${this.gl.getError()}`
    }
    this.gl.shaderSource(shader, source)
    this.gl.compileShader(shader)
    if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
      throw `WebGL shader compile error: ${this.gl.getShaderInfoLog(shader)}\nsource:\n${glUtils.withLineNumber(source)}`
    }
    return glUtils.nonNull(shader)
  }
}


const activeProgram = new WeakMap<WebGL2RenderingContext, Program>()


const { recallProgram, memoProgram } = (() => {
  const memo = new WeakMap<WebGL2RenderingContext, Map<string, Program>>()

  function getMap(gl: WebGL2RenderingContext) {
    if (!memo.has(gl)) {
      memo.set(gl, new Map())
    }
    return memo.get(gl)!
  }

  type MemoSource = {
    vertSource: string
    fragSource: string
  }

  const makeKey = (sources: MemoSource) => {
    return JSON.stringify([sources.vertSource, sources.fragSource])
  }

  const recallProgram = (gl: WebGL2RenderingContext, sources: MemoSource) => {
    const map = getMap(gl)
    const key = makeKey(sources)
    return map.get(key)
  }

  const memoProgram = (gl: WebGL2RenderingContext, sources: MemoSource, program: Program) => {
    const map = getMap(gl)
    const key = makeKey(sources)
    map.set(key, program)
    return () => {
      map.delete(key)
    }
  }

  return { recallProgram, memoProgram }
})()
