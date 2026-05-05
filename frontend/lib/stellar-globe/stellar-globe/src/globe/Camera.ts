import { mat4, vec3 } from 'gl-matrix'
import { SkyCoord, asec2rad, deg2rad, wrapTo2Pi } from "~/lib/angle"
import * as easing from '~/lib/easing'
import { V3 } from "~/types"
import { thetaphi2xyz, xyz2thetaphi } from '~/utils/math'
import { composite, izenith3, izenith4, mulZenith4, zenith3 } from "~/utils/matrilx-utils"
import { View } from "~/view"
import { MvpMatrix } from "~/view/MvpMatrix"
import { Globe } from "."
import { Animation } from "./animation"

export type CameraMode = 'GNOMONIC' | 'STEREOGRAPHIC' | 'FLOATING_EYE'

export type CameraParams = {
  aspectRatio: number
  fovy: number
  mode: CameraMode
  theta: number,
  phi: number,
  roll: number,
  za: number, // zenith alpha
  zd: number, // zenith delta
  zp: number, // rotation angle around zenith pole
}

type JumpToOptions = {
  duration: number
  easingFunction: typeof easing.fastStart4
  coord: SkyCoord
  keepFovy: boolean
}


type CameraOptions = Partial<CameraParams> & {
  retina?: boolean
  lodBias?: number
}


export class Camera implements CameraParams {
  aspectRatio = -1
  mode: CameraMode = 'STEREOGRAPHIC'

  theta = 0
  phi = 0
  fovy = deg2rad(45)
  roll = 0
  lodBias = 0

  za = 0
  zd = Math.PI / 2
  zp = 0

  min_fovy = asec2rad(5)
  max_fovy = 4

  // Apple製品でcanvas内の解像度を２倍にする。
  // この設定を変えてもサイズや太さが変わるのではなく、ぼやけたりくっきりするだけ。
  retina = true

  constructor(
    private globe: Globe,
    options: CameraOptions = {},
  ) {
    const keys: (keyof typeof options & keyof typeof this)[] = ['aspectRatio', 'fovy', 'lodBias', 'mode', 'phi', 'retina', 'roll', 'theta', 'za', 'zd', 'zp']
    for (const k of keys) {
      const v = options[k]
      if (v !== undefined) {
        // @ts-ignore
        this[k] = options[k]
      }
    }
    this.setLodHooks()
  }

  coord2thetaphi(coord: SkyCoord) {
    const v = vec3.transformMat3(vec3.create(), coord.xyz, zenith3(this.za, this.zd, this.zp))
    return xyz2thetaphi(v[0], v[1], v[2])
  }

  xyz2thetaphi(v: V3) {
    return this.coord2thetaphi(SkyCoord.fromXyz(v))
  }

  thetaphi2xyz(theta: number, phi: number) {
    return vec3.transformMat3([0, 0, 0], thetaphi2xyz(theta, phi), izenith3(this.za, this.zd, this.zp)) as V3
  }

  center() {
    return cameraCenter(this)
  }

