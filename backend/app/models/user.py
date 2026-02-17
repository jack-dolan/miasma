"""
User model for authentication and user management
"""

from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """User model for authentication and profile management"""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile information
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
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
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    password_reset_token: Mapped[str] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Email verification
    email_verification_token: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Preferences and settings
    preferences: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    
    # Relationships
    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    lookup_results: Mapped[List["LookupResult"]] = relationship(
        "LookupResult",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"