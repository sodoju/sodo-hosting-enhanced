from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.models.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    max_projects: Mapped[int] = mapped_column(Integer, default=5)
    max_file_size_mb: Mapped[int] = mapped_column(Integer, default=10)
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=100)
    allows_zip: Mapped[bool] = mapped_column(Boolean, default=True)
    allows_github: Mapped[bool] = mapped_column(Boolean, default=True)
    allows_nodejs: Mapped[bool] = mapped_column(Boolean, default=True)
    allows_multi_file: Mapped[bool] = mapped_column(Boolean, default=True)
    allows_env_vars: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_credits: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"))
    granted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")
