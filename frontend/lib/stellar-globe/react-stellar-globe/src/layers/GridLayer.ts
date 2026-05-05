import { GridLayer } from "@stellar-globe/stellar-globe"
import { makePureLayerComponent, setDisplayName } from "../GlobeContext"

type GridLayerOptionsManipulator = ConstructorParameters<typeof GridLayer>[1]

const GridLayer$ = makePureLayerComponent<{
  optionsManipulate?: GridLayerOptionsManipulator
  visible?: boolean
}>(
  (globe, { optionsManipulate }) => new GridLayer(globe, optionsManipulate),
  'visible',
)

setDisplayName({ GridLayer$ })

export { GridLayer$ }
