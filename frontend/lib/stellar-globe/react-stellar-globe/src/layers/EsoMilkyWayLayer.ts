import { EsoMilkyWayLayer } from "@stellar-globe/stellar-globe"
import { makePureLayerComponent, setDisplayName } from "../GlobeContext"

const EsoMilkyWayLayer$ = makePureLayerComponent<
  ConstructorParameters<typeof EsoMilkyWayLayer>[1] &
  { visible?: boolean }
>((globe, options) => new EsoMilkyWayLayer(globe, options), 'visible')

setDisplayName({ EsoMilkyWayLayer$ })

export { EsoMilkyWayLayer$ }
