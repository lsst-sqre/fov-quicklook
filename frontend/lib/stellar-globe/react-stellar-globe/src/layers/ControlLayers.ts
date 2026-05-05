import { PanLayer, RollLayer, TouchLayer, ZoomLayer } from "@stellar-globe/stellar-globe"
import { makePureLayerComponent, setDisplayName } from "../GlobeContext"

const PanLayer$ = makePureLayerComponent<{ enabled?: boolean }>(globe => new PanLayer(globe), 'enabled')
const ZoomLayer$ = makePureLayerComponent<{ enabled?: boolean }>(globe => new ZoomLayer(globe), 'enabled')
const RollLayer$ = makePureLayerComponent<{ enabled?: boolean }>(globe => new RollLayer(globe), 'enabled')
const TouchLayer$ = makePureLayerComponent<{ enabled?: boolean }>(globe => new TouchLayer(globe), 'enabled')

setDisplayName({ PanLayer$, ZoomLayer$, RollLayer$, TouchLayer$ })

export { PanLayer$, ZoomLayer$, RollLayer$, TouchLayer$ }
