import { mat4 } from "gl-matrix"
import { AttribList, Program, utils as glUtils } from '~/lib/gl-wrapper'
import { V3, V4 } from '~/types'
import { ReleaseCallbacks } from "~/utils/EventManager"
import { View } from "~/view"
import shaderFrag from './frag.glsl?raw'
import shaderVert from './vert.glsl?raw'


export type Vertex = {
  position: V3
  color: V4
}

export type BlendMode = 'NORMAL' | 'ADD'

export class Renderer {
  blendMode: BlendMode = 'ADD'
  modelMatrix = mat4.create()

  private program: Program
  private attribList: AttribList
  private releaseCallbacks = ReleaseCallbacks()
  private onRelease = this.releaseCallbacks.add

  constructor(private readonly gl: WebGL2RenderingContext) {
    this.program = Program.new(gl,
      shaderVert,
      shaderFrag,
    )
    this.attribList = new AttribList(gl, {
      members: [
        { name: 'a_position', nComponents: 3 },
        { name: 'a_color', nComponents: 4 },
      ],
    })
    this.onRelease(() => {
      this.attribList.release()
      this.program.release()
    })
  }

  private vertices: Vertex[] = []
  private needsUpdate = false

  addStrips(vs: Vertex[]) {
    this.vertices.push(vs[0], ...vs, vs[vs.length - 1])
    this.needsUpdate = true
  }

  addTriangle(a: Vertex, b: Vertex, c: Vertex) {
    this.addStrips([a, b, c, c])
  }

  release() {
    this.releaseCallbacks.flush()
  }

  render(view: View, alpha = 1) {
    if (this.needsUpdate) {
      this.updateVBO()
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
      })
      glUtils.enable(gl, [gl.BLEND], () => {
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
    for (const v of this.vertices) {
      attrs.push(
        ...v.position,
        ...v.color,
      )
    }
    this.attribList.setData({ array: new Float32Array(attrs) })
    this.needsUpdate = false
  }
}