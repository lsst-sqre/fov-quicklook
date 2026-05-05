import { Inertia2D } from '~/lib/inertia'
import { mat2, vec2 } from 'gl-matrix'
import { Globe } from "~/globe"
import { AnimationCallback } from "~/globe/animation"
import { on } from '~/utils/event'
import { clip } from "~/utils/math"
import { mouse } from '~/utils/mouse'
import { GlobePointerEvent } from "./GlobePointerEvent"
import { Layer } from "./layer"
import { InertialPointingObject } from './layer/PointingObject'


const EPSILON = (1 / 3600) / 180 * Math.PI


class PanPointingObject extends InertialPointingObject {
  private fovy0: number
  private J = mat2.create() // matrix for dx,dy -> d_theta, d_phi

  constructor(
    globe: Globe,
    inertia: Inertia2D,
  ) {
    super(globe, inertia, true)
    this.fovy0 = this.globe.camera.fovy
  }

  hit(e: GlobePointerEvent) {
    return {
      passThrough: false,
      hit: e.originalEvent({
        mouse: me => mouse.button(me) === mouse.Button.LEFT,
        touch: () => true,
      }) ?? false
    }
  }

  protected onInertialPointerDown(e: GlobePointerEvent): void {
    const canvas = this.globe.canvas
    const { x, y } = e.offset()
    const camera = this.globe.camera
    const c0 = camera.coord2thetaphi(canvas.coordFromOffset(x, y))
    const cx = camera.coord2thetaphi(canvas.coordFromOffset(x + 1, y)) // d{t,p} / dx
    const cy = camera.coord2thetaphi(canvas.coordFromOffset(x, y + 1)) // d{t,p} / dy
    if (Math.abs(c0[1] - cx[1]) > Math.PI) {
      cx[1] += (cx[1] > c0[1] ? -1 : +1) * 2 * Math.PI
    }
    if (Math.abs(c0[1] - cy[1]) > Math.PI) {
      cy[1] += (cy[1] > c0[1] ? -1 : +1) * 2 * Math.PI
    }
    const dt_dx = cx[0] - c0[0]
    const dt_dy = cy[0] - c0[0]
    const dp_dx = cx[1] - c0[1]
    const dp_dy = cy[1] - c0[1]
    mat2.set(this.J,
      dp_dx, dt_dx,
      dp_dy, dt_dy,
    )
    // console.log(c0[0] / Math.PI, c0[1] / Math.PI)
    // console.log(this.J.map(c => c / Math.sqrt(mat2.determinant(this.J))))
    this.fovy0 = this.globe.camera.fovy
  }

  protected onInertiaMove({ dt }: AnimationCallback) {
    const { velocity: { x: vx, y: vy } } = this.inertia.state
    const dCoord = vec2.transformMat2(vec2.create(), [dt * vx, dt * vy], this.J)
    const camera = this.globe.camera
    const scale = Math.min(this.globe.camera.fovy / this.fovy0, 1)
    camera.phi -= scale * dCoord[0]
    camera.theta -= scale * dCoord[1]
    camera.theta = clip(camera.theta, -Math.PI / 2 + EPSILON, Math.PI / 2 - EPSILON)
  }

  get dragDetectionDelay() {
    return 0
  }
}


export class PanLayer extends Layer {
  constructor(
    globe: Globe,
  ) {
    super(globe)
    this.pointingObjects.push(new PanPointingObject(globe, new Inertia2D({
      omega0: 5.e-2,
      gamma: 4.e-2,
      gamma0: 1.e-3,
    })))
  }

  protected onAddToGlobe() {
    const el = this.globe.containerElement
    const offDblclick = on(el, 'dblclick', (e: MouseEvent) => {
      e.preventDefault()
      const coord = this.globe.canvas.coordFromClientCoord(e)
      const [theta, phi] = this.globe.camera.coord2thetaphi(coord)
      this.globe.camera.jumpTo({ theta, phi })
    })
    this.onRemoveFromGlobe(offDblclick)
  }
}
