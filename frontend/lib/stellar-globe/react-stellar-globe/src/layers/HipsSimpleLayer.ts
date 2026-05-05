import { hips } from "@stellar-globe/stellar-globe"
import { makePureLayerComponent, setDisplayName } from "../GlobeContext"


const HipsSimpleLayer$ = makePureLayerComponent<{
  visible?: boolean,
  baseUrl: string,
  animationLod?: number,
}>(
  (globe, { baseUrl, animationLod }) => new hips.SimpleImageLayer(globe, baseUrl, { animationLod }),
  'visible',
)


setDisplayName({ HipsSimpleLayer$ })
export { HipsSimpleLayer$ }
