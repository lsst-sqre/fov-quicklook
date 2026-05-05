import { useAppSelector } from "../../store/hooks"
import { FitsImageLayer$ } from "./FitsMaskImageLayer/react"

export function FitsImageLayers() {
  const images = useAppSelector(state => state.fitsImage.images)

  return images.map(image => (
    <FitsImageLayer$ key={image.id} url={image.url} color={image.maskConfig.color} maskBit={image.maskConfig.maskBit} />
  ))
}
