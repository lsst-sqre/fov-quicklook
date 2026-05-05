import { mat4 } from "gl-matrix"
import { AttribList, Program, utils as glUtils } from '~/lib/gl-wrapper'
import { V3, V4 } from '~/types'
import { View } from "~/view"

export type JOINT = 'MITER' | 'NONE'

export type Point = {
  position: V3
  color: V4
  size: number
}

export type Path = {
  points: Point[]
  close: boolean
  joint: JOINT
}

export type BlendMode = 'NORMAL' | 'ADD'

import shaderFrag from './frag.glsl?raw'
import shaderVert from './vert.glsl?raw'


type Options = {
  darkenNarrowLine?: boolean
  minWidth?: number
  blendMode?: BlendMode
}


export class Renderer {
  private program: Program
  private attribList: AttribList

  // depthTest = false
  // stencilTest = false
  darkenNarrowLine: boolean
  minWidth: number
  blendMode: BlendMode

  modelMatrix = mat4.create()

  private _paths: Path[] = []

  setPaths(path: Path[]) {
    this._paths = path.slice()
    this.needsUpdatePaths = true
  }

  constructor(private readonly gl: WebGL2RenderingContext, options: Options = {}) {
    this.darkenNarrowLine = options.darkenNarrowLine ?? true
    this.minWidth = options.minWidth ?? 5
    this.blendMode = options.blendMode ?? 'ADD'

    this.program = Program.new(gl,
      shaderVert,
      shaderFrag,
    )
    this.attribList = new AttribList(gl, {
      members: [
        { name: 'a_p', nComponents: 3 },
        { name: 'a_a', nComponents: 3 },
        { name: 'a_b', nComponents: 3 },
        { name: 'a_y', nComponents: 1 },
        { name: 'a_width', nComponents: 1 },
        { name: 'a_color', nComponents: 4 },
      ],
    })
  }

  protected alreadyReleased = false

  release() {
    this.alreadyReleased = true
    this.attribList.release()
    this.program.release()
  }

  private needsUpdatePaths = false

  render(view: View, alpha = 1) {
    if (this.needsUpdatePaths) {
      this.updateVBO()
      this.needsUpdatePaths = false
    }

    if (this.attribList.vertexCount === 0) {
      return
    }

    if (alpha <= 0) {
      return
    }

    const mvp = view.mvp

    const gl = this.gl
    const p = this.program

    p.enableAttribList(this.attribList, () => {
      p.uniformMatrix4fv({ u_pvmMatrix: mat4.mul(mat4.create(), mvp.pv, this.modelMatrix) })
      p.uniform1f({
        u_alpha: alpha,
        u_fovy: mvp.fovy,
        u_aspectRatio: mvp.aspectRatio,
        u_minWidth: view.pixelRatio * this.minWidth / gl.drawingBufferHeight,
      })
      p.uniform1i({ u_darkenNarrowLine: this.darkenNarrowLine ? 1 : 0 })
      const features: number[] = [gl.BLEND]
      let clearBit = 0
      // if (this.stencilTest) {
      //   features.push(gl.STENCIL_TEST)
      //   clearBit |= gl.STENCIL_BUFFER_BIT
      //   gl.clearStencil(0)
      //   gl.stencilFunc(gl.EQUAL, 0, ~0)
      //   gl.stencilOp(gl.KEEP, gl.KEEP, gl.INCR)
      // }
      // if (this.depthTest) {
      //   features.push(gl.DEPTH_TEST)
      //   clearBit |= gl.DEPTH_BUFFER_BIT
      // }
      if (clearBit) {
        gl.clear(clearBit)
      }
      glUtils.enable(gl, features, () => {
        switch (this.blendMode) {
          case 'ADD':
            gl.blendFunc(gl.SRC_ALPHA, gl.ONE)
            break
          case 'NORMAL':
            gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
            break
        }
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, this.attribList.vertexCount)
      })
    })
  }

  private updateVBO() {
    const attrs: number[] = []
    const paths = this._paths
    for (const path of paths) {
      switch (path.joint) {
        case 'MITER':
          path2attrsMiter(attrs, path)
          break
        case 'NONE':
          path2attrsNone(attrs, path)
          break
      }
    }
    this.attribList.setData({ array: new Float32Array(attrs) })
  }
}

function path2attrsMiter(attrs: number[], path: Path) {
  // path.pointsはreduxなどから来ることがあり変更してはいけない
  const points = path.points.slice()
  if (path.points.length < 2) {
    throw new Error('Path must include more than 2 points')
  }
  if (path.close) {
    points.unshift(points[points.length - 1])
    points.push(points[1], points[2])
  } else {
    // cap ends
    points.unshift({
      ...points[0],
      position: points[0].position.map((p, i) => 2 * p - points[1].position[i]) as V3,
    })
    const last = points.length - 1
    points.push({
      ...points[last],
      position: points[last].position.map((p, i) => 2 * p - points[last - 1].position[i]) as V3,
    })
  }
  for (let i = 1; i < points.length - 1; ++i) {
    // (a) - (p) - (b)
    const p = points[i]
    const a = points[i - 1]
    const b = points[i + 1]
    attrs.push(...p.position, ...a.position, ...b.position, -1, 0.5 * p.size, ...p.color)
    if (i === 1) {
      attrs.push(...attrs.slice(attrs.length - 15))
    }
    attrs.push(...p.position, ...a.position, ...b.position, +1, 0.5 * p.size, ...p.color)
  }
  attrs.push(...attrs.slice(attrs.length - 15))
}

function path2attrsNone(attrs: number[], path: Path) {
  const points = path.points.slice()
  if (points.length < 2) {
    throw new Error('Path must include more than 2 points')
  }

  if (path.close) {
    points.push(points[0])
  }

  for (let i = 0; i < points.length - 1; ++i) {
    const a = points[i]
    const b = points[i + 1]
    const a2 = [0, 1, 2].map((j) => 2 * a.position[j] - b.position[j]) // a + (a - b)
    const b2 = [0, 1, 2].map((j) => 2 * b.position[j] - a.position[j]) // b + (b - a)
    attrs.push(...a.position, ...a2, ...b.position, +1, 0.5 * a.size, ...a.color)
    attrs.push(...a.position, ...a2, ...b.position, +1, 0.5 * a.size, ...a.color)
    attrs.push(...a.position, ...a2, ...b.position, -1, 0.5 * a.size, ...a.color)
    attrs.push(...b.position, ...a.position, ...b2, +1, 0.5 * b.size, ...b.color)
    attrs.push(...b.position, ...a.position, ...b2, -1, 0.5 * b.size, ...b.color)
    attrs.push(...b.position, ...a.position, ...b2, -1, 0.5 * b.size, ...b.color)
  }
}
