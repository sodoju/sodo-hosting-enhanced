from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from bot.models.base import Base


class BroadcastStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    cancelled = "cancelled"


class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_by: Mapped[int] = mapped_column(BigInteger)
    message_text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[BroadcastStatus] = mapped_column(SAEnum(BroadcastStatus, name="broadcaststatus_enum"), default=BroadcastStatus.pending)
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
