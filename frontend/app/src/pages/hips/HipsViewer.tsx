import { ConstellationLayer$, EsoMilkyWayLayer$, Globe$, GlobeHandle, GridLayer$, HipparcosCatalogLayer$, HipsSimpleLayer$ } from "@stellar-globe/react-stellar-globe"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { useGetHipsFileQuery } from "../../store/api/openapi"
import { useEffect, useRef } from "react"
import { angle, easing, hips } from "@stellar-globe/stellar-globe"
import { env } from "../../env"
import { hipsSlice } from "../../store/features/hipsSlice"
import { copyTextToClipboard } from "../../utils/copyTextToClipboard"

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

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

  const notes = useAppSelector((state) => state.hips.notes)
  const dispatch = useAppDispatch()

  const copyPostion = () => {
    const camera = globeHandle.current?.().camera
    if (camera) {
      copyTextToClipboard(JSON.stringify({ ...camera.center(), fovy: camera.fovy, roll: camera.roll }))
    }
  }

  const go = async () => {
    const camera = globeHandle.current?.().camera
    if (camera) {
      for (const item of program) {
        const coord = angle.SkyCoord.fromRad(item.a.rad, item.d.rad)
        await camera.jumpTo(
          { fovy: item.fovy, roll: item.roll ?? 0 },
          { coord, duration: item.duration, easingFunction: easing.slowStartStop4 }
        )
        await sleep(item.sleep)
      }
    }
  }

  return (
    <>
      <Globe$ ref={globeHandle}>
        <GridLayer$ />
        <EsoMilkyWayLayer$ />
        {/* <HipsSimpleLayer$ baseUrl={`${env.baseUrl}/api/hips/${repository}`} /> */}
        <ConstellationLayer$ />
        {repository && (
          <HipsSimpleLayer$ animationLod={0} baseUrl={`${env.baseUrl}/api/hips/${repository}`} />
        )}
        <HipparcosCatalogLayer$ />
      </Globe$>
      <div style={{ position: 'absolute', top: 0, right: 0 }} >
        {/* <textarea readOnly value={notes} style={{ width: '200px', height: '20px' }} /> */}
        <button onClick={copyPostion}>CopyPosition</button>
        <button onClick={go}>Go</button>
      </div>
    </>
  )
}


const program = [
  { duration: 0, sleep: 2000, "a": { "rad": 3.3649577673135616 }, "d": { "rad": 0.09015022330730997 }, "fovy": 3.999703721015735 }, // 引き
  { duration: 10_000, sleep: 2000, "a": { "rad": 3.6923819094783985 }, "d": { "rad": -0.12139376245396043 }, "fovy": 0.09384965629748067 }, // 視野
  { duration: 5_000, sleep: 3000, "a": { "rad": 3.680098232497507 }, "d": { "rad": -0.10561775406822269 }, "fovy": 0.0027608202729330032 }, // 単体
  { duration: 5_000, sleep: 3000, "a": { "rad": 3.6947477323641404 }, "d": { "rad": -0.0952440155974535 }, "fovy": 0.009057240642903915 }, // 双子
  { duration: 5_000, sleep: 3000, "a": { "rad": 3.6939240896400634 }, "d": { "rad": -0.09517745945593162 }, "fovy": 0.0011762514343165542 }, // 双子の１つ
  { duration: 5_000, sleep: 3000, "a": { "rad": 3.69529468327062 }, "d": { "rad": -0.09557626090780202 }, "fovy": 0.001117886093378543, "roll": 1.0100896946296096 }, // 双子のもう１つ
  { duration: 10_000, sleep: 1000, "a": { "rad": 3.3649577673135616 }, "d": { "rad": 0.09015022330730997 }, "fovy": 3.999703721015735 }, // 引き
]
