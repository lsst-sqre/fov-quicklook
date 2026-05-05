import { Inertia2D } from "~/lib/inertia"
import { Globe } from "~/globe"
import { AnimationCallback } from "~/globe/animation"
import { mouse } from '~/utils/mouse'
import { GlobePointerEvent } from "./GlobePointerEvent"
import { Layer } from "./layer"
import { InertialPointingObject } from "./layer/PointingObject"


class RollPointingObject extends InertialPointingObject {
  hit(e: GlobePointerEvent) {
    return {
      passThrough: false,
      hit: e.originalEvent({
        mouse: me => mouse.button(me) === mouse.Button.MIDDLE,
      }) ?? false
    }
  }

  private offset = { x: NaN, y: NaN }

  protected onInertialPointerDown(e: GlobePointerEvent): void {
    const { x, y } = e.offset()
    this.offset.x = x
    this.offset.y = y
  }

  protected onInertiaMove({ dt }: AnimationCallback): void {
    let { position: { x, y }, velocity: { x: vx, y: vy } } = this.inertia.state
    x += this.offset.x
    y += this.offset.y
    const dx = dt * vx
    const dy = dt * vy
    const canvas = this.globe.canvas.domElement
    y -= canvas.clientHeight / 2
    x -= canvas.clientWidth / 2
    if (x !== 0 && y !== 0) {
      this.globe.camera.roll += (y * dx - x * dy) / (x * x + y * y)
    }
  }

  get dragDetectionDelay() {
    return 0
  }
}


export class RollLayer extends Layer {
  constructor(
    globe: Globe,
  ) {
    super(globe)
    this.pointingObjects.push(new RollPointingObject(globe, new Inertia2D()))
  }
}
