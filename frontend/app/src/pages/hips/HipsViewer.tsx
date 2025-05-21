import { Globe$, GlobeHandle, GridLayer$, HipsSimpleLayer$ } from "@stellar-globe/react-stellar-globe"
import { useAppSelector } from "../../store/hooks"
import { useGetHipsFileQuery } from "../../store/api/openapi"
import { useEffect, useRef } from "react"
import { angle, hips } from "@stellar-globe/stellar-globe"
import { env } from "../../env"


export function HipsViewer() {
  const repository = useAppSelector((state) => state.hips.repository)
  const globeHandle = useRef<GlobeHandle>(null)


  useEffect(() => {
    (async () => {
      if (repository) {
        const properties = await hips.fetchHiPSProperties(`${env.baseUrl}/api/hips/${repository}`)
        const dec = Number(properties['hips_initial_dec'])
        const ra = Number(properties['hips_initial_ra'])
        const fov = Number(properties['hips_initial_fov'])
        if (isFinite(dec) && isFinite(ra) && isFinite(fov)) {
          globeHandle.current?.().camera.jumpTo({ fovy: angle.deg2rad(fov), }, { coord: angle.SkyCoord.fromDeg(ra, dec) })
        }
      }
    })()
  }, [repository])

  return (
    <Globe$ ref={globeHandle}>
      <GridLayer$ />
      {repository && (
        <HipsSimpleLayer$ baseUrl={`${env.baseUrl}/api/hips/${repository}`} />
      )}
    </Globe$>
  )
}
