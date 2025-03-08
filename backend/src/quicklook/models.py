import datetime
from typing import Literal

from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class QuicklookRecord(Base):
    Phase = Literal['ready', 'in_progress']

    __tablename__ = 'quicklooks'

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    phase: Mapped[Phase] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.now(), onupdate=func.now())
