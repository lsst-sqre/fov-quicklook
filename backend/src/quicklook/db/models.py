"""Database setup and models for quicklook system."""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Quicklook(Base):
    __tablename__ = "quicklooks"

    visit_name: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    disk_usage: Mapped[int] = mapped_column(Integer, nullable=False)
    ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    accesses: Mapped[list["Access"]] = relationship(back_populates="quicklook", cascade="all, delete-orphan")


class Access(Base):
    __tablename__ = "accesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_name: Mapped[str] = mapped_column(String, ForeignKey("quicklooks.visit_name"), nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    quicklook: Mapped["Quicklook"] = relationship(back_populates="accesses")
