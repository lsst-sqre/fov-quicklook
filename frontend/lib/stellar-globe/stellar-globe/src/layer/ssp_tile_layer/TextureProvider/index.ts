import { wegblProfile } from "~/devel/webgl-profiler/utils"
import { Globe } from "~/globe"
import { Cache } from "~/lib/cache"
import { ImageLike } from '~/lib/gl-wrapper'
import { nonNull } from "~/lib/gl-wrapper/utils"
import { AsyncTextureProvider, TileRef, TileTexture, Tract } from "~/renderer/tile_renderer"
import { loadImage } from "~/utils"
import { ImageFilter } from "~/utils/image_filter"
import { range } from "~/utils/math"
import decode_png from './glsl/decode_png.glsl?raw'
import sdss_true_color from './glsl/sdss_true_color.glsl?raw'
import sdss_true_color_mixer_png from './glsl/sdss_true_color_png_mixer.frag.glsl?raw'
import simple_rgb from './glsl/simple_rgb.glsl?raw'
import simple_rgb_png_mixer from './glsl/simple_rgb_png_mixer.frag.glsl?raw'
import { SspTileParams, SspTileParamsOf } from "./params"


class SimpleRgbMixerPng extends ImageFilter {
  constructor(
    gl: WebGL2RenderingContext,
    public params: SspTileParamsOf<'simpleRgb'>,
  ) {
    super(gl, expandShader(simple_rgb_png_mixer))
  }

  setUniformParams() {
    this.program.uniform1f({
      u_a: this.params.a,
      u_bias: this.params.bias,
      u_beta: this.params.beta,
      u_b0: this.params.b0,
    })
  }
}

class SdssTrueColorMixerPng extends ImageFilter {
  constructor(
    gl: WebGL2RenderingContext,
    public params: SspTileParamsOf<'sdssTrueColor'>,
  ) {
    super(gl, expandShader(sdss_true_color_mixer_png))
  }

  setUniformParams() {
    this.program.uniform1f({
      u_a: this.params.a,
      u_bias: this.params.bias,
      u_beta: this.params.beta,
      u_b0: this.params.b0,
    })
  }
}


class SimpleColorMatrixPng extends ImageFilter {
  constructor(
    gl: WebGL2RenderingContext,
    public params: SspTileParamsOf<'simpleColorMatrix'>,
  ) {
    super(gl, SimpleColorMatrixPng.fragmentShader(params))
  }

  static fragmentShader(params: SspTileParamsOf<'simpleColorMatrix'>) {
    // 出力は
    // r = \sum_i colors[i][0]
    // g = \sum_i colors[i][1]
    // b = \sum_i colors[i][2]
    // raw = decode_png(vec3(r, g, b))
    // float t0 = texture(u_texture0, v_coord).r,
    //       t1 = texture(u_texture1, v_coord).r, ...;
    // float r = color[0][0] * t0 + color[1][0] * t1 + ...;
    // float g = color[0][1] * t0 + color[1][1] * t1 + ...;

    const n = params.colors.length
    const ts = range(n).map(i => `t${i} = texture(u_texture${i}, v_coord).r`).join(', ')
    const r = range(n).map(i => `u_color[${i}][0] * t${i}`).join(' + ')
    const g = range(n).map(i => `u_color[${i}][1] * t${i}`).join(' + ')
    const b = range(n).map(i => `u_color[${i}][2] * t${i}`).join(' + ')

    const fragShader = expandShader(`\
      #version 300 es

      precision highp float;
      uniform sampler2D ${range(n).map(t => `u_texture${t}`)};
      uniform vec3  u_color[${n}];
      uniform float u_beta;
      uniform float u_a;
      uniform float u_bias;
      uniform float u_b0;
      in      vec2  v_coord;
      out     vec4  outputColor;

      //@import ./decode_png;
      //@import ./simple_rgb;
      
      void main(void){
        float ${ts};
        vec3 raw = decode_png(vec3(${r}, ${g}, ${b}));
        vec3 color = simple_rgb(raw, u_beta, u_a, u_bias, u_b0);
        outputColor = vec4(color, 1.);
      }
    `)

    return fragShader
  }

  setUniformParams() {
    this.program.uniform3fv(Object.fromEntries(
      this.params.colors.map((c, i) => [`u_color[${i}]`, c])
    ))
    this.program.uniform1f({
      u_a: this.params.a,
      u_bias: this.params.bias,
      u_beta: this.params.beta,
      u_b0: this.params.b0,
    })
  }
}


