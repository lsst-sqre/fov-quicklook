import { DomLayer$, GlobeEventLayer$ } from "@stellar-globe/react-stellar-globe"
import { V3, angle } from "@stellar-globe/stellar-globe"
import { Fragment, useCallback, useMemo, useState } from "react"
import { useAppContext } from "../../../context"
import { useAppSelector } from "../../../store/hooks"
import { cameraSlice } from "../../camera/cameraSlice"
import { RingsTract } from "./RingsTract"
import styles from './styles.module.scss'

export function TractNumbersLayer() {
  const ringsTract = useMemo(() => RingsTract.numRings(120), [])

  const [camera, setCamera] = useState({
    fovy: useAppSelector(state => state.camera.params).fovy,
    center: useAppSelector(cameraSlice.selectors.center),
  })

  const { globeHandle } = useAppContext()

  const updateCameraParams = useCallback(() => {
    const camera = globeHandle.current!().camera
    setCamera({ center: camera.center(), fovy: camera.fovy })
  }, [globeHandle])

  const tracts = useMemo(() => {
    const { a, d } = camera.center
    const tracts: { position: V3, index: number }[] = []
    const i = ringsTract.d2ringIndex(d.rad)
    const size = 3
    for (let ii = -3; ii <= size; ++ii) {
      const iii = i + ii
      const j = ringsTract.ia2j(iii, a.rad)
      if (iii < 0 || iii >= ringsTract.numRings) continue
      for (let jj = -3; jj <= size; ++jj) {
        const jjj = j + jj
        const [aaa, ddd] = ringsTract.ij2ad(iii, jjj)
        const position = angle.SkyCoord.fromRad(aaa, ddd).xyz as V3
        const index = ringsTract.ij2index(iii, jjj)
        tracts.push({ position, index })
      }
    }
    return tracts
  }, [camera, ringsTract])

  return (
    <Fragment>
      <GlobeEventLayer$ onCameraMove={updateCameraParams} />
      {camera.fovy <= 0.2 &&
        tracts.map(({ position, index }) => (
          <DomLayer$ key={index} position={position}>
            <div className={styles.tractNumber}>{index}</div>
          </DomLayer$>
        ))
      }
    </Fragment>
  )
}
