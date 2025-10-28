from typing import Annotated

import fastapi

from quicklook.types import VisitName


def dep_visit_name(
    visit_name: Annotated[str, fastapi.Path(..., pattern=r'^\w+:\w+$')],
):
    return VisitName(visit_name)
