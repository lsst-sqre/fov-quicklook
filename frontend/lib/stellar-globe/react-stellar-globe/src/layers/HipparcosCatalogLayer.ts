import { HipparcosCatalogLayer } from "@stellar-globe/stellar-globe"
import { makePureLayerComponent, setDisplayName } from "../GlobeContext"

const HipparcosCatalogLayer$ = makePureLayerComponent<{
  visible?: boolean
}>(
  globe => new HipparcosCatalogLayer(globe),
  'visible',
)

setDisplayName({ HipparcosCatalogLayer$ })
export { HipparcosCatalogLayer$ }
