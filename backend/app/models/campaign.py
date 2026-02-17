"""
Campaign model for managing data poisoning campaigns
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class CampaignStatus(str, enum.Enum):
    """Status of a campaign"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Campaign(Base):
    """Campaign for submitting fake data to data broker sites"""

    __tablename__ = "campaigns"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to user who created the campaign
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Campaign details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus),
        default=CampaignStatus.DRAFT,
        nullable=False
    )

    # Target identity (the real person whose records we're poisoning)
    target_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    target_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Target configuration
    target_sites: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    target_count: Mapped[int] = mapped_column(Integer, default=10)

    # Fake profile configuration
    profile_template: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Execution tracking
    submissions_completed: Mapped[int] = mapped_column(Integer, default=0)
    submissions_failed: Mapped[int] = mapped_column(Integer, default=0)
    last_execution: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_execution: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="campaigns"
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="campaign",
        cascade="all, delete-orphan"
    )
    baselines: Mapped[List["CampaignBaseline"]] = relationship(
        "CampaignBaseline",
        back_populates="campaign",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name={self.name}, status={self.status})>"
