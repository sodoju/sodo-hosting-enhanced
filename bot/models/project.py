from __future__ import annotations
import enum
import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.models.base import Base


class ProjectStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    stopped = "stopped"
    failed = "failed"
    suspended = "suspended"


class Runtime(str, enum.Enum):
    python = "python"
    nodejs = "nodejs"


class DeploymentStatus(str, enum.Enum):
    queued = "queued"
    building = "building"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    runtime: Mapped[Runtime] = mapped_column(SAEnum(Runtime, name="runtime_enum"), default=Runtime.python)
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus, name="projectstatus_enum"), default=ProjectStatus.pending)
    entry_file: Mapped[str | None] = mapped_column(String(256), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    process_pid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    env_vars: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    deployments: Mapped[list["Deployment"]] = relationship(
        "Deployment", back_populates="project", cascade="all, delete-orphan",
        order_by="Deployment.created_at.desc()"
    )
    log_entries: Mapped[list["LogEntry"]] = relationship(
        "LogEntry", back_populates="project", cascade="all, delete-orphan"
    )


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    triggered_by: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[DeploymentStatus] = mapped_column(SAEnum(DeploymentStatus, name="deploymentstatus_enum"), default=DeploymentStatus.queued)
    log_output: Mapped[str] = mapped_column(Text, default="", server_default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="deployments")


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    deployment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="log_entries")
