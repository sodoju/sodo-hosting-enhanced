from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.models.base import Base


class RedeemCode(Base):
    __tablename__ = "redeem_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    credit_amount: Mapped[int] = mapped_column(Integer)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    records: Mapped[list["RedeemRecord"]] = relationship(
        "RedeemRecord", back_populates="code_ref", cascade="all, delete-orphan"
    )


class RedeemRecord(Base):
    __tablename__ = "redeem_records"
    __table_args__ = (UniqueConstraint("code_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code_id: Mapped[int] = mapped_column(Integer, ForeignKey("redeem_codes.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    code_ref: Mapped["RedeemCode"] = relationship("RedeemCode", back_populates="records")
