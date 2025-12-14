from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.lookup_service import LookupService

router = APIRouter()


class LookupRequest(BaseModel):
    first_name: str
    last_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    age: Optional[int] = None
    sources: Optional[List[str]] = None


@router.post("/search")
async def search_person(request: LookupRequest):
    """Search for a person across data broker sites"""
    try:
        results = await LookupService.search_person(
            first_name=request.first_name,
            last_name=request.last_name,
            city=request.city,
            state=request.state,
            age=request.age,
            sources=request.sources
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_sources():
    """Get list of available data sources"""
    sources = LookupService.get_available_sources()
    return {"sources": sources}