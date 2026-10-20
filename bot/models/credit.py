from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.models.base import Base


class TransactionType(str, enum.Enum):
    welcome = "welcome"
    daily = "daily"
    referral = "referral"
    redeem = "redeem"
    admin_add = "admin_add"
    admin_deduct = "admin_deduct"
    purchase = "purchase"
    refund = "refund"


class CreditWallet(Base):
    __tablename__ = "credit_wallets"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="wallet")
    transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction", back_populates="wallet", cascade="all, delete-orphan",
        order_by="CreditTransaction.created_at.desc()"
    )


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("credit_wallets.user_id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(BigInteger)
    type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType, name="transactiontype_enum"))
    description: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    wallet: Mapped["CreditWallet"] = relationship("CreditWallet", back_populates="transactions")
