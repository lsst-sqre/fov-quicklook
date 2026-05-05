import { View } from ".."
import { clip } from '~/utils/math'

const overlayAlphaStart = 0.1
const overlayAlphaGradient = 4

export function baseAlpha(view: View) {
  return 1 - overlayAlpha(view)
}

export function overlayAlpha(view: View) {
  const b = overlayAlphaStart
  const a = overlayAlphaGradient
  return clip((view.mvp.arc - b) * a, 0, 1)
}