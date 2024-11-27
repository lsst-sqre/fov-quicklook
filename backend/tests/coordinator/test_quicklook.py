import asyncio

from quicklook.coordinator.quicklook import Quicklook, QuicklookMeta
from quicklook.models import QuicklookRecord
from quicklook.types import BBox, CcdId, ImageStat, ProcessCcdResult, Visit
from quicklook.utils.event import WatchEvent
import pytest


async def test_quicklook_subscribe():
    events: list[WatchEvent[Quicklook]] = []
    gather_ready = asyncio.Event()

    async def gather_events():
        nonlocal events
        async for _ in Quicklook.subscribe():
            gather_ready.set()
            events = [*events, *_]
            if len(_) > 0 and _[-1].type == 'deleted':
                break

    async def generate_events():
        await gather_ready.wait()
        ql = Quicklook.from_record(QuicklookRecord(id='raw:broccoli', phase='ready'))
        ql.notify()
        ql.delete()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(gather_events())
        tg.create_task(generate_events())

    assert len(events) == 3


async def test_quicklook_meta():
    visit = Visit.from_id('raw:example')
    Quicklook.enqueue(visit=visit)
    ql = Quicklook.get(visit)
    assert ql
    assert ql.load_meta().meta is None
    ql.save_meta(QuicklookMeta(ccd_meta=[]))
    assert ql.load_meta().meta == QuicklookMeta(ccd_meta=[])
    process_ccd_result = ProcessCcdResult(
        ccd_id=CcdId(visit=visit, ccd_name='R00_SG0'),
        image_stat=ImageStat(median=0.0, mad=0.0, shape=(0, 0)),
        amps=[],
        bbox=BBox(minx=0, miny=0, maxx=0, maxy=0),
    )
    ql.save_meta(QuicklookMeta.from_process_ccd_results([process_ccd_result]))
    assert ql.load_meta().meta == QuicklookMeta.from_process_ccd_results([process_ccd_result])


@pytest.fixture(autouse=True)
async def setup():
    await Quicklook.delete_all()
    yield
    await Quicklook.delete_all()