class SdssTrueColorMatrixPng extends ImageFilter {
  constructor(
    gl: WebGL2RenderingContext,
    public params: SspTileParamsOf<'sdssTrueColorMatrix'>,
  ) {
    super(gl, SdssTrueColorMatrixPng.fragmentShader(params))
  }

  static fragmentShader(params: SspTileParamsOf<"sdssTrueColorMatrix">) {
    // 出力はF
    // r = \sum_i colors[i][0]
    // g = \sum_i colors[i][1]
    // b = \sum_i colors[i][2]
    // raw = decode_png(vec3(r, g, b))
    // float t0 = texture(u_texture0, v_coord).r,
    //       t1 = texture(u_texture1, v_coord).r, ...;
    // float r = color[0][0] * t0 + color[1][0] * t1 + ...;
    // float g = color[0][1] * t0 + color[1][1] * t1 + ...;

    const n = params.colors.length
    const ts = range(n).map(i => `t${i} = texture(u_texture${i}, v_coord).r`).join(', ')
    const r = range(n).map(i => `u_color[${i}][0] * t${i}`).join(' + ')
    const g = range(n).map(i => `u_color[${i}][1] * t${i}`).join(' + ')
    const b = range(n).map(i => `u_color[${i}][2] * t${i}`).join(' + ')

    const fragShader = expandShader(`\
      #version 300 es
      precision highp float;
      uniform sampler2D ${range(n).map(t => `u_texture${t}`)};
      uniform vec3  u_color[${n}];
      uniform float u_beta;
      uniform float u_a;
      uniform float u_bias;
      uniform float u_b0;
      in      vec2  v_coord;
      out     vec4  outputColor;

      //@import ./decode_png;
      //@import ./sdss_true_color;
      
      void main(void){
        float ${ts};
        vec3 raw = decode_png(vec3(${r}, ${g}, ${b}));
        vec3 color = sdss_true_color(raw, u_beta, u_a, u_bias, u_b0);
        outputColor = vec4(color, 1.);
      }
    `)

    return fragShader
  }

  setUniformParams() {
    this.program.uniform3fv(Object.fromEntries(
      this.params.colors.map((c, i) => [`u_color[${i}]`, c])
    ))
    this.program.uniform1f({
      u_a: this.params.a,
      u_bias: this.params.bias,
      u_beta: this.params.beta,
      u_b0: this.params.b0,
    })
  }
}


export type MagFilter = 'nearest' | 'linear'


type SspTileTextureProviderOptions = {
  baseUrl: string
  params: SspTileParams
  magFilter: MagFilter
}


export class SspTileTextureProvider extends AsyncTextureProvider {
  private tracts: Tract[] = []
  private tractName = new Map<Tract, string>()
  private imageFilter!: ImageFilter
  private params!: SspTileParams
  private imageCache: ReturnType<typeof CachedImageLoader>
  private magFilter
  readonly baseUrl: string

  constructor(
    globe: Globe,
    {
      baseUrl,
      params,
      magFilter,
    }: SspTileTextureProviderOptions,
  ) {
    super(globe)
    this.baseUrl = baseUrl
    this.magFilter = magFilter
    this.imageCache = CachedImageLoader()
    this.onRelease(() => this.imageCache.release())
    this.setParams(params)
    this.loadMetadata()
    const offResize = this.globe.on('resize', () => this.updateImageCacheSize())
    this.onRelease(offResize)
  }

  private updateImageCacheSize() {
    const { width, height } = this.globe.canvas.domElement
    const margin = 2
    const n = Math.floor(
      margin *
      4 * // 1レベル上の画像
      this.params.filters.length *
      width * height / (256 ** 2)
    )
    this.imageCache.setCacheSize(n)
  }

  setParams(params: SspTileParams) {
    if (
      params.type !== this.params?.type ||
      params.filters.length !== this.params?.filters.length
    ) { // constructor内では this.params === undefined
      this.imageFilter && this.imageFilter.release()
      switch (params.type) {
        case 'sdssTrueColor':
          this.imageFilter = new SdssTrueColorMixerPng(this.globe.gl, params.sdssTrueColor)
          break
        case 'simpleRgb':
          this.imageFilter = new SimpleRgbMixerPng(this.globe.gl, params.simpleRgb)
          break
        case 'simpleColorMatrix':
          this.imageFilter = new SimpleColorMatrixPng(this.globe.gl, params.simpleColorMatrix)
          break
        case 'sdssTrueColorMatrix':
          this.imageFilter = new SdssTrueColorMatrixPng(this.globe.gl, params.sdssTrueColorMatrix)
          break
      }
      this.onRelease(() => this.imageFilter.release())
    }
    switch (params.type) {
      case 'sdssTrueColor':
        (this.imageFilter as SdssTrueColorMixerPng).params = params.sdssTrueColor
        break
      case 'simpleRgb':
        (this.imageFilter as SimpleRgbMixerPng).params = params.simpleRgb
        break
      case 'simpleColorMatrix':
        (this.imageFilter as SimpleColorMatrixPng).params = params.simpleColorMatrix
        break
      case 'sdssTrueColorMatrix':
        (this.imageFilter as SdssTrueColorMatrixPng).params = params.sdssTrueColorMatrix
        break
    }
    this.params = { ...params }
    this.updateImageCacheSize()
    this.update()
  }

