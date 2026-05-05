import { vec4 } from 'gl-matrix'
import { Globe } from '~/globe'
import { SkyCoord } from '~/lib/angle'
import { SinglePointerEvent } from '~/utils/SinglePointerEvent'
import { View } from '~/view'


export class GlobePointerEvent extends SinglePointerEvent {
  readonly coord: SkyCoord

  constructor(e: SinglePointerEvent, readonly globe: Globe, readonly view: View) {
    super(e.e)
    this.coord = globe.canvas.coordFromClientCoord(e)
  }

  offset() {
    const rect = this.globe.canvas.domElement.getBoundingClientRect()
    return {
      x: this.clientX - rect.left,
      y: this.clientY - rect.top,
    }
  }

  coord2offset(coord: SkyCoord): [number, number] {
    // @ts-ignore
    const p = vec4.transformMat4(vec4.create(), [...coord.xyz, 1], this.view.mvp.pv)
    const x = p[0] / p[3]
    const y = p[1] / p[3]
    // const z = p[2] / p[3]
    const rect = this.globe.canvas.domElement.getBoundingClientRect()
    return [
      rect.width * (x + 1) / 2.,
      rect.height * (1 - (y + 1) / 2.),
    ]
  }

  private stopCount = 0

  stopPropagation() {
    ++this.stopCount
  }

  /** @internal */
  get stopped() {
    return this.stopCount > 0
  }
}


export class GlobePointerDragEvent {
  constructor(
    private readonly current: GlobePointerEvent,
    readonly downEvent: GlobePointerEvent,
  ) {

  }

  get coord() {
    return this.current.coord
  }

  get offset() {
    return this.current.offset
  }

  coord2offset(coord: SkyCoord): [number, number] {
    return this.coord2offset(coord)
  }

  stopPropagation() {
    return this.current.stopPropagation()
  }

  /** @internal */
  get stopped() {
    return this.current.stopped
  }

  delta() {
    return {
      x: this.current.clientX - this.downEvent.clientX,
      y: this.current.clientY - this.downEvent.clientY,
    }
  }

  get moved() {
    return !(this.current.clientX === this.downEvent.clientX && this.current.clientY === this.downEvent.clientY)
  }
}
