import { Inertia } from '~/lib/inertia'
import { WheelEventNormalizer } from '~/lib/wheel-event-normalizer'
import { vec3 } from 'gl-matrix'
import { Animation } from "~/globe/animation"
import { SkyCoord } from "~/lib/angle"
import { V3 } from '~/types'
import { SinglePointerEvent } from '~/utils/SinglePointerEvent'
import { on } from "~/utils/event"
import { clip, dot } from '~/utils/math'
import { Layer } from "./layer"


export class ZoomLayer extends Layer {
  private inertia = new Inertia({
    gamma: 1.e-1, // ドラッグ中の抵抗
    gamma0: 1.e-1, // ドラッグ後の抵抗
    omega0: 2., // バネの強さ
    minSpeed: 1.e-4, // これより速度が落ちると止まったとみなす
  })

  protected onAddToGlobe() {
    let animation: Animation | undefined = undefined
    const domElement = this.globe.containerElement

    const wheelEventNormalizer = new WheelEventNormalizer(e => {
      this.inertia.dragTo(e.deltaY)
      if (animation === undefined) {
        animation = this.globe.animations.add(({ T, dt }) => {
          this.inertia.evolve(T)
          if (!this.inertia.state.moving) {
            animation?.stop()
          }
          this.zoomStep(this.globe.canvas.xyzFromClientCoord(wheelEventNormalizer.lastRawEvent), dt)
        }, { cameraMotion: true })
        animation!.then(() => {
          animation = undefined
          wheelEventNormalizer.stop()
        })
      }
    }, {
      inertia: new Inertia({ gamma0: 2.e-3, omega0: 1.e-0, minSpeed: 1.e-4 }),
      hotDuration: 150,
    })

    const offWheel = on(domElement, 'wheel', rawEvent => {
      rawEvent.preventDefault()
      wheelEventNormalizer.feedRawEvent(rawEvent)
    }, { passive: false })
    this.onRemoveFromGlobe(offWheel)

    const offDown = SinglePointerEvent.onDown(domElement, () => {
      animation?.stop()
    })
    this.onRemoveFromGlobe(offDown)
  }

  private zoomStep(targetXyz: V3, dt: number) {
    const { x: zoomSpeed } = this.inertia.state
    const k = 2.e-5
    const camera = this.globe.camera
    const dScale = Math.exp(k * dt * zoomSpeed)
    const pole = camera.thetaphi2xyz(Math.PI / 2, 0)
    const centerXyz = camera.thetaphi2xyz(camera.theta, camera.phi)
    let [x1, y1, z1] = centerXyz
    const [x2, y2, z2] = targetXyz
    let dx = (1 - dScale) * (x2 - x1)
    let dy = (1 - dScale) * (y2 - y1)
    let dz = (1 - dScale) * (z2 - z1)
    // A: center - O - pole
    const cosA = dot(pole, centerXyz)
    const tanA = Math.sqrt(1 / (cosA * cosA) - 1)
    const r = clip(tanA / camera.fovy - 0.1, 0, 1)
    dx = r * dx + (1 - r) * x1
    dy = r * dy + (1 - r) * y1
    dz = r * dz + (1 - r) * z1
    if (vec3.angle([x1, y1, z1], pole) >= 1.e-1 * camera.fovy) {
      x1 += dx
      y1 += dy
      z1 += dz
    }
    const coord = SkyCoord.fromXyz([x1, y1, z1])
    const [theta, phi] = camera.coord2thetaphi(coord)
    camera.theta = theta
    camera.phi = phi
    camera.fovy *= dScale
    camera.cage()
  }
}