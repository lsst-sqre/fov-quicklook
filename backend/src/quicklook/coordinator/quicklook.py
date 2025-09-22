from quicklook.types import Visit
from quicklook.utils.dynamic_dispatch import dynamic_dispatch


async def create_quickook(visit: Visit):
    # list ccds
    ccds: list = []

    # タイル化
    async for x in dynamic_dispatch(workers=, ccds=ccds):
        pass
