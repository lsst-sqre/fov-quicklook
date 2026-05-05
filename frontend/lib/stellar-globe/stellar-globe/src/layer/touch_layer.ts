import { Globe } from '~/globe'
import { ClientCoord } from '~/globe/canvas'
import { SkyCoord } from '~/lib/angle'
import Hammer from '~/utils/TinyHammer'
import { Layer } from './layer'


export class TouchLayer extends Layer {
  private mc!: Hammer

  constructor(
    globe: Globe,
  ) {
    super(globe)
    this.mc = new Hammer(this.globe.canvas.domElement)
    this.setupPinch()
    this.setupDoubleTap()
    this.setupTap2()
    this.onRelease(() => {
      this.mc.destroy()
    })
  }

  private setupDoubleTap() {
    this.mc.get('doubletap').set({ posThreshold: 30 })
    this.mc.on('doubletap', (e) => {
      if (e.pointerType === 'touch') {
        const { x: clientX, y: clientY } = e.center
        const { theta, phi, fovy } = zoomOnClientCoord(this.globe, 0.5, { clientX, clientY })
        this.globe.camera.jumpTo({ theta, phi, fovy })
        this.globe.requestRefresh()
      }
    })
  }

  private setupTap2() {
    // this.mc.add(new Hammer.Tap({ event: 'tap2', pointers: 2 }))
    // TinyHammer では tap2 はaddせずに使える
    this.mc.on('tap2', () => {
      const camera = this.globe.camera
      camera.jumpTo({ fovy: camera.fovy * 2 })
    })
  }

  private setupPinch() {
    // this.mc.get('pinch').set({ enable: true })
    // TinyHammer では pinch は enable せずに使える
    let scale = 1
    
    this.mc.on('pinchstart', () => {
      scale = 1
    })

    this.mc.on('pinchmove', (e) => {
      const { x: clientX, y: clientY } = e.center
      const { theta, phi, fovy } = zoomOnClientCoord(this.globe, scale / e.scale, { clientX, clientY })
      const camera = this.globe.camera
      scale = e.scale
      camera.theta = theta
      camera.phi = phi
      camera.fovy = fovy
      camera.cage()
      this.globe.requestRefresh()
    })
  }
}

function zoomOnClientCoord(globe: Globe, dScale: number, clinentCoord: ClientCoord) {
  const canvas = globe.canvas
  const camera = globe.camera
  const centerXyz = camera.thetaphi2xyz(camera.theta, camera.phi)
  const targetXyz = canvas.xyzFromClientCoord(clinentCoord)
  let [x1, y1, z1] = centerXyz
  const [x2, y2, z2] = targetXyz
  let dx = (1 - dScale) * (x2 - x1)
  let dy = (1 - dScale) * (y2 - y1)
  let dz = (1 - dScale) * (z2 - z1)
  x1 += dx
  y1 += dy
  z1 += dz
  const coord = SkyCoord.fromXyz([x1, y1, z1])
  const [theta, phi] = camera.coord2thetaphi(coord)
  return {
    theta,
    phi,
    fovy: camera.fovy * dScale,
  }
}
