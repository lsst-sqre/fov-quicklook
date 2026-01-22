from typing import Annotated

import fastapi

from quicklook.types import CcdDataRef, CcdName, TilePos, VisitName


def dep_visit_name(
    visit_name: Annotated[str, fastapi.Path(..., pattern=r'^\w+:\w+:\w+$')],
):
    return VisitName(visit_name)


def dep_ccd_name(
    ccd_name: Annotated[str, fastapi.Path(..., pattern=r'^\w+$')],
):
    return CcdName(ccd_name)


def dep_ccd_data_ref(
    visit: Annotated[VisitName, fastapi.Depends(dep_visit_name)],
    ccd: Annotated[CcdName, fastapi.Depends(dep_ccd_name)],
):
    return CcdDataRef(visit, ccd)


def dep_tile_pos(
    z: Annotated[int, fastapi.Path(...)],
    y: Annotated[int, fastapi.Path(...)],
    x: Annotated[int, fastapi.Path(...)],
):
    return TilePos(z, y, x)