  jumpTo(params2: Partial<CameraParams>, options: Partial<JumpToOptions> = {}) {
    const duration = options.duration ?? 400
    const easingFunction = options.easingFunction || easing.fastStart4

    this.globe.animations.stopCameraMotion()

    const p1: CameraParams = {
      aspectRatio: this.aspectRatio,
      theta: this.theta,
      phi: this.phi,
      fovy: this.fovy,
      roll: this.roll,
      mode: this.mode,
      za: this.za,
      zd: this.zd,
      zp: this.zp,
    }

    const p2 = { ...p1 }
    for (const [k, v] of Object.entries(params2)) {
      if (v !== undefined) {
        // @ts-ignore
        p2[k] = v
      }
    }

    if (options.coord) {
      const v = vec3.transformMat3(vec3.create(), options.coord.xyz, zenith3(p2.za, p2.zd, p2.zp));
      [p2.theta, p2.phi] = xyz2thetaphi(v[0], v[1], v[2])
    }

    p1.mode !== p2.mode && this.changeMode(p2.mode, duration)

    p1.phi = wrapTo2Pi(p1.phi)
    if (Math.abs(p1.phi - p2.phi) > Math.PI) {
      if (p1.phi > p2.phi) {
        p2.phi += 2 * Math.PI
      } else {
        p1.phi += 2 * Math.PI
      }
    }

    p1.za = wrapTo2Pi(p1.za)
    p2.za = wrapTo2Pi(p2.za)
    if (Math.abs(p1.za - p2.za) > Math.PI) {
      if (p1.za > p2.za) {
        p2.za += 2 * Math.PI
      } else {
        p1.za += 2 * Math.PI
      }
    }

    const distance = vec3.distance(thetaphi2xyz(p1.theta, p1.phi), thetaphi2xyz(p2.theta, p2.phi))

    return this.globe.animations.add(({ r: ratio }) => {
      const r = easingFunction(ratio)
      this.phi = r * p2.phi + (1 - r) * p1.phi
      this.theta = r * p2.theta + (1 - r) * p1.theta
      const f = 1 - (2 * (r - 0.5)) ** 2
      this.fovy = options.keepFovy ?
        (1 - r) * p1.fovy + r * p2.fovy : f * Math.max(distance - 2 * p1.fovy, 0) + (1 - r) * p1.fovy + r * p2.fovy
      this.roll = (1 - r) * p1.roll + r * p2.roll
      this.za = (1 - r) * p1.za + r * p2.za
      this.zd = (1 - r) * p1.zd + r * p2.zd
      this.zp = (1 - r) * p1.zp + r * p2.zp
    }, { duration, cameraMotion: true })
  }

  private modeTransitionPv?: mat4

  view(): View {
    return {
      mvp: new MvpMatrix(this.modeTransitionPv ?? this.pv()),
      lodBias: this.lodBias,
      pixelRatio: this.pixelRatio,
      drawingBufferHeight: this.globe.gl.drawingBufferHeight,
    }
  }

  private customPvMatrix?: (p: CameraParams) => mat4
  private pv(mode = this.mode) {
    return (this.customPvMatrix || cameraMatrix)({
      aspectRatio: this.aspectRatio,
      theta: this.theta,
      phi: this.phi,
      fovy: this.fovy,
      roll: this.roll,
      mode,
      za: this.za,
      zd: this.zd,
      zp: this.zp,
    })
  }

  private modeAnimation?: Animation
  changeMode(mode: CameraMode, duration = 200) {
    this.globe.emit('camera-mode-change', { mode })
    const oldMode = this.mode
    this.modeAnimation && this.modeAnimation.stop()
    this.mode = mode
    this.modeAnimation = this.globe.animations.add(({ r }) => {
      r = easing.fastStart4(r)
      // @ts-ignore
      this.modeTransitionPv = composite([1 - r, r], [this.pv(oldMode), this.pv()]) as mat4
    }, { duration, immediate: true, cameraMotion: true })
    this.modeAnimation.then(() => {
      this.modeAnimation = undefined
      this.modeTransitionPv = undefined
    })
  }

  private cageAnimation?: Animation
  /** @internal */
  cage() {
    const { min_fovy: MIN_FOVY, max_fovy: MAX_FOVY } = this
    if (this.cageAnimation === undefined && (this.fovy < MIN_FOVY || MAX_FOVY < this.fovy)) {
      this.cageAnimation = this.globe.animations.add(({ dt }) => {
        if (MIN_FOVY <= this.fovy && this.fovy <= MAX_FOVY) {
          this.cageAnimation!.stop()
          return
        }
        const k = 5.e-3
        const base = this.fovy > MAX_FOVY ? MAX_FOVY : MIN_FOVY
        let d = Math.log(this.fovy / base)
        d += (d < 0 ? -1 : 1) * 1.e-3
        this.fovy *= Math.exp(-k * dt * d)
      }, { cameraMotion: true })
      this.cageAnimation.then(() => this.cageAnimation = undefined)
    }
  }

