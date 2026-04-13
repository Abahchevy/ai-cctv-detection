"""
Database Models (SQLAlchemy)
"""
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ViolationRecord(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(64), nullable=False, index=True)
    track_id = Column(Integer, nullable=True)
    missing_ppe = Column(Text, nullable=False)          # JSON list
    snapshot_path = Column(Text, nullable=True)
    timestamp_utc = Column(String(32), nullable=False, index=True)
    frame_index = Column(Integer, nullable=False)
