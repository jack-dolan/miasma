"""
LookupResult model for storing person search results from data brokers
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LookupResult(Base):
    """Stores results from person lookups across data broker sites"""

    __tablename__ = "lookup_results"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to user who performed the search
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Search query parameters
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Search metadata
    sources_searched: Mapped[int] = mapped_column(Integer, default=0)
    sources_successful: Mapped[int] = mapped_column(Integer, default=0)
    total_records_found: Mapped[int] = mapped_column(Integer, default=0)

    # Raw results stored as JSON
    raw_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship to user
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="lookup_results"
    )

    # Relationship to individual person records
    person_records: Mapped[list["PersonRecord"]] = relationship(
        "PersonRecord",
        back_populates="lookup_result",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LookupResult(id={self.id}, name={self.first_name} {self.last_name}, records={self.total_records_found})>"


class PersonRecord(Base):
    """Individual person record found in a lookup"""

    __tablename__ = "person_records"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to lookup result
    lookup_result_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lookup_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Source information
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Person information
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Arrays stored as JSON
    addresses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    phone_numbers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    emails: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    relatives: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Profile URL on the data broker site
    profile_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Raw data from scraper
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship to lookup result
    lookup_result: Mapped["LookupResult"] = relationship(
        "LookupResult",
        back_populates="person_records"
    )

    def __repr__(self) -> str:
        return f"<PersonRecord(id={self.id}, name={self.name}, source={self.source})>"
