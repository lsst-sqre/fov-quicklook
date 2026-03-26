from typing import Annotated

import fastapi

from quicklook.types import VisitName

VISIT_NAME_PATH_PATTERN = r'^[^:/]+:[^:/]+:[^:/]+$'


async def dep_visit_name(
    visit_name: Annotated[str, fastapi.Path(..., pattern=VISIT_NAME_PATH_PATTERN)],
):
    return VisitName(visit_name)
