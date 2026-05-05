import { SkyCoord, angle } from "@stellar-globe/stellar-globe"
import { MenuDivider, MenuItem, SubMenu } from "@szhsin/react-menu"
import { useBlockUI } from "../../common/components/Modal"
import { catalogsSlice } from "../features/catalog/catalogSlice"
import { useAppDispatch } from "../store/hooks"
import { simbadCatalog } from "./simbad"

export function SimbadMenu({ openedAt }: { openedAt: SkyCoord }) {
  const dispatch = useAppDispatch()
  const blockUI = useBlockUI()

  const addSymbadCatalog = (radiusAmin: number) => {
    return async () => {
      await blockUI(async () => {
        try {
          const { attributes, markers, fields, } = await simbadCatalog(openedAt, angle.amin2rad(radiusAmin))
          dispatch(catalogsSlice.actions.catalogAdded({
            name: `SIMBAD`,
            fields,
            attributes,
            markers,
          }))
        } catch (e) {
          alert(e)
        }
      })
    }
  }

  const openSymbadPage = (radiusAmin: number) => {
    return () => {
      const { a, d } = openedAt
      const coord = `${a.deg}+${d.deg}`
      const url = `https://simbad.u-strasbg.fr/simbad/sim-coo?Coord=${coord}&CooFrame=FK5&CooEpoch=2000&CooEqui=2000&CooDefinedFrames=none&Radius=${radiusAmin}&Radius.unit=arcmin&submit=submit+query`
      window.open(url, '_blank')
    }
  }

  const radiusAminList: [number, string][] = [
    [1, '1&prime;'],
    [5, '5&prime;'],
    [10, '10&prime;'],
    [60, '1&deg;'],
  ]

  return (
    <SubMenu label="Query Objects on SIMBAD within">
      {radiusAminList.map(([radiusAmin, label]) => (
        <MenuItem key={radiusAmin} onClick={addSymbadCatalog(radiusAmin)}><div dangerouslySetInnerHTML={{ __html: label }} /></MenuItem>
      ))}
      <MenuDivider />
      <MenuItem disabled>Open SIMBAD page</MenuItem>
      {radiusAminList.map(([radiusAmin, label]) => (
        <MenuItem key={radiusAmin} onClick={openSymbadPage(radiusAmin)}>
          <div
            dangerouslySetInnerHTML={{ __html: label }}
          />
        </MenuItem>
      ))}
    </SubMenu>
  )
}
