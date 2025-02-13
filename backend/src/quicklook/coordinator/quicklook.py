from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from typing import AsyncGenerator, Union

from pydantic import BaseModel
from sqlalchemy import Delete, delete, insert, select

from quicklook.db import db_context
from quicklook.models import QuicklookMetaRecord, QuicklookRecord
from quicklook.types import AmpMeta, BBox, CcdId, GeneratorPod, GeneratorProgress, ImageStat, ProcessCcdResult, Visit
from quicklook.utils.http_request import http_request
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent
import asyncio


@dataclass
class Quicklook:
    # Quicklookを表すクラス
    # DBのラッパー

    visit: Visit
    phase: QuicklookRecord.Phase
    ccd_generator_map: dict[str, GeneratorPod] | None = None  # ccd_name -> GeneratorPod
    generating_progress: dict[str, GeneratorProgress] | None = None
    transferreing_progress: dict[str, GeneratorProgress] | None = None
    meta: Union['QuicklookMeta', None] = None

    @classmethod
    @contextmanager
    def _db(cls):
        with db_context() as db:
            yield db

    @classmethod
    def enqueue(cls, visit: Visit):
        stmt = select(QuicklookRecord).filter(QuicklookRecord.id == visit.id)
        with cls._db() as db:
            r = db.execute(stmt).scalar_one_or_none()
            if r is None:  # pragma: no branch
                r = QuicklookRecord(id=visit.id, phase='queued')
                db.add(r)
                db.commit()

    @classmethod
    def dequeue(cls):
        with cls._db() as db:
            stmt = select(QuicklookRecord).filter(QuicklookRecord.phase == 'queued').order_by(QuicklookRecord.created_at)
            r = db.execute(stmt).scalar_one_or_none()
        if r:  # pragma: no branch
            ql = cls.from_record(r)
            ql.phase = 'processing'
            ql.save()
            return ql

    @classmethod
    def from_record(cls, r: QuicklookRecord) -> 'Quicklook':
        return cls._manager().from_record(r)

    @classmethod
    async def delete_all(cls):
        from quicklook.coordinator.api.generators import ctx
        
        with cls._db() as db:
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
        with cls._db() as db:
            stmt = select(QuicklookRecord).filter(QuicklookRecord.id == visit.id)
            r = db.execute(stmt).scalar_one_or_none()
        if r:  # pragma: no branch
            return cls.from_record(r)

    @classmethod
    @cache
    def _manager(cls) -> '_QuicklookManager':
        return _QuicklookManager()

    @classmethod
    def subscribe(cls) -> AsyncGenerator[list[WatchEvent['Quicklook']], None]:
        return cls._manager().subscribe()

    def save(self) -> None:
        with self._db() as db:
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
        with self._db() as db:
            stmt = delete(QuicklookRecord).filter(QuicklookRecord.id == self.visit.id)
            db.execute(stmt)
            db.commit()
        self._manager().unregister(self)

    @classmethod
    @contextmanager
    def enable_subscription(cls):
        yield

    def load_meta(self) -> 'Quicklook':
        with self._db() as db:
            stmt = select(QuicklookRecord).where(QuicklookRecord.id == self.id)
            r = db.execute(stmt).scalar_one()
            if r.meta:
                self.meta = QuicklookMeta.model_validate(r.meta.body)
        return self

    def save_meta(self, meta: 'QuicklookMeta'):
        self.meta = meta
        body_json = meta.model_dump_json()
        with self._db() as db:
            db.execute(Delete(QuicklookMetaRecord).where(QuicklookMetaRecord.id == self.id))
            stmt = insert(QuicklookMetaRecord).values(id=self.id, body_json=body_json)
            db.execute(stmt)
            db.commit()


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
    ql: Quicklook


class _QuicklookManager:
    def __init__(self):
        self._entries: dict[Visit, CacheEntry] = {}
        self._event_queue = BroadcastQueue[WatchEvent[Quicklook]]()

    def unregister(self, ql: Quicklook):
        self._entries.pop(ql.visit)
        self._event_queue.put(WatchEvent(ql, 'deleted'))

    def notify_modified(self, ql: Quicklook):
        self._event_queue.put(WatchEvent(ql, 'modified'))

    def from_record(self, r: QuicklookRecord) -> Quicklook:
        visit = Visit.from_id(r.id)
        if visit not in self._entries:
            ql = Quicklook(visit=visit, phase=r.phase)
            self._entries[visit] = CacheEntry(ql)
            self._event_queue.put(WatchEvent(ql, 'added'))
        return self._entries[visit].ql

    async def subscribe(self) -> AsyncGenerator[list[WatchEvent[Quicklook]], None]:
        yield [WatchEvent(e.ql, 'added') for e in self._entries.values()]
        with self._event_queue.subscribe() as events:
            while True:
                yield [await events.get()]
