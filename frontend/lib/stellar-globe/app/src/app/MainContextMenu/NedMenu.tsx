import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuItem, SubMenu } from "@szhsin/react-menu"

export function NedMenu({ openedAt }: { openedAt: SkyCoord }) {
  const openNedPage = (radiusAmin: number) => {
    return () => {
      const { a, d } = openedAt
      const coords = `ra=${encodeURIComponent(a.sexadecimal(15, false))}&dec=${encodeURIComponent(d.sexadecimal(1, true))}`
      const url = `https://ned.ipac.caltech.edu/conesearch?search_type=Near%20Position%20Search&in_csys=Equatorial&in_equinox=J2000&${coords}&radius=${radiusAmin}`
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
    <SubMenu label="Query Objects on NED within">
      <MenuItem disabled>Open NED page</MenuItem>
      {radiusAminList.map(([radiusAmin, label]) => (
        <MenuItem key={radiusAmin} onClick={openNedPage(radiusAmin)}>
          <div
            dangerouslySetInnerHTML={{ __html: label }}
          />
        </MenuItem>
      ))}
    </SubMenu>
  )
}