  izenith() {
    return izenith4(this.za, this.zd, this.zp)
  }

  private lodAnimation?: Animation
  private setLodHooks() {
    this.globe.on('camera-move-start', () => {
      if (this.lodAnimation) {
        this.lodAnimation.stop()
      }
      this.lodBias = 1
    })
    this.globe.on('camera-move-end', () => {
      this.lodAnimation = this.globe.animations.add(
        ({ r }) => this.lodBias = 1 - r,
        { duration: 200 },
      )
      this.lodAnimation.then(() => {
        this.lodAnimation = undefined
      })
    })
  }

  setRetina(retina: boolean) {
    this.retina = retina
    this.globe.resize()
    this.globe.requestRefresh()
  }

  get pixelRatio() {
    return this.retina ? window.devicePixelRatio : 1
  }
}

function cameraMatrix(p: CameraParams) {
  const out = mat4.create()
  generateCameraMatrix(out, p)
  mulZenith4(out, p.za, p.zd, p.zp)
  return out
}

function generateCameraMatrix(out: mat4, p: CameraParams) {
  const halfFovy = p.fovy / 2
  const ar = p.aspectRatio
  const cA = Math.cos(p.phi)
  const sA = Math.sin(p.phi)
  const cD = Math.cos(p.theta)
  const sD = Math.sin(p.theta)
  const sR = Math.sin(p.roll)
  const cR = Math.cos(p.roll)
  switch (p.mode) {
    case 'GNOMONIC':
      mat4.set(out,
        (cA * sD * sR + cR * sA) / (ar * halfFovy), (-cA * cR * sD + sA * sR) / halfFovy, 41 * cA * cD / 39, cA * cD,
        (-cA * cR + sA * sD * sR) / (ar * halfFovy), -(cA * sR + cR * sA * sD) / halfFovy, 41 * cD * sA / 39, cD * sA,
        -cD * sR / (ar * halfFovy), cD * cR / halfFovy, 41 * sD / 39, sD,
        0, 0, -4 / 39, 0)
      break
    case 'STEREOGRAPHIC':
      mat4.set(out,
        2 * (cA * sD * sR + cR * sA) / (ar * halfFovy), 2 * (-cA * cR * sD + sA * sR) / halfFovy, 13 * cA * cD / 11, cA * cD,
        // tslint:disable-next-line:max-line-length
        2 * (-cA * cR + sA * sD * sR) / (ar * halfFovy), -(2 * cA * sR + 2 * cR * sA * sD) / halfFovy, 13 * cD * sA / 11, cD * sA,
        -2 * cD * sR / (ar * halfFovy), 2 * cD * cR / halfFovy, 13 * sD / 11, sD,
        0, 0, 7 / 11, 1)
      break
    case 'FLOATING_EYE':
      mat4.set(out,
        // tslint:disable-next-line:max-line-length
        (halfFovy + 1) * (cA * sD * sR + cR * sA) / (ar * halfFovy), (halfFovy + 1) * (-cA * cR * sD + sA * sR) / halfFovy, 41 * cA * cD / 39, cA * cD,
        // tslint:disable-next-line:max-line-length
        (halfFovy + 1) * (-cA * cR + sA * sD * sR) / (ar * halfFovy), -(halfFovy + 1) * (cA * sR + cR * sA * sD) / halfFovy, 41 * cD * sA / 39, cD * sA,
        -cD * sR * (halfFovy + 1) / (ar * halfFovy), cD * cR * (halfFovy + 1) / halfFovy, 41 * sD / 39, sD,
        0, 0, 41 * halfFovy / 39 - 20 / 39, halfFovy,
      )
      break
  }
}


export function cameraCenter(params: Pick<CameraParams, 'theta' | 'phi' | 'za' | 'zd' | 'zp'>) {
  const { theta, phi, za, zd, zp } = params
  const xyz = vec3.transformMat3([0, 0, 0], thetaphi2xyz(theta, phi), izenith3(za, zd, zp)) as V3
  return SkyCoord.fromXyz(xyz)
}
