import { Globe } from "~/globe"
import { Layer } from "../layer"
import { V3, V4 } from "~/types"
import { View } from "~/view"
import { BillboardImage, BillboardImageRef, BillboardRenderer } from "~/renderer/billboard_renderer"
import { MarkerType, makeMarkerImageData, markerTypes } from "./marker"
import { PointingObject } from "../layer/PointingObject"
import { GlobePointerEvent } from "../GlobePointerEvent"
import { KdTree } from "~/utils/kd_tree"
import { wegblProfile } from "~/devel/webgl-profiler/utils"


type MarkerRendererOptions = {
  markers: Marker[]
  defaultColor: V4
  defaultType: MarkerType
  markerSize?: number
  markerWidth?: number
}

type MarkerLayerOptions = MarkerRendererOptions & {
  baseColor?: V4
}

type Marker = {
  position: V3
  color?: V4
  type?: MarkerType
}

const defaultMarkerSize = 32


export class MarkerLayer extends Layer {
  private renderer: BillboardRenderer

  constructor(
    globe: Globe,
    private options: MarkerLayerOptions,
  ) {
    super(globe)
    this.renderer = new BillboardRenderer(this.globe.gl)
    this.renderer.color = options.baseColor ?? this.renderer.color
    this.onRelease(() => this.renderer.release())
    this.update(options)
  }

  render(view: View): void {
    this.renderer.render(view)
  }

  update(options: Partial<MarkerRendererOptions>) {
    this.options = { ...this.options, ...options }
    refreshRenderer(this.renderer, this.options)
    this.globe.requestRefresh()
  }

  set baseColor(baseColor: V4 | undefined) {
    this.renderer.color = baseColor ?? [1, 1, 1, 1]
  }
}


type ClickEvent = {
  /**
   * @TJS-type integer
   */
  index: number
}


type HoverChangeEvent = {
  index: number | null
}


type ClickableMarkerLayerOptions = MarkerLayerOptions & {
  dimmAlpha: number
  onClick?: (e: ClickEvent) => void
  onHoverChange?: (e: HoverChangeEvent) => void
}


export class ClickableMarkerLayer extends Layer {
  private baseMarkerRenderer: BillboardRenderer
  private focusedMarkerRenderer: BillboardRenderer
  private pointingObject: MarkerPointingObject

  constructor(
    globe: Globe,
    private options: ClickableMarkerLayerOptions
  ) {
    super(globe)
    this.baseMarkerRenderer = new BillboardRenderer(this.globe.gl)
    this.onRelease(() => this.baseMarkerRenderer.release())
    this.focusedMarkerRenderer = new BillboardRenderer(this.globe.gl)
    this.onRelease(() => this.focusedMarkerRenderer.release())
    this.pointingObjects.push(this.pointingObject = new MarkerPointingObject(() => ({
      layer: this,
      renderer: this.focusedMarkerRenderer,
      options: this.options,
    })))
    this.update(options)
  }

  update(options: Partial<MarkerRendererOptions>) {
    this.options = { ...this.options, ...options }
    refreshRenderer(this.baseMarkerRenderer, this.options)
    this.pointingObject.refresh()
    this.globe.requestRefresh()
  }

  render(view: View): void {
    const gl = this.globe.gl
    wegblProfile(gl, 'ClickableMarker', () => {
      this.baseMarkerRenderer.render(view, this.options.dimmAlpha)
      this.focusedMarkerRenderer.render(view)
    })
  }

  set onClick(handler: ((e: ClickEvent) => void) | undefined) {
    this.options.onClick = handler
  }

  set onHoverChange(handler: ((e: HoverChangeEvent) => void) | undefined) {
    this.options.onHoverChange = handler
  }

  set baseColor(baseColor: V4 | undefined) {
    this.baseMarkerRenderer.color = baseColor ?? [1, 1, 1, 1]
    this.focusedMarkerRenderer.color = baseColor ?? [1, 1, 1, 1]
  }

  set dimmAlpha(dimmAlpha: number) {
    this.options.dimmAlpha = dimmAlpha
    this.globe.requestRefresh()
  }
}


class MarkerPointingObject extends PointingObject {
  private index: KdTree<3, number>

  constructor(
    readonly backdoor: () => {
      layer: ClickableMarkerLayer,
      renderer: BillboardRenderer,
      options: ClickableMarkerLayerOptions,
    },
  ) {
    super()
    this.index = this.rebuildIndex()
  }

  private focusedIndex = -1

  private rebuildIndex() {
    const { options: { markers } } = this.backdoor()
    return this.index = new KdTree(markers.map((_, i) => i), i => markers[i].position)
  }

  refresh() {
    this.focusedIndex = -1
    this.rebuildIndex()
    this.refreshActiveMarkerRenderer()
  }

  private refreshActiveMarkerRenderer() {
    const { options, layer, renderer } = this.backdoor()
    const { markers } = options
    refreshRenderer(renderer, { ...options, markers: this.focusedIndex >= 0 ? [markers[this.focusedIndex]] : [] })
    layer.globe.requestRefresh()
  }

  protected onClick(_e: GlobePointerEvent): void {
    const { options: { onClick } } = this.backdoor()
    if (onClick && this.focusedIndex >= 0) {
      onClick({ index: this.focusedIndex })
    }
  }

  hit(e: GlobePointerEvent): { hit: boolean; passThrough: boolean } {
    const { layer, options } = this.backdoor()
    const markerSize = (options.markerSize ?? defaultMarkerSize) * layer.globe.camera.pixelRatio
    const fovy = layer.globe.camera.fovy
    const h = layer.globe.canvas.domElement.height
    // 画面上の markerSize は天球上のどれだけの距離か
    const hitRadius = fovy * markerSize / h
    const hits = this.index.nearest(e.coord.xyz, 1, hitRadius)
    const lastFocusedMarker = this.focusedIndex
    this.focusedIndex = hits.length > 0 ? hits[0] : -1
    if (lastFocusedMarker !== this.focusedIndex) {
      this.refreshActiveMarkerRenderer()
      const { options: { onHoverChange } } = this.backdoor()
      onHoverChange?.({ index: this.focusedIndex >= 0 ? this.focusedIndex : null })
    }
    return {
      hit: this.focusedIndex >= 0,
      passThrough: true,
    }
  }
}


function refreshRenderer(
  renderer: BillboardRenderer,
  options: MarkerRendererOptions,
) {
  const { markers, defaultColor, defaultType } = options
  const imageId = Object.fromEntries(markerTypes.map((type, i) => [type, i]))
  const imageRefs: BillboardImageRef[] = markers.map(({ position, color, type }) => {
    return {
      position,
      imageID: imageId[type ?? defaultType],
      color: color ?? defaultColor,
    }
  })
  const images: BillboardImage[] = markerTypes.map(type => ({
    imageData: makeMarkerImageData(type, {
      size: options.markerSize ?? defaultMarkerSize,
      width: options.markerWidth ?? 0.2,
    }),
    origin: [0, 0],
  }))
  renderer.buildArray(images, imageRefs)
}
