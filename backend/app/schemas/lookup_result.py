"""
Pydantic schemas for lookup result API operations
"""

from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel


# ============================================================================
# Request Schemas
# ============================================================================

class LookupRequest(BaseModel):
    """Schema for person lookup request"""
    first_name: str
    last_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    age: Optional[int] = None
    sources: Optional[List[str]] = None
    save_results: bool = True  # Whether to persist results to database


# ============================================================================
# Person Record Schemas
# ============================================================================

class PersonRecordBase(BaseModel):
    """Base schema for person record data"""
    name: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    addresses: Optional[List[str]] = None
    phone_numbers: Optional[List[str]] = None
    emails: Optional[List[str]] = None
    relatives: Optional[List[str]] = None
    profile_url: Optional[str] = None


class PersonRecordCreate(PersonRecordBase):
    """Schema for creating a person record"""
    source: str
    raw_data: Optional[Dict[str, Any]] = None


class PersonRecordResponse(PersonRecordBase):
    """Schema for person record in responses"""
    id: int
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Lookup Result Schemas
# ============================================================================

class LookupResultBase(BaseModel):
    """Base schema for lookup result"""
    first_name: str
    last_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    age: Optional[int] = None


class LookupResultCreate(LookupResultBase):
    """Schema for creating a lookup result"""
    sources_searched: int = 0
    sources_successful: int = 0
    total_records_found: int = 0
    raw_results: Optional[Dict[str, Any]] = None


class LookupResultSummary(LookupResultBase):
    """Brief summary of a lookup result"""
    id: int
    sources_searched: int
    sources_successful: int
    total_records_found: int
    created_at: datetime

    class Config:
        from_attributes = True


class LookupResultResponse(LookupResultBase):
    """Full lookup result with person records"""
    id: int
    user_id: Optional[int] = None
    sources_searched: int
    sources_successful: int
    total_records_found: int
    created_at: datetime
    person_records: List[PersonRecordResponse] = []

    class Config:
        from_attributes = True


class LookupResultDetail(LookupResultResponse):
    """Detailed lookup result including raw data"""
    raw_results: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============================================================================
# Search Response Schemas
# ============================================================================

class SourceResult(BaseModel):
    """Result from a single data source"""
    source: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str


class SearchResponse(BaseModel):
    """Response from a person search operation"""
    success: bool
    lookup_result_id: Optional[int] = None  # ID of saved result (if saved)
    query: Dict[str, Any]
    sources_searched: int
    sources_successful: int
    total_records_found: int
    results: List[SourceResult]
    timestamp: str


# ============================================================================
# List/Pagination Schemas
# ============================================================================

class LookupResultList(BaseModel):
    """Paginated list of lookup results"""
    items: List[LookupResultSummary]
    total: int
    page: int
    page_size: int
    pages: int
