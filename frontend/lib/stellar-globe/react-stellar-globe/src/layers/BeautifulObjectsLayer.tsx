import { BeautifulObjectLayer, EsoMilkyWayLayer } from "@stellar-globe/stellar-globe"
import { makePureLayerComponent, setDisplayName } from "../GlobeContext"
import { memo } from "react"

const One = makePureLayerComponent<
  {
    which: ConstructorParameters<typeof BeautifulObjectLayer>[1]
    visible?: boolean
  }
>((globe, { which }) => new BeautifulObjectLayer(globe, which), 'visible')

type Props = {
  visible?: boolean
}

const BeautifulObjectLayer$ = memo(({ visible }: Props) => {
  return (
    <>
      <One visible={visible} which='m31' />
      <One visible={visible} which='m42' />
      <One visible={visible} which='m45' />
      <One visible={visible} which='m101' />
      <One visible={visible} which='perseus' />
    </>
  )
})

setDisplayName({ BeautifulObjectLayer$ })
export { BeautifulObjectLayer$ }
