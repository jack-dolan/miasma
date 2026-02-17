"""
Analytics routes for dashboard metrics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db, get_required_user_id
from app.models.campaign import Campaign, CampaignStatus
from app.models.lookup_result import LookupResult, PersonRecord

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Get dashboard metrics for the current user"""

    # Data sources found (unique sources across all lookups)
    sources_query = (
        select(func.count(func.distinct(PersonRecord.source)))
        .join(LookupResult)
        .where(LookupResult.user_id == user_id)
    )
    sources_result = await db.execute(sources_query)
    sources_found = sources_result.scalar() or 0

    # Campaign stats
    campaign_query = select(Campaign).where(Campaign.user_id == user_id)
    campaign_result = await db.execute(campaign_query)
    campaigns = campaign_result.scalars().all()

    active_campaigns = sum(
        1 for c in campaigns
        if c.status in (CampaignStatus.RUNNING, CampaignStatus.SCHEDULED)
    )

    total_submissions = sum(c.submissions_completed for c in campaigns)
    total_failed = sum(c.submissions_failed for c in campaigns)
    total_attempted = total_submissions + total_failed
    success_rate = round(total_submissions / total_attempted * 100) if total_attempted > 0 else 0

    # Lookup stats
    lookup_count_query = select(func.count(LookupResult.id)).where(LookupResult.user_id == user_id)
    lookup_result = await db.execute(lookup_count_query)
    total_lookups = lookup_result.scalar() or 0

    records_query = (
        select(func.count(PersonRecord.id))
        .join(LookupResult)
        .where(LookupResult.user_id == user_id)
    )
    records_result = await db.execute(records_query)
    total_records = records_result.scalar() or 0

    # Recent lookups (last 5)
    recent_lookups_query = (
        select(LookupResult)
        .where(LookupResult.user_id == user_id)
        .order_by(LookupResult.created_at.desc())
        .limit(5)
    )
    recent_result = await db.execute(recent_lookups_query)
    recent_lookups = [
        {
            "id": r.id,
            "name": f"{r.first_name} {r.last_name}",
            "sources_searched": r.sources_searched,
            "records_found": r.total_records_found,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_result.scalars().all()
    ]

    # Recent campaigns (last 5)
    recent_campaigns = sorted(campaigns, key=lambda c: c.updated_at, reverse=True)[:5]
    campaign_list = [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status.value if hasattr(c.status, 'value') else c.status,
            "submissions_completed": c.submissions_completed,
        }
        for c in recent_campaigns
    ]

    return {
        "sources_found": sources_found,
        "active_campaigns": active_campaigns,
        "total_submissions": total_submissions,
        "success_rate": success_rate,
        "total_lookups": total_lookups,
        "total_records": total_records,
        "recent_lookups": recent_lookups,
        "recent_campaigns": campaign_list,
    }
