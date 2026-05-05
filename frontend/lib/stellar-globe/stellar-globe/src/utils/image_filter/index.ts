import { AttribList, Program, Texture, ImageLike } from "~/lib/gl-wrapper"
import vertShader from './imageFilter.vert.glsl?raw'


export abstract class ImageFilter {
  protected program: Program
  private attribList: AttribList
  private frameBuffer: WebGLFramebuffer
  private textures: Texture[] = []

  constructor(
    readonly gl: WebGL2RenderingContext,
    fragmentShader: string,
  ) {
    this.attribList = new AttribList(gl, {
      members: [{ name: 'a_coord', nComponents: 2 }],
      array: new Float32Array([
        0, 0, 1, 0, 1, 1,
        0, 0, 1, 1, 0, 1,
      ]),
    })
    this.frameBuffer = gl.createFramebuffer()!
    this.program = Program.new(
      gl,
      vertShader,
      fragmentShader,
    )
  }

  release() {
    this.attribList.release()
    this.gl.deleteFramebuffer(this.frameBuffer)
    this.program.release()
    for (const t of this.textures) { t.release() }
  }

  protected setUniformParams() { }

  applyToImages(outTexture: Texture, outWidth: number, outHeight: number, images: ImageLike[]) {
    return this.apply(outTexture, outWidth, outHeight, images.length, (t, i) => t.setImage(images[i]))
  }

  apply(
    outTexture: Texture, outWidth: number, outHeight: number, nSources: number, setter: (t: Texture, i: number) => void,
  ) {
    const { gl, program } = this

    gl.bindTexture(gl.TEXTURE_2D, outTexture.name)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, outWidth, outHeight, 0, gl.RGBA, gl.UNSIGNED_BYTE, null)
    gl.bindTexture(gl.TEXTURE_2D, null)

    gl.bindFramebuffer(gl.FRAMEBUFFER, this.frameBuffer)
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, outTexture.name, 0)

    const { drawingBufferWidth, drawingBufferHeight } = gl
    gl.viewport(0, 0, outWidth, outHeight)

    for (let i = 0; i < nSources; ++i) {
      if (!this.textures[i]) {
        this.textures[i] = new Texture(this.gl)
      }
      setter(this.textures[i], i)
    }

    program.use()
    this.setUniformParams()
    this.attribList.enable(program, () => {
      for (let i = 0; i < nSources; ++i) {
        gl.uniform1i(program.uniformLocation(`u_texture${i}`), i)
        gl.activeTexture((gl as any)[`TEXTURE${i}`])
        gl.bindTexture(gl.TEXTURE_2D, this.textures[i].name)
      }
      gl.drawArrays(gl.TRIANGLES, 0, 6)
      for (let i = 0; i < nSources; ++i) {
        gl.activeTexture((gl as any)[`TEXTURE${i}`])
        gl.bindTexture(gl.TEXTURE_2D, null)
      }
    })

    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    gl.activeTexture(gl.TEXTURE0)
    gl.viewport(0, 0, drawingBufferWidth, drawingBufferHeight)
  }
}
