"""
Schemas for profile generation endpoints
"""

from typing import Optional

from pydantic import BaseModel, Field


class GeneratePreviewRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=50)
    template: Optional[dict] = None
    target_first_name: Optional[str] = None
    target_last_name: Optional[str] = None
    target_state: Optional[str] = None
    target_age: Optional[int] = None


class GeneratePreviewResponse(BaseModel):
    profiles: list[dict]
