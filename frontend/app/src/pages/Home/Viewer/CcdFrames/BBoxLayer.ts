import { Globe, Layer, path, Tract, V2, V4, View } from "@stellar-globe/stellar-globe"
import { BBox } from "../../../../store/api/openapi"


export class BBoxLayer extends Layer {
  private r: path.Renderer

  constructor(globe: Globe, readonly color: V4) {
    super(globe)
    this.r = new path.Renderer(globe.gl, {
      blendMode: "NORMAL",
      darkenNarrowLine: false,
      minWidth: 3 * globe.camera.pixelRatio,
    })
    this.onRelease(() => this.r.release())
  }

  render(view: View): void {
    this.r.render(view)
  }

  update(bboxes: BBox[], tract: Tract) {
    const { color } = this
    const paths: path.Path[] = [...(function* () {
      for (const b of bboxes) {
        yield* bboxFramePath(b, tract, color)
      }
    })()]
    this.r.setPaths(paths)
    this.globe.requestRefresh()
  }
}


function* bboxCoords(bbox: { minx: number, miny: number, maxx: number, maxy: number }): Generator<V2> {
  yield [bbox.minx, bbox.miny]
  yield [bbox.maxx, bbox.miny]
  yield [bbox.maxx, bbox.maxy]
  yield [bbox.minx, bbox.maxy]
}


function* bboxFramePath(bbox: BBox, tract: Tract, color: V4): Generator<path.Path> {
  yield {
    close: true,
    joint: 'MITER',
    points: [...bboxCoords(bbox)].map(xy => (
      {
        color,
        size: 0,
        position: tract.pixel2xyz(...xy),
      }
    )),
  }
}