  private async loadMetadata() {
    const tracts = await (await fetch(`${this.baseUrl}/meta.json`)).json()
    if (this.alreadyReleased) {
      return
    }
    this.tracts = []
    this.tractName.clear()
    for (const name of Object.keys(tracts)) {
      const tract = Tract.fromFitsHeader((tracts as any)[name].wcs)
      this.tractName.set(tract, name)
      this.tracts.push(tract)
    }
    this.updateImageCacheSize()
    this.globe.requestRefresh()
  }

  walkTracts(cb: (tract: Tract) => void) {
    for (const t of this.tracts) {
      cb(t)
    }
  }

  private imageUrls(ref: TileRef) {
    return this.params.filters
      .map((f) => `${this.baseUrl}/${f}/${this.tractName.get(ref.tract)}/${ref.level}/${ref.p}/${ref.q}.png`)
  }

  async makeTileTexture(ref: TileRef, { sync, fadeIn }: { fadeIn: boolean, sync: boolean }) {
    const urls = this.imageUrls(ref)
    const revision = this.revision
    const images = await Promise.all(urls.map(url => this.imageCache(url)))
    const tt = new TileTexture(this, { fadeIn, revision })
    const gl = this.globe.gl
    const { tileSize } = ref.tract

    if (!sync) {
      // await waitIdleTime()
    }

    if (this.alreadyReleased) {
      return tt
    }

    wegblProfile(gl, 'imageFilter', () => {
      // this.imageFilter.applyToImages(tt.tex, tileSize, tileSize, images)
      this.imageFilter.apply(tt.tex, tileSize, tileSize, images.length, (tex, index) => {
        tex.bind(() => {
          const image = images[index]
          // const { width, height } = image
          // gl.texStorage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, width, height)
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, gl.LUMINANCE, gl.UNSIGNED_BYTE, image)
        })
      })
    })

    tt.tex.bind(() => {
      if (ref.level === ref.tract.maxTileLevel) {
        gl.generateMipmap(gl.TEXTURE_2D)
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
      }
      if (this.magFilter === 'nearest' && ref.level === 0) {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
      }
    })
    return tt
  }

  setMagFilter(magFilter: MagFilter) {
    this.magFilter = magFilter
    this.update()
  }
}


function expandShader(template: string) {
  const modules = {
    decode_png,
    sdss_true_color,
    simple_rgb,
  } as { [modname: string]: string }
  return template.replace(/^\s*\/\/@import\s+\.\/(.*?);/mg, (_m, mod) => modules[mod])
}


function CachedImageLoader(maxSize = 0) {
  const cache = new Cache<string, ImageLike>({ maxSize })
  const zeroBitmapRequest = create1x1BitmapData()

  const fetch = async (url: string) => {
    const cache_hit = cache.get(url)
    if (cache_hit) {
      return cache_hit
    }
    const failover = await zeroBitmapRequest
    const fresh = await loadImage(url, { failover })
    cache.set(url, fresh)
    return fresh
  }

  return Object.assign(fetch, {
    release: () => cache.clear(),
    setCacheSize: (maxSize: number) => cache.setLimit(maxSize),
  })
}

async function create1x1BitmapData(r = 0, g = 0, b = 0, a = 255) {
  const imageData = new ImageData(1, 1)
  imageData.data[0] = r // R
  imageData.data[1] = g // G
  imageData.data[2] = b // B
  imageData.data[3] = a // A
  const canvas = document.createElement('canvas')
  canvas.width = 1
  canvas.height = 1
  const ctx = nonNull(canvas.getContext('2d'))
  ctx.putImageData(imageData, 0, 0)
  const blob = await new Promise<Blob>(resolve => canvas.toBlob(blob => resolve(blob as Blob)))
  const imageBitmap = await createImageBitmap(blob)
  return imageBitmap
}
