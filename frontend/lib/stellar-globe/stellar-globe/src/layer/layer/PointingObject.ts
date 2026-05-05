import { Inertia2D } from "~/lib/inertia"
import { CursorStyle, Globe } from "~/globe"
import { Animation, AnimationCallback } from "~/globe/animation"
import { GlobePointerDragEvent, GlobePointerEvent } from "~/layer/GlobePointerEvent"


type HitResult = {
  hit: boolean
  passThrough: boolean
}


export abstract class PointingObject {
  abstract hit(e: GlobePointerEvent): HitResult
  protected onPointerDown(e: GlobePointerEvent) { e }
  protected onDrag(e: GlobePointerDragEvent) { e }
  protected onPointerUp(e: GlobePointerDragEvent) { e }
  protected onClick(e: GlobePointerEvent) { e }
  protected onContextMenu(e: GlobePointerEvent) { e }
  protected onMove(e: GlobePointerEvent) { e }
  protected onHover(e: GlobePointerEvent) { e }
  protected onEnter(e: GlobePointerEvent) { e }
  protected onLeave(e: GlobePointerEvent) { e }
  private hovering = false;

  /** @internal */
  runHover(e: GlobePointerEvent) {
    const hitResult = this.hit(e)
    const { hit } = hitResult
    this.onHover(e)
    if (this.hovering !== hit) {
      this.hovering = hit
      if (hit) {
        this.onEnter(e)
      } else {
        this.onLeave(e)
      }
    }
    return hitResult
  }

  /** @internal */
  runOnClick(...args: Parameters<PointingObject["onClick"]>) { return this.onClick(...args) }

  /** @internal */
  runOnContextMenu(...args: Parameters<PointingObject["onContextMenu"]>) { return this.onContextMenu(...args) }

  /** @internal */
  runOnPointerUp(...args: Parameters<PointingObject["onPointerUp"]>) { return this.onPointerUp(...args) }

  /** @internal */
  runOnPointerDown(...args: Parameters<PointingObject["onPointerDown"]>) { return this.onPointerDown(...args) }

  /** @internal */
  runOnDrag(...args: Parameters<PointingObject["onDrag"]>) { return this.onDrag(...args) }

  hoverIcon(_e: GlobePointerEvent): CursorStyle {
    return 'default'
  }

  dragIcon(_e: GlobePointerEvent): CursorStyle {
    return 'default'
  }

  get dragDetectionDelay() {
    return 100
  }
}


export abstract class InertialPointingObject extends PointingObject {
  private animation?: Animation

  constructor(
    protected readonly globe: Globe,
    protected readonly inertia: Inertia2D,
    private readonly cameraMotion = false
  ) {
    super()
  }

  protected onPointerDown(e: GlobePointerEvent): void {
    this.inertia.reset()
    this.onInertialPointerDown(e)
  }

  protected onPointerUp(): void {
    this.inertia.release()
  }

  protected onDrag(e: GlobePointerDragEvent): void {
    if (this.animation === undefined) {
      this.animation = this.globe.animations.add(animationArgs => {
        this.onInertiaMove(animationArgs)
        this.inertia.evolve(animationArgs.T)
        const { moving } = this.inertia.state
        if (!moving) {
          this.animation?.stop()
        }
      }, { cameraMotion: this.cameraMotion })
      this.animation.then(() => {
        this.animation = undefined
      })
    }
    const d = e.delta()
    this.inertia.dragTo(d.x, d.y)
  }

  protected onInertiaMove(animationArgs: AnimationCallback) {
    animationArgs
  }

  protected onInertialPointerDown(e: GlobePointerEvent) {
    e
  }

  protected onInertiaMoveEnd() {
  }
}


export type PointingObjectDef = {
  hit: (e: GlobePointerEvent) => { hit: boolean, passThrough?: boolean }
  onPointerDown?: (e: GlobePointerEvent) => {
    onDrag?: (e: GlobePointerDragEvent) => void
    onPointerUp?: (e: GlobePointerDragEvent) => void
  } | void,
  onContextMenu?: (e: GlobePointerEvent) => void
  onClick?: (e: GlobePointerEvent) => void
  hoverIcon?: CursorStyle | ((e: GlobePointerEvent) => CursorStyle)
  dragIcon?: CursorStyle | ((e: GlobePointerEvent) => CursorStyle)
  dragDetectiveDelay?: number
}


export function makePointingObject(def: PointingObjectDef): PointingObject {
  return new class extends PointingObject {
    hoverIcon(e: GlobePointerEvent): CursorStyle {
      return typeof def.hoverIcon === 'function' ? def.hoverIcon(e) : def.hoverIcon ?? 'default'
    }

    dragIcon(e: GlobePointerEvent): CursorStyle {
      return typeof def.dragIcon === 'function' ? def.dragIcon(e) : def.dragIcon ?? 'default'
    }

    hit(e: GlobePointerEvent): { hit: boolean; passThrough: boolean } {
      const { hit, passThrough } = def.hit(e)
      return { hit, passThrough: passThrough ?? false }
    }

    private _onDrag?: PointingObject["onDrag"]
    private _onPointerUp?: PointingObject["onPointerUp"]

    protected onPointerDown(e: GlobePointerEvent): void {
      const { onDrag: drag, onPointerUp: pointerUp } = def.onPointerDown?.(e) ?? {}
      this._onDrag = drag
      this._onPointerUp = pointerUp
    }

    protected onDrag(e: GlobePointerDragEvent): void {
      this._onDrag?.(e)
    }

    protected onPointerUp(e: GlobePointerDragEvent): void {
      this._onPointerUp?.(e)
    }

    protected onContextMenu(e: GlobePointerEvent): void {
      def.onContextMenu?.(e)
    }

    protected onClick(e: GlobePointerEvent): void {
      def.onClick?.(e)
    }
  }
}
