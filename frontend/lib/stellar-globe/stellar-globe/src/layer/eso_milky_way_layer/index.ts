import { mat4 } from 'gl-matrix'
import { wegblProfile } from '~/devel/webgl-profiler/utils'
import { Globe } from '~/globe'
import { Layer } from '~/layer/layer'
import { overlayAlpha } from '~/layer/overlayAlpha'
import { ImageLike } from '~/lib/gl-wrapper'
import { CubeMapRenderer } from '~/renderer/cube_map_renderer2'
import { loadImage } from '~/utils/image'
import { View } from '~/view'

// thanks to ESO/S. Brunier
// https://www.eso.org/public/images/eso0932a/


type Options = {
  fadeInDuration?: number
  imageSize?: 512 | 1024
}


export class EsoMilkyWayLayer extends Layer {
  private renderer?: EsoMilkyWay

  constructor(
    globe: Globe,
    options: Options = {},
  ) {
    super(globe)
    this.loadImages(options)
  }

  private fadeAlpha = 0

  private async loadImages({
    fadeInDuration = 400,
    imageSize = 1024,
  }: Options) {
    let alive = true
    this.onRelease(() => alive = false)
    const gl = this.globe.gl
    const maxCubeMapSize = Math.min(gl.getParameter(gl.MAX_CUBE_MAP_TEXTURE_SIZE), imageSize)
    const images = await EsoMilkyWay.loadImages(this.globe.dataRepository, maxCubeMapSize)
    if (alive) {
      this.renderer = new EsoMilkyWay(this.globe.gl, images)
      this.onRelease(() => this.renderer?.release())
      this.addAnimation(({ r }) => {
        this.fadeAlpha = r
      }, { duration: fadeInDuration })
    }
  }

  render(view: View) {
    wegblProfile(this.globe.gl, 'EsoMiokyWay', () => {
      const alpha = overlayAlpha(view) * this.fadeAlpha
      this.renderer?.render(view, alpha)
    })
  }

  static attributions = [{
    which: 'The Milky Way Panorama',
    label: 'ESO/S. Brunier',
    link: 'https://www.eso.org/public/images/eso0932a/',
  }]
}


class EsoMilkyWay extends CubeMapRenderer {
  constructor(
    gl: WebGL2RenderingContext,
    images: ImageLike[],
  ) {
    super(gl)
    this.setCubeImage(images)
  }

  private m = mat4.fromValues(
    +0.0017373464070261, -0.4792437255382538, -0.8776800036430359, 0,
    +0.8911036849021912, +0.3990314602851868, -0.2161209583282471, 0,
    +0.4537965655326843, -0.7817283272743225, +0.4277492463588715, 0,
    0, 0, 0, 1,
  )

  mMatrix() {
    return this.m
  }

  static async loadImages(dataRepository: string, maxCubeMapSize: number) {
    const sizes = [1024, 512]
    for (const size of sizes) {
      if (size <= maxCubeMapSize) {
        const urls = ['px', 'py', 'pz', 'nx', 'ny', 'nz']
          .map((dir) => `${dataRepository}/eso_milky_way_layer/images-${size}/${dir}.png`)
        const images = await Promise.all(urls.map(url => loadImage(url, { flipY: false })))
        return images
      }
    }
    throw new Error(`No available image: size: ${maxCubeMapSize}`)
  }

  // private enableMatrixCalibrator() {
  //   let scale = 0.001
  //   const globe = this.globe
  //   // @ts-ignore
  //   return on(document, 'keydown', (e: KeyboardEvent) => {
  //     const camera = globe.viewFactory.view().camera
  //     switch (e.code) {
  //       case 'KeyA':
  //         scale *= e.shiftKey ? 0.5 : 2
  //         break
  //       case 'KeyR':
  //         mat4.rotate(this.m, this.m, (e.shiftKey ? +1 : -1) * scale, camera.direction)
  //         globe.requestRefresh()
  //         break
  //       case 'KeyX':
  //         mat4.rotate(this.m, this.m, (e.shiftKey ? +1 : -1) * scale, camera.up)
  //         globe.requestRefresh()
  //         break
  //       case 'KeyY':
  //         const axis = vec3.cross(vec3.create(), camera.up, camera.direction)
  //         mat4.rotate(this.m, this.m, (e.shiftKey ? +1 : -1) * scale, axis)
  //         globe.requestRefresh()
  //         break
  //     }
  //     console.log(this.m)
  //   })
  // }
}
