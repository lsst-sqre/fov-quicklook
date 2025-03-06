import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from typing import AsyncGenerator, Union

from pydantic import BaseModel
from sqlalchemy import delete, select

from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.types import AmpMeta, BBox, CcdId, GeneratorPod, GeneratorProgress, ImageStat, ProcessCcdResult, Visit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent
from quicklook.utils.http_request import http_request


@dataclass
class QuicklookJob:
    visit: Visit
    phase: QuicklookRecord.Phase
    ccd_generator_map: dict[str, GeneratorPod] | None = None  # ccd_name -> GeneratorPod
    generating_progress: dict[str, GeneratorProgress] | None = None
    transferreing_progress: dict[str, GeneratorProgress] | None = None
    meta: Union['QuicklookMeta', None] = None

    @classmethod
    def enqueue(cls, visit: Visit):
        stmt = select(QuicklookRecord).filter(QuicklookRecord.id == visit.id)
        with db_context() as db:
            r = db.execute(stmt).scalar_one_or_none()
            if r is None:  # pragma: no branch
                r = QuicklookRecord(id=visit.id, phase='queued')
                db.add(r)
                db.commit()

    @classmethod
    def dequeue(cls):
        with db_context() as db:
            stmt = select(QuicklookRecord).filter(QuicklookRecord.phase == 'queued').order_by(QuicklookRecord.created_at)
            r = db.execute(stmt).scalar_one_or_none()
        if r:  # pragma: no branch
            ql = cls.from_record(r)
            ql.phase = 'processing'
            ql.save()
            return ql

    @classmethod
    def from_record(cls, r: QuicklookRecord) -> 'QuicklookJob':
        return cls._manager().from_record(r)

    @classmethod
    async def delete_all(cls):
        from quicklook.coordinator.api.generators import ctx

        with db_context() as db:
            stmt = select(QuicklookRecord)
            records = db.execute(stmt).scalars().all()
        for r in records:
            ql = cls.from_record(r)
            ql.delete()

        async def delete_generator(g: GeneratorPod):
            await http_request('delete', f'http://{g.host}:{g.port}/quicklooks/*')

        await asyncio.gather(*(delete_generator(g) for g in ctx().generators))

    @classmethod
    def get(cls, visit: Visit):
        with db_context() as db:
            stmt = select(QuicklookRecord).filter(QuicklookRecord.id == visit.id)
            r = db.execute(stmt).scalar_one_or_none()
        if r:  # pragma: no branch
            return cls.from_record(r)

    @classmethod
    @cache
    def _manager(cls) -> 'QuicklookJobManager':
        return QuicklookJobManager()

    @classmethod
    def subscribe(cls) -> AsyncGenerator[list[WatchEvent['QuicklookJob']], None]:
        return cls._manager().subscribe()

    def save(self) -> None:
        with db_context() as db:
            stmt = select(QuicklookRecord).filter(QuicklookRecord.id == self.visit.id)
            r = db.execute(stmt).scalar_one()
            r.phase = self.phase
            db.commit()

    @property
    def id(self):
        return self.visit.id

    def notify(self):
        self._manager().notify_modified(self)

    def delete(self):
        with db_context() as db:
            stmt = delete(QuicklookRecord).filter(QuicklookRecord.id == self.visit.id)
            db.execute(stmt)
            db.commit()
        self._manager().unregister(self)

    @classmethod
    @contextmanager
    def enable_subscription(cls):
        yield

    def save_meta(self, meta: 'QuicklookMeta'):
        self.meta = meta


class CcdMeta(BaseModel):
    ccd_id: CcdId
    image_stat: ImageStat
    amps: list[AmpMeta]
    bbox: BBox


class QuicklookMeta(BaseModel):
    ccd_meta: list[CcdMeta]

    @classmethod
    def from_process_ccd_results(cls, results: list[ProcessCcdResult]) -> 'QuicklookMeta':
        return cls(
            ccd_meta=[
                CcdMeta(
                    ccd_id=result.ccd_id,
                    image_stat=result.image_stat,
                    amps=result.amps,
                    bbox=result.bbox,
                )
                for result in results
            ]
        )


@dataclass
class CacheEntry:
    job: QuicklookJob


class QuicklookJobManager:
    def __init__(self):
        self._entries: dict[Visit, CacheEntry] = {}
        self._event_queue = BroadcastQueue[WatchEvent[QuicklookJob]]()

    def unregister(self, ql: QuicklookJob):
        self._entries.pop(ql.visit)
        self._event_queue.put(WatchEvent(ql, 'deleted'))

    def notify_modified(self, ql: QuicklookJob):
        self._event_queue.put(WatchEvent(ql, 'modified'))

    def from_record(self, r: QuicklookRecord) -> QuicklookJob:
        visit = Visit.from_id(r.id)
        if visit not in self._entries:
            ql = QuicklookJob(visit=visit, phase=r.phase)
            self._entries[visit] = CacheEntry(ql)
            self._event_queue.put(WatchEvent(ql, 'added'))
        return self._entries[visit].job

    async def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJob]], None]:
        yield [WatchEvent(e.job, 'added') for e in self._entries.values()]
        with self._event_queue.subscribe() as events:
            while True:
                yield [await events.get()]
