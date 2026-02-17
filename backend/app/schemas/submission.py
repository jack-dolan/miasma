"""
Pydantic schemas for submission API operations
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class SubmissionResponse(BaseModel):
    """Schema for submission in responses"""
    id: int
    campaign_id: int
    site: str
    status: str
    profile_data: Optional[dict] = None
    reference_id: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubmissionList(BaseModel):
    """Paginated list of submissions"""
    items: List[SubmissionResponse]
    total: int
    page: int
    page_size: int
    pages: int
