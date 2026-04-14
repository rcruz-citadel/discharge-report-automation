"""SQLAlchemy ORM table definitions for the discharge_app schema."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AppSession(Base):
    """Server-side session store. Token is a 32-byte random hex string."""

    __tablename__ = "app_session"
    __table_args__ = {"schema": "discharge_app"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    user_email: Mapped[str] = mapped_column(Text, nullable=False)
    user_name: Mapped[str] = mapped_column(Text, nullable=False)
    user_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppUser(Base):
    """Application users managed by admins. Read-only from API perspective."""

    __tablename__ = "app_user"
    __table_args__ = {"schema": "discharge_app"}

    user_email: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # 'staff' | 'manager' | 'admin'
    practices: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class OutreachStatus(Base):
    """Per-discharge-event outreach status. Composite PK: (event_id, discharge_date)."""

    __tablename__ = "outreach_status"
    __table_args__ = {"schema": "discharge_app"}

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    discharge_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="no_outreach"
    )
    updated_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserActivityLog(Base):
    """Append-only activity log for audit trail and manager metrics."""

    __tablename__ = "user_activity_log"
    __table_args__ = {"schema": "discharge_app"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)  # 'login' | 'outreach_update' | etc.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
