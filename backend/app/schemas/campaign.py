"""
Pydantic schemas for campaign API operations
"""

from datetime import datetime
from typing import Optional, List, Literal, Dict, Any

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    """Schema for creating a campaign"""
    name: str
    description: Optional[str] = None
    target_first_name: str
    target_last_name: str
    target_city: Optional[str] = None
    target_state: Optional[str] = None
    target_age: Optional[int] = None
    target_sites: Optional[List[str]] = None
    target_count: int = 10
    campaign_type: Literal["optout", "poisoning"] = "poisoning"


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    name: Optional[str] = None
    description: Optional[str] = None
    target_first_name: Optional[str] = None
    target_last_name: Optional[str] = None
    target_city: Optional[str] = None
    target_state: Optional[str] = None
    target_age: Optional[int] = None
    target_sites: Optional[List[str]] = None
    target_count: Optional[int] = None
    status: Optional[str] = None
    campaign_type: Optional[Literal["optout", "poisoning"]] = None


class CampaignResponse(BaseModel):
    """Schema for campaign in responses"""
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    status: str
    campaign_type: str
    target_first_name: Optional[str] = None
    target_last_name: Optional[str] = None
    target_city: Optional[str] = None
    target_state: Optional[str] = None
    target_age: Optional[int] = None
    target_sites: Optional[List[str]] = None
    target_count: int
    submissions_completed: int
    submissions_failed: int
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    last_scan_at: Optional[datetime] = None
    last_scan_result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignList(BaseModel):
    """Paginated list of campaigns"""
    items: List[CampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int
