import { AttribList, Program, utils as glUtils } from '~/lib/gl-wrapper'
import { V3, V4 } from "~/types"
import { View } from "~/view"
import shaderFrag from './frag.glsl?raw'
import shaderVert from './vert.glsl?raw'


type Point = {
  position: V3
  color: V4
  size: number
}


export class PointRenderer {
  private program: Program
  private attribList: AttribList

  darkenSmallPoint = true
  minSize = 3

  constructor(private readonly gl: WebGL2RenderingContext) {
    this.program = Program.new(gl,
      shaderVert,
      shaderFrag,
    )
    this.attribList = new AttribList(gl, {
      members: [
        { name: 'a_position', nComponents: 3 },
        { name: 'a_size', nComponents: 1 },
        { name: 'a_color', nComponents: 4 },
      ],
    })
  }

  release() {
    this.attribList.release()
    this.program.release()
  }

  render(view: View, alpha = 1) {
    if (this.attribList.vertexCount === 0) {
      return
    }

    if (alpha <= 0) {
      return
    }

    const camera = view.mvp

    const gl = this.gl
    const p = this.program
    p.enableAttribList(this.attribList, () => {
      p.uniformMatrix4fv({ u_pvMatrix: camera.pv })
      p.uniform1f({
        u_alpha: alpha,
        u_fovy: camera.fovy,
        u_bufferHeight: gl.drawingBufferHeight,
        u_minSize: this.minSize,
      })
      p.uniform1i({ u_darkenSmallPoint: this.darkenSmallPoint ? 1 : 0 })
      glUtils.enable(gl, [gl.BLEND], () => {
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE)
        gl.drawArrays(gl.POINTS, 0, this.attribList.vertexCount)
      })
    })
  }

  // @ts-ignore
  private updateVBO(points: Point[]) {
    /*
      { name: 'a_position', nComponents: 3 },
      { name: 'a_size', nComponents: 1 },
      { name: 'a_color', nComponents: 4 },
    */
    const attrs: number[] = []
    for (const p of points) {
      attrs.push(...p.position, p.size, ...p.color)
    }
    this.attribList.setData({ array: new Float32Array(attrs) })
  }

  setArray(array: Float32Array) {
    this.attribList.setData({ array })
  }
}
