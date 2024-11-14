from typing import Annotated

import fastapi

from quicklook.types import CcdDataType, Visit


def visit_from_path(
    id: Annotated[str, fastapi.Path(..., pattern=r'^\w+:\w+$')],
):
    return Visit.from_id(id)
