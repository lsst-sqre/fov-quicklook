import { GlobePointerEvent } from "~/layer/GlobePointerEvent"
import { CameraMode, Layer } from ".."
import { Camera } from "./Camera"

export interface GlobeEventMap {
  'camera-move-start': CameraMoveEvent
  'camera-move-end': CameraMoveEvent
  'camera-move': CameraMoveEvent
  'camera-mode-change': CameraModeChangeEvent
  'pointer-down': GlobePointerEvent
  'pointer-move': GlobePointerEvent
  'pointer-up': GlobePointerEvent
  'layer-change': LayerChangeEvent
  'imageloadend': ImageLoadEvent
  'hips-shiftmap-worker-start': {}
  'hips-shiftmap-worker-end': {}
  'resize': GlobeResizeEvent
}

type CameraMoveEvent = ReturnType<typeof cameraToCameraMoveEvent>

type CameraModeChangeEvent = {
  mode: CameraMode
}

type LayerChangeEvent = {
  added?: Layer[]
  removed?: Layer[]
}
type ImageLoadEvent = {}
type GlobeResizeEvent = {}


export function cameraToCameraMoveEvent(camera: Camera) {
  return { camera }
}
