"""
Campaign service for managing data poisoning campaigns
"""

import logging
from typing import Dict, Optional, Any, List

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


class CampaignService:
    """Service for campaign CRUD and execution"""

    VALID_STATUSES = {s.value for s in CampaignStatus}
    ALLOWED_TRANSITIONS = {
        "draft": {"scheduled", "running"},
        "scheduled": {"running", "paused", "draft"},
        "running": {"paused", "completed", "failed"},
        "paused": {"running", "draft"},
        "completed": {"draft"},
        "failed": {"draft"},
    }

    @classmethod
    async def create_campaign(
        cls,
        db: AsyncSession,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        target_sites: Optional[List[str]] = None,
        target_count: int = 10,
    ) -> Campaign:
        """Create a new campaign"""

        # Check user campaign limit
        count_query = select(func.count(Campaign.id)).where(Campaign.user_id == user_id)
        result = await db.execute(count_query)
        current_count = result.scalar() or 0

        if current_count >= settings.MAX_CAMPAIGNS_PER_USER:
            raise ValueError(f"Campaign limit reached ({settings.MAX_CAMPAIGNS_PER_USER})")

        campaign = Campaign(
            user_id=user_id,
            name=name,
            description=description,
            target_sites=target_sites,
            target_count=min(target_count, settings.MAX_SUBMISSIONS_PER_CAMPAIGN),
            status=CampaignStatus.DRAFT,
        )

        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)

        logger.info(f"Created campaign {campaign.id} for user {user_id}")
        return campaign

    @classmethod
    async def get_campaign(
        cls,
        db: AsyncSession,
        campaign_id: int,
        user_id: int,
    ) -> Optional[Campaign]:
        """Get a single campaign by ID (scoped to user)"""

        query = select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def list_campaigns(
        cls,
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List campaigns for a user with pagination"""

        query = select(Campaign).where(Campaign.user_id == user_id)
        count_query = select(func.count(Campaign.id)).where(Campaign.user_id == user_id)

        if status_filter and status_filter in cls.VALID_STATUSES:
            query = query.where(Campaign.status == status_filter)
            count_query = count_query.where(Campaign.status == status_filter)

        # Total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginated results
        offset = (page - 1) * page_size
        query = query.order_by(desc(Campaign.updated_at)).offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    @classmethod
    async def update_campaign(
        cls,
        db: AsyncSession,
        campaign_id: int,
        user_id: int,
        **updates,
    ) -> Optional[Campaign]:
        """Update a campaign"""

        campaign = await cls.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Handle status transitions
        if "status" in updates and updates["status"] is not None:
            new_status = updates["status"]
            current = campaign.status.value if isinstance(campaign.status, CampaignStatus) else campaign.status
            allowed = cls.ALLOWED_TRANSITIONS.get(current, set())

            if new_status not in allowed:
                raise ValueError(f"Cannot transition from '{current}' to '{new_status}'")

            campaign.status = new_status

        # Update other fields
        for field in ("name", "description", "target_sites", "target_count"):
            if field in updates and updates[field] is not None:
                setattr(campaign, field, updates[field])

        await db.commit()
        await db.refresh(campaign)

        logger.info(f"Updated campaign {campaign_id}")
        return campaign

    @classmethod
    async def delete_campaign(
        cls,
        db: AsyncSession,
        campaign_id: int,
        user_id: int,
    ) -> bool:
        """Delete a campaign"""

        campaign = await cls.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return False

        await db.delete(campaign)
        await db.commit()

        logger.info(f"Deleted campaign {campaign_id}")
        return True

    @classmethod
    async def get_campaign_stats(
        cls,
        db: AsyncSession,
        user_id: int,
    ) -> Dict[str, Any]:
        """Get aggregate stats for a user's campaigns"""

        query = select(Campaign).where(Campaign.user_id == user_id)
        result = await db.execute(query)
        campaigns = result.scalars().all()

        total = len(campaigns)
        active = sum(1 for c in campaigns if c.status in (CampaignStatus.RUNNING, CampaignStatus.SCHEDULED))
        completed_count = sum(c.submissions_completed for c in campaigns)
        failed_count = sum(c.submissions_failed for c in campaigns)

        total_submissions = completed_count + failed_count
        success_rate = (completed_count / total_submissions * 100) if total_submissions > 0 else 0

        return {
            "total_campaigns": total,
            "active_campaigns": active,
            "total_submissions": completed_count,
            "failed_submissions": failed_count,
            "success_rate": round(success_rate, 1),
        }
