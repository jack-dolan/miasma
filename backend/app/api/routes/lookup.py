"""
API routes for person lookup operations
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.services.lookup_service import LookupService
from app.schemas.lookup_result import (
    LookupRequest,
    SearchResponse,
    SourceResult,
    LookupResultResponse,
    LookupResultDetail,
    LookupResultList,
    LookupResultSummary,
    PersonRecordResponse
)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_person(
    request: LookupRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    Search for a person across data broker sites

    - **first_name**: Person's first name (required)
    - **last_name**: Person's last name (required)
    - **city**: Optional city to narrow search
    - **state**: Optional state (2-letter code)
    - **age**: Optional age
    - **sources**: Optional list of specific sources to search
    - **save_results**: Whether to save results to database (default: True)
    """
    try:
        # Perform the search
        results = await LookupService.search_person(
            first_name=request.first_name,
            last_name=request.last_name,
            city=request.city,
            state=request.state,
            age=request.age,
            sources=request.sources
        )

        lookup_result_id = None

        # Save results to database if requested
        if request.save_results and results.get("success"):
            lookup_result = await LookupService.save_lookup_result(
                db=db,
                search_results=results,
                user_id=user_id
            )
            lookup_result_id = lookup_result.id

        # Build response
        return SearchResponse(
            success=results.get("success", False),
            lookup_result_id=lookup_result_id,
            query=results.get("query", {}),
            sources_searched=results.get("sources_searched", 0),
            sources_successful=results.get("sources_successful", 0),
            total_records_found=results.get("total_records_found", 0),
            results=[
                SourceResult(
                    source=r.get("source", "unknown"),
                    success=r.get("success", False),
                    data=r.get("data"),
                    error=r.get("error"),
                    timestamp=r.get("timestamp", "")
                )
                for r in results.get("results", [])
            ],
            timestamp=results.get("timestamp", "")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_sources():
    """Get list of available data sources and their status"""
    sources = LookupService.get_available_sources()
    return {"sources": sources}


@router.get("/results", response_model=LookupResultList)
async def list_lookup_results(
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    first_name: Optional[str] = Query(None, description="Filter by first name"),
    last_name: Optional[str] = Query(None, description="Filter by last name")
):
    """
    Get paginated list of stored lookup results

    Returns lookup results with summary information.
    Use GET /results/{id} for full details including person records.
    """
    result = await LookupService.get_lookup_results(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        first_name=first_name,
        last_name=last_name
    )

    return LookupResultList(
        items=[
            LookupResultSummary(
                id=item.id,
                first_name=item.first_name,
                last_name=item.last_name,
                city=item.city,
                state=item.state,
                age=item.age,
                sources_searched=item.sources_searched,
                sources_successful=item.sources_successful,
                total_records_found=item.total_records_found,
                created_at=item.created_at
            )
            for item in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        pages=result["pages"]
    )


@router.get("/results/{lookup_id}", response_model=LookupResultResponse)
async def get_lookup_result(
    lookup_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    Get a specific lookup result by ID

    Returns the lookup result with all associated person records.
    """
    lookup_result = await LookupService.get_lookup_result(
        db=db,
        lookup_id=lookup_id,
        user_id=user_id
    )

    if not lookup_result:
        raise HTTPException(status_code=404, detail="Lookup result not found")

    return LookupResultResponse(
        id=lookup_result.id,
        user_id=lookup_result.user_id,
        first_name=lookup_result.first_name,
        last_name=lookup_result.last_name,
        city=lookup_result.city,
        state=lookup_result.state,
        age=lookup_result.age,
        sources_searched=lookup_result.sources_searched,
        sources_successful=lookup_result.sources_successful,
        total_records_found=lookup_result.total_records_found,
        created_at=lookup_result.created_at,
        person_records=[
            PersonRecordResponse(
                id=record.id,
                source=record.source,
                name=record.name,
                age=record.age,
                location=record.location,
                addresses=record.addresses,
                phone_numbers=record.phone_numbers,
                emails=record.emails,
                relatives=record.relatives,
                profile_url=record.profile_url,
                created_at=record.created_at
            )
            for record in lookup_result.person_records
        ]
    )


@router.get("/results/{lookup_id}/detail", response_model=LookupResultDetail)
async def get_lookup_result_detail(
    lookup_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """
    Get detailed lookup result including raw data

    Returns the full lookup result with raw scraper responses.
    """
    lookup_result = await LookupService.get_lookup_result(
        db=db,
        lookup_id=lookup_id,
        user_id=user_id
    )

    if not lookup_result:
        raise HTTPException(status_code=404, detail="Lookup result not found")

    return LookupResultDetail(
        id=lookup_result.id,
        user_id=lookup_result.user_id,
        first_name=lookup_result.first_name,
        last_name=lookup_result.last_name,
        city=lookup_result.city,
        state=lookup_result.state,
        age=lookup_result.age,
        sources_searched=lookup_result.sources_searched,
        sources_successful=lookup_result.sources_successful,
        total_records_found=lookup_result.total_records_found,
        created_at=lookup_result.created_at,
        raw_results=lookup_result.raw_results,
        person_records=[
            PersonRecordResponse(
                id=record.id,
                source=record.source,
                name=record.name,
                age=record.age,
                location=record.location,
                addresses=record.addresses,
                phone_numbers=record.phone_numbers,
                emails=record.emails,
                relatives=record.relatives,
                profile_url=record.profile_url,
                created_at=record.created_at
            )
            for record in lookup_result.person_records
        ]
    )


@router.delete("/results/{lookup_id}")
async def delete_lookup_result(
    lookup_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id)
):
    """Delete a lookup result and all associated person records"""
    deleted = await LookupService.delete_lookup_result(
        db=db,
        lookup_id=lookup_id,
        user_id=user_id
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Lookup result not found")

    return {"message": "Lookup result deleted", "id": lookup_id}
