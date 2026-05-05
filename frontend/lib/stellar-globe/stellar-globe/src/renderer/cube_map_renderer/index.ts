// import { mat4 } from 'gl-matrix'
// import { AttribList, ImageLike, IndexBuffer, Program, utils as glUtils } from "~/lib/gl-wrapper"
// import { View } from "~/view"
// import shaderFrag from './frag.glsl?raw'
// import shaderVert from './vert.glsl?raw'



// export class CubeMapRenderer {
//   private program: Program
//   private attribList!: AttribList
//   private indexBuffer!: IndexBuffer
//   private texture?: WebGLTexture

//   constructor(readonly gl: WebGL2RenderingContext) {
//     this.program = Program.new(gl,
//       shaderVert,
//       shaderFrag,
//     )
//     this.buildArray()
//   }

//   release() {
//     this.program.release()
//     this.attribList.release()
//     this.indexBuffer.release()
//     this.texture && this.gl.deleteTexture(this.texture)
//   }

//   render(view: View, alpha = 1) {
//     if (this.texture === undefined) {
//       return
//     }
//     if (alpha <= 0) {
//       return
//     }
//     const p = this.program
//     const gl = this.gl
//     p.use()
//     p.enableAttribList(this.attribList, () => {
//       p.uniform1i({ u_cubeTexture: 0 })
//       // @ts-ignore
//       p.uniformMatrix4fv({ u_pvMatrix: view.mvp.pv, u_mMatrix: this.mMatrix() })
//       p.uniform3fv({ u_eyePosition: view.mvp.eyePosition })
//       p.uniform1f({
//         u_alpha: alpha,
//         u_radius: 1,
//       })
//       glUtils.enable(gl, [gl.BLEND, gl.CULL_FACE], () => {
//         gl.blendFunc(gl.SRC_ALPHA, gl.ONE)
//         this.indexBuffer.bind(() => {
//           gl.bindTexture(gl.TEXTURE_CUBE_MAP, this.texture!)
//           gl.drawElements(gl.TRIANGLES, this.indexBuffer.length, gl.UNSIGNED_SHORT, 0)
//           gl.bindTexture(gl.TEXTURE_CUBE_MAP, null)
//         })
//       })
//     })
//   }

//   protected mMatrix() {
//     return E
//   }

//   private buildArray() {
//     this.attribList = new AttribList(this.gl, {
//       members: [
//         { name: 'a_position', nComponents: 3 },
//       ],
//       array: new Float32Array([
//         -1, -1, -1,
//         -1, -1, +1,
//         -1, +1, -1,
//         -1, +1, +1,
//         +1, -1, -1,
//         +1, -1, +1,
//         +1, +1, -1,
//         +1, +1, +1,
//       ]),
//     })
//     this.indexBuffer = new IndexBuffer(this.gl, {
//       array: new Int16Array([
//         1, 0, 2, 1, 2, 3,
//         1, 7, 5, 1, 3, 7,
//         5, 7, 6, 4, 5, 6,
//         3, 6, 7, 2, 6, 3,
//         0, 6, 2, 0, 4, 6,
//         0, 1, 5, 0, 5, 4,
//       ]),
//     })
//   }

//   private setupTexture() {
//     const gl = this.gl
//     this.texture = gl.createTexture()!
//     gl.bindTexture(gl.TEXTURE_CUBE_MAP, this.texture!)
//     gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
//     gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
//     gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
//     gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
//     gl.bindTexture(gl.TEXTURE_CUBE_MAP, null)
//   }

//   static faces = ['px', 'py', 'pz', 'nx', 'ny', 'nz']

//   setCubeImage(images: ImageLike[]) {
//     const gl = this.gl
//     this.texture || this.setupTexture()
//     const targets = [
//       gl.TEXTURE_CUBE_MAP_POSITIVE_X,
//       gl.TEXTURE_CUBE_MAP_POSITIVE_Y,
//       gl.TEXTURE_CUBE_MAP_POSITIVE_Z,
//       gl.TEXTURE_CUBE_MAP_NEGATIVE_X,
//       gl.TEXTURE_CUBE_MAP_NEGATIVE_Y,
//       gl.TEXTURE_CUBE_MAP_NEGATIVE_Z,
//     ]
//     gl.bindTexture(gl.TEXTURE_CUBE_MAP, this.texture!)
//     for (let i = 0; i < targets.length; ++i) {
//       gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 1)
//       gl.texImage2D(targets[i], 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, images[i])
//       gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 0)
//     }
//     gl.generateMipmap(gl.TEXTURE_CUBE_MAP)
//     gl.bindTexture(gl.TEXTURE_CUBE_MAP, null)
//   }
// }

// const E = mat4.create()
