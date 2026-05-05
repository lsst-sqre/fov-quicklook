import { AttribList, Program, Texture, utils as glUtils } from "~/lib/gl-wrapper"
import { get2dContext } from "~/utils/canvas"
import { View } from "~/view"
import shaderFrag from './frag.glsl?raw'
import shaderVert from './vert.glsl?raw'

import { V2, V3, V4 } from '~/types'
import { Box, PackRectSizeError, tryPackRects } from "./pack_rects"

export type BillboardImage = {
  imageData: ImageData
  origin: V2
}

export type BillboardImageRef = {
  imageID: number
  position: V3
  color: V4
}

type BBox = {
  rect: Rect
  origin: V2
}


export class BillboardRenderer {
  scale = 1

  private program: Program
  private attribList: AttribList
  private texture: Texture

  color: V4 = [1, 1, 1, 1]

  constructor(
    private readonly gl: WebGL2RenderingContext,
    images: BillboardImage[] = [],
    imageRefs: BillboardImageRef[] = [],
  ) {
    this.program = Program.new(gl,
      shaderVert,
      shaderFrag,
    )
    this.attribList = new AttribList(gl, {
      members: [
        { name: 'a_vCoord', nComponents: 3 },
        { name: 'a_color', nComponents: 4 },
        { name: 'a_size', nComponents: 2 },
        { name: 'a_tCoord', nComponents: 2 },
      ],
    })
    this.texture = new Texture(gl)
    this.buildArray(images, imageRefs)
  }

  release() {
    this.program.release()
    this.attribList.release()
    this.texture.release()
  }

  buildArray(images: BillboardImage[], imageRefs: BillboardImageRef[]) {
    const gl = this.gl
    const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE)
    const packedTexture = packTextures(images, maxTextureSize)
    this.texture.bind(() => {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, packedTexture.imageData)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
      gl.generateMipmap(gl.TEXTURE_2D)
    })
    const attrs: number[] = []
    const { width: W, height: H } = packedTexture.imageData
    for (const s of imageRefs) {
      const { rect: { left: l, right: r, top: t, bottom: b, width: w, height: h }, origin: o } = packedTexture.bbox[s.imageID]
      attrs.push(
        ...s.position, ...s.color, (-1 + o[0]) * w, (-1 + o[1]) * h, l / W, b / H,
        ...s.position, ...s.color, (+1 + o[0]) * w, (-1 + o[1]) * h, r / W, b / H,
        ...s.position, ...s.color, (+1 + o[0]) * w, (+1 + o[1]) * h, r / W, t / H,
        ...s.position, ...s.color, (-1 + o[0]) * w, (-1 + o[1]) * h, l / W, b / H,
        ...s.position, ...s.color, (+1 + o[0]) * w, (+1 + o[1]) * h, r / W, t / H,
        ...s.position, ...s.color, (-1 + o[0]) * w, (+1 + o[1]) * h, l / W, t / H,
      )
    }
    this.attribList.setData({
      array: new Float32Array(attrs),
    })
  }

  render(view: View, alpha = 1) {
    if (this.attribList.vertexCount === 0 || alpha <= 0) {
      return
    }
    const gl = this.gl
    const p = this.program
    p.use()
    const ratio = this.scale * view.pixelRatio
    p.uniformMatrix4fv({ u_pvMatrix: view.mvp.pv })
    p.uniform4fv({ u_color: this.color })
    p.uniform1i({ u_texture: 0 })
    p.uniform1f({
      u_alpha: alpha,
      u_width: 1 / ratio * gl.drawingBufferWidth,
      u_height: 1 / ratio * gl.drawingBufferHeight,
    })
    glUtils.enable(gl, [gl.BLEND], () => {
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
      this.texture.bind(() => {
        this.attribList.enable(p, () => {
          gl.drawArrays(gl.TRIANGLES, 0, this.attribList.vertexCount)
        })
      })
    })
  }
}


function packTextures(images: BillboardImage[], maxSize: number) {
  const boxes: Box[] = images.map(image => ({ width: image.imageData.width + 2, height: image.imageData.height + 2 }))
  try {
    const { boxPositions, containerHeight, containerWidth } = tryPackRects(boxes, maxSize)
    const canvasWidth = powerOf2(containerWidth)
    const canvasHeight = powerOf2(containerHeight)
    return get2dContext(canvasWidth, canvasHeight, (ctx) => {
      const bbox: BBox[] = []
      for (let i = 0; i < images.length; ++i) {
        const image = images[i]
        const { x, y } = boxPositions[i]
        const { width, height } = image.imageData
        ctx.putImageData(image.imageData, x + 1, y + 1)
        bbox.push({
          rect: new Rect(
            width, height,
            x, y,
          ), origin: image.origin
        })
      }
      return {
        imageData: ctx.getImageData(0, 0, canvasWidth, canvasHeight),
        bbox,
      }
    })
  }
  catch (e) {
    if (e instanceof PackRectSizeError) {
      return {
        imageData: new ImageData(1, 1),
        bbox: []
      }
    }
    throw e
  }
}


function powerOf2(n: number) {
  let p = 1
  while (p < n) {
    p *= 2
  }
  return p
}


class Rect {
  constructor(
    readonly width: number,
    readonly height: number,
    readonly left: number,
    readonly top: number,
  ) { }
  get right() { return this.left + this.width }
  get bottom() { return this.top + this.height }
}
