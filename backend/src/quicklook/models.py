import datetime
import json
from typing import Literal, Union

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from quicklook.types import HeaderType, Visit


class Base(DeclarativeBase):
    pass


class QuicklookRecord(Base):
    Phase = Literal['queued', 'processing', 'ready', 'deleting']

    __tablename__ = 'quicklooks'

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    phase: Mapped[Phase] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def visit(self):
        return Visit.from_id(self.id)

    meta: Mapped[Union[None, 'QuicklookMetaRecord']] = relationship('QuicklookMetaRecord', uselist=False, back_populates='quicklook', cascade="all, delete")


class QuicklookMetaRecord(Base):
    __tablename__ = 'quicklook_meta'

    id: Mapped[str] = mapped_column(String(256), ForeignKey('quicklooks.id', ondelete="CASCADE"), primary_key=True)
    body_json: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.now(), onupdate=func.now())

    quicklook: Mapped[QuicklookRecord] = relationship('QuicklookRecord', back_populates='meta')

    @property
    def body(self):
        return json.loads(self.body_json)

    @body.setter
    def body(self, value):
        self.body_json = json.dumps(value)
