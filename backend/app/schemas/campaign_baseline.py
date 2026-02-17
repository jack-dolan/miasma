"""
Pydantic schemas for campaign baseline and accuracy tracking
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class BaselineResponse(BaseModel):
    """Schema for a baseline snapshot in responses"""
    id: int
    campaign_id: int
    snapshot_type: str
    taken_at: datetime
    sources_checked: int
    records_found: int
    accuracy_score: Optional[float] = None
    data_points_total: int
    data_points_accurate: int

    class Config:
        from_attributes = True


class BaselineDetailResponse(BaselineResponse):
    """Includes full raw scraper data"""
    raw_results: Optional[dict] = None


class BaselineListResponse(BaseModel):
    """List of baseline snapshots"""
    baselines: List[BaselineResponse]


class AccuracyComparison(BaseModel):
    """Comparison between baseline and latest check"""
    baseline: Optional[BaselineResponse] = None
    latest_check: Optional[BaselineResponse] = None
    accuracy_change: Optional[float] = None
    checks_count: int
