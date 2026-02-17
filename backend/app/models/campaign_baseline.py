"""
CampaignBaseline model for tracking data broker accuracy over time
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CampaignBaseline(Base):
    """Snapshot of what data brokers have on a target at a point in time"""

    __tablename__ = "campaign_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "baseline" for the initial snapshot, "check" for follow-ups
    snapshot_type: Mapped[str] = mapped_column(String(20), nullable=False)

    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sources_checked: Mapped[int] = mapped_column(Integer, default=0)
    records_found: Mapped[int] = mapped_column(Integer, default=0)

    # Full scraper output
    raw_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Accuracy tracking
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    data_points_total: Mapped[int] = mapped_column(Integer, default=0)
    data_points_accurate: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="baselines",
    )

    def __repr__(self) -> str:
        return f"<CampaignBaseline(id={self.id}, type={self.snapshot_type}, score={self.accuracy_score})>"
