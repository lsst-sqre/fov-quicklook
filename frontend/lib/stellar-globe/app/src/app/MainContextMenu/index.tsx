import { SkyCoord } from "@stellar-globe/stellar-globe"
import { MenuItem, SubMenu } from "@szhsin/react-menu"
import { Fragment } from "react/jsx-runtime"
import { copyToClipboard } from "../../common/utils/copyToClipboard"
import { AngleUnit } from "../../common/utils/formatAngle"
import { AddCoordinatesToCatalogMenu } from "./AddCoordinatesToCatalogMenu"
import { SimbadMenu } from "./SimbadMenu"
import { NedMenu } from "./NedMenu"


type Props = {
  openedAt: SkyCoord
}


export function MainContextMenu({
  openedAt,
}: Props) {
  const copyCoords = async (angleUnit: AngleUnit) => {
    await copyToClipboard(skyCoordToString(openedAt, angleUnit))
  }

  return (
    <Fragment>
      <SimbadMenu openedAt={openedAt} />
      <NedMenu openedAt={openedAt} />
      <SubMenu label='Copy Coordinates'>
        <MenuItem onClick={() => copyCoords('degree')}>in Degree</MenuItem>
        <MenuItem onClick={() => copyCoords('sexadecimal')}>in Sexadecimal</MenuItem>
      </SubMenu>
      <AddCoordinatesToCatalogMenu openedAt={openedAt} />
    </Fragment>
  )
}


function skyCoordToString(coord: SkyCoord, angleUnit: AngleUnit) {
  switch (angleUnit) {
    case 'degree':
      return `${coord.a.deg} ${coord.d.deg}`
    case 'radian':
      return `${coord.a.rad} ${coord.d.rad}`
    case 'sexadecimal': {
      const { a, d } = coord.toString()
      return `${a} ${d}`
    }
  }
}
