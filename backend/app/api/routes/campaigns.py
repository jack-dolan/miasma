"""
Campaign routes for managing data poisoning campaigns
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_required_user_id
from app.services.campaign_service import CampaignService
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignList,
)

router = APIRouter()


@router.get("/", response_model=CampaignList)
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
):
    """List all campaigns for the current user"""
    result = await CampaignService.list_campaigns(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        status_filter=status,
    )

    return CampaignList(
        items=[
            CampaignResponse(
                id=c.id,
                user_id=c.user_id,
                name=c.name,
                description=c.description,
                status=c.status.value if hasattr(c.status, 'value') else c.status,
                target_sites=c.target_sites,
                target_count=c.target_count,
                submissions_completed=c.submissions_completed,
                submissions_failed=c.submissions_failed,
                last_execution=c.last_execution,
                next_execution=c.next_execution,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        pages=result["pages"],
    )


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Create a new campaign"""
    try:
        campaign = await CampaignService.create_campaign(
            db=db,
            user_id=user_id,
            name=data.name,
            description=data.description,
            target_sites=data.target_sites,
            target_count=data.target_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CampaignResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value if hasattr(campaign.status, 'value') else campaign.status,
        target_sites=campaign.target_sites,
        target_count=campaign.target_count,
        submissions_completed=campaign.submissions_completed,
        submissions_failed=campaign.submissions_failed,
        last_execution=campaign.last_execution,
        next_execution=campaign.next_execution,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Get a specific campaign"""
    campaign = await CampaignService.get_campaign(db, campaign_id, user_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value if hasattr(campaign.status, 'value') else campaign.status,
        target_sites=campaign.target_sites,
        target_count=campaign.target_count,
        submissions_completed=campaign.submissions_completed,
        submissions_failed=campaign.submissions_failed,
        last_execution=campaign.last_execution,
        next_execution=campaign.next_execution,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Update a campaign"""
    try:
        campaign = await CampaignService.update_campaign(
            db=db,
            campaign_id=campaign_id,
            user_id=user_id,
            **data.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value if hasattr(campaign.status, 'value') else campaign.status,
        target_sites=campaign.target_sites,
        target_count=campaign.target_count,
        submissions_completed=campaign.submissions_completed,
        submissions_failed=campaign.submissions_failed,
        last_execution=campaign.last_execution,
        next_execution=campaign.next_execution,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Delete a campaign"""
    deleted = await CampaignService.delete_campaign(db, campaign_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Campaign deleted", "id": campaign_id}
