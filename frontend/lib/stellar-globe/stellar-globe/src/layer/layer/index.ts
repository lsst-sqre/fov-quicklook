import { Globe } from "~/globe"
import { AnimationManager } from "~/globe/animation"
import { ReleaseCallbacks } from "~/utils/EventManager"
import { View } from "~/view"
import { PointingObject } from "./PointingObject"


export class Layer {
  constructor(
    readonly globe: Globe,
  ) {
  }

  // @ts-ignore
  render(view: View) {
    // will be implemented in subclass
  }

  release() {
    this.globe.removeLayer(this) // if globe does not have this layer, this does nothing.
    this.releaseCallbacks.flush()
  }

  addAnimation(...args: Parameters<AnimationManager["add"]>) {
    const a = this.globe.animations.add(...args)
    a.finally(this.onRelease(a.stop))
    return a
  }

  private releaseCallbacks = ReleaseCallbacks()
  protected onRelease = this.releaseCallbacks.add

  protected onAddToGlobe() {
    // will be implemented in subclass
  }

  /** @internal */
  runOnAddToGlobeCallbacks() {
    this.onAddToGlobe()
  }

  private onRemoveFromGlobeCallbacks = ReleaseCallbacks()
  protected onRemoveFromGlobe = this.onRemoveFromGlobeCallbacks.add
  /** @internal */
  runRemoveFromGlobeCallbacks() {
    this.onRemoveFromGlobeCallbacks.flush()
  }

  pointingObjects: PointingObject[] = []
}
