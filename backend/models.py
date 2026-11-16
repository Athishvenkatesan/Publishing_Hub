"""One row per (submission, account). The history table reads these rows."""
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base

FINAL = {"PUBLISHED", "FAILED", "CANCELLED"}


def now():
    return datetime.now(timezone.utc)


class Publication(Base):
    __tablename__ = "publication"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[str] = mapped_column(String(40), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(120), default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    platform: Mapped[str] = mapped_column(String(30))
    account_id: Mapped[str] = mapped_column(String(64))
    account_name: Mapped[str] = mapped_column(String(120), default="")
    mode: Mapped[str] = mapped_column(String(10))  # now | schedule
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(60), default="UTC")
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", index=True)
    zernio_post_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    post_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    def as_dict(self):
        iso = lambda d: d.replace(tzinfo=d.tzinfo or timezone.utc).isoformat() if d else None
        return {
            "id": self.id, "group_id": self.group_id, "filename": self.filename,
            "title": self.title, "caption": self.caption, "platform": self.platform, "account_name": self.account_name,
            "mode": self.mode, "scheduled_for": iso(self.scheduled_for), "timezone": self.timezone,
            "status": self.status, "post_url": self.post_url, "error": self.error,
            "created_at": iso(self.created_at),
        }
