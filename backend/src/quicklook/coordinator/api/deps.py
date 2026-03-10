from typing import Annotated

import fastapi

from quicklook.datasource import get_datasource
from quicklook.types import VisitName

VISIT_NAME_PATH_PATTERN = r'^[^:/]+:[^:/]+:[^:/]+$'


async def dep_visit_name(
    visit_name: Annotated[str, fastapi.Path(..., pattern=VISIT_NAME_PATH_PATTERN)],
):
    return await get_datasource().resolve_visit(VisitName(visit_name))
