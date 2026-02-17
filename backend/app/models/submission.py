"""
Submission model for tracking individual fake data submissions to broker sites
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Submission(Base):
    """Individual fake data submission to a data broker site"""

    __tablename__ = "submissions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to campaign
    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Target site
    site: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Status
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus),
        default=SubmissionStatus.PENDING,
        nullable=False
    )

    # The fake profile data that was/will be submitted
    profile_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Confirmation or tracking number from the target site
    reference_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Error details if submission failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # When the submission was actually sent
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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

    # Relationship to campaign
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="submissions"
    )

    def __repr__(self) -> str:
        return f"<Submission(id={self.id}, site={self.site}, status={self.status})>"
