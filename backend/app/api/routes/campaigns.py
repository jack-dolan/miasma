"""
Campaign routes for managing data poisoning campaigns
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_required_user_id
from app.services.campaign_service import CampaignService
from app.services.campaign_executor import CampaignExecutor
from app.services.lookup_service import LookupService
from app.services.accuracy_service import AccuracyService
from app.core.database import AsyncSessionLocal
from app.models.submission import Submission, SubmissionStatus
from app.models.campaign_baseline import CampaignBaseline
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignList,
)
from app.schemas.submission import SubmissionResponse, SubmissionList
from app.schemas.campaign_baseline import (
    BaselineResponse,
    BaselineDetailResponse,
    BaselineListResponse,
    AccuracyComparison,
)

router = APIRouter()


def _campaign_response(c) -> CampaignResponse:
    return CampaignResponse(
        id=c.id,
        user_id=c.user_id,
        name=c.name,
        description=c.description,
        status=c.status.value if hasattr(c.status, 'value') else c.status,
        target_first_name=c.target_first_name,
        target_last_name=c.target_last_name,
        target_city=c.target_city,
        target_state=c.target_state,
        target_age=c.target_age,
        target_sites=c.target_sites,
        target_count=c.target_count,
        submissions_completed=c.submissions_completed,
        submissions_failed=c.submissions_failed,
        last_execution=c.last_execution,
        next_execution=c.next_execution,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


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
        items=[_campaign_response(c) for c in result["items"]],
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
            target_first_name=data.target_first_name,
            target_last_name=data.target_last_name,
            target_city=data.target_city,
            target_state=data.target_state,
            target_age=data.target_age,
            target_sites=data.target_sites,
            target_count=data.target_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _campaign_response(campaign)


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

    return _campaign_response(campaign)


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

    return _campaign_response(campaign)


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


@router.post("/{campaign_id}/execute", status_code=202)
async def execute_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Start executing a campaign"""
    try:
        campaign = await CampaignService.update_campaign(
            db=db,
            campaign_id=campaign_id,
            user_id=user_id,
            status="running",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await CampaignExecutor.start_campaign(campaign_id, AsyncSessionLocal)

    return {"message": "Campaign execution started", "campaign_id": campaign_id}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Pause a running campaign"""
    try:
        campaign = await CampaignService.update_campaign(
            db=db,
            campaign_id=campaign_id,
            user_id=user_id,
            status="paused",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await CampaignExecutor.pause_campaign(campaign_id)

    return {"message": "Campaign paused", "campaign_id": campaign_id}


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Resume a paused campaign"""
    try:
        campaign = await CampaignService.update_campaign(
            db=db,
            campaign_id=campaign_id,
            user_id=user_id,
            status="running",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await CampaignExecutor.resume_campaign(campaign_id, AsyncSessionLocal)

    return {"message": "Campaign resumed", "campaign_id": campaign_id}


@router.get("/{campaign_id}/submissions", response_model=SubmissionList)
async def list_submissions(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List submissions for a campaign"""
    # make sure campaign belongs to user
    campaign = await CampaignService.get_campaign(db, campaign_id, user_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # count
    count_q = select(func.count(Submission.id)).where(Submission.campaign_id == campaign_id)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # fetch page
    offset = (page - 1) * page_size
    q = (
        select(Submission)
        .where(Submission.campaign_id == campaign_id)
        .order_by(Submission.id)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    items = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 0

    return SubmissionList(
        items=[
            SubmissionResponse(
                id=s.id,
                campaign_id=s.campaign_id,
                site=s.site,
                status=s.status.value if hasattr(s.status, "value") else s.status,
                profile_data=s.profile_data,
                reference_id=s.reference_id,
                error_message=s.error_message,
                submitted_at=s.submitted_at,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# Baseline & accuracy tracking
# ---------------------------------------------------------------------------

def _baseline_response(b: CampaignBaseline) -> BaselineResponse:
    return BaselineResponse(
        id=b.id,
        campaign_id=b.campaign_id,
        snapshot_type=b.snapshot_type,
        taken_at=b.taken_at,
        sources_checked=b.sources_checked,
        records_found=b.records_found,
        accuracy_score=b.accuracy_score,
        data_points_total=b.data_points_total,
        data_points_accurate=b.data_points_accurate,
    )


async def _take_snapshot(
    campaign_id: int,
    snapshot_type: str,
    db: AsyncSession,
    user_id: int,
) -> CampaignBaseline:
    """Run scrapers against the campaign target and store a baseline snapshot."""
    campaign = await CampaignService.get_campaign(db, campaign_id, user_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not campaign.target_first_name or not campaign.target_last_name:
        raise HTTPException(
            status_code=400,
            detail="Campaign must have target first and last name set",
        )

    # Run the lookup
    search_results = await LookupService.search_person(
        first_name=campaign.target_first_name,
        last_name=campaign.target_last_name,
        city=campaign.target_city,
        state=campaign.target_state,
        age=campaign.target_age,
    )

    # Build real_info from campaign target fields
    real_info = {
        "first_name": campaign.target_first_name,
        "last_name": campaign.target_last_name,
        "city": campaign.target_city,
        "state": campaign.target_state,
        "age": campaign.target_age,
    }

    # Score accuracy
    accuracy = AccuracyService.calculate_accuracy(
        search_results.get("results", []),
        real_info,
    )

    baseline = CampaignBaseline(
        campaign_id=campaign_id,
        snapshot_type=snapshot_type,
        sources_checked=search_results.get("sources_searched", 0),
        records_found=search_results.get("total_records_found", 0),
        raw_results=search_results,
        accuracy_score=accuracy["accuracy_score"],
        data_points_total=accuracy["data_points_total"],
        data_points_accurate=accuracy["data_points_accurate"],
    )

    db.add(baseline)
    await db.commit()
    await db.refresh(baseline)
    return baseline


@router.post("/{campaign_id}/baseline", response_model=BaselineResponse, status_code=201)
async def take_baseline(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Take a baseline snapshot of what data brokers currently have"""
    baseline = await _take_snapshot(campaign_id, "baseline", db, user_id)
    return _baseline_response(baseline)


@router.post("/{campaign_id}/check", response_model=BaselineResponse, status_code=201)
async def take_check(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Take a follow-up check to see if accuracy has changed"""
    baseline = await _take_snapshot(campaign_id, "check", db, user_id)
    return _baseline_response(baseline)


@router.get("/{campaign_id}/baselines", response_model=BaselineListResponse)
async def list_baselines(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """List all snapshots for a campaign"""
    campaign = await CampaignService.get_campaign(db, campaign_id, user_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = (
        select(CampaignBaseline)
        .where(CampaignBaseline.campaign_id == campaign_id)
        .order_by(CampaignBaseline.taken_at)
    )
    result = await db.execute(query)
    baselines = result.scalars().all()

    return BaselineListResponse(
        baselines=[_baseline_response(b) for b in baselines],
    )


@router.get("/{campaign_id}/accuracy", response_model=AccuracyComparison)
async def get_accuracy(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Get accuracy comparison between baseline and latest check"""
    campaign = await CampaignService.get_campaign(db, campaign_id, user_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get the first baseline
    baseline_q = (
        select(CampaignBaseline)
        .where(
            CampaignBaseline.campaign_id == campaign_id,
            CampaignBaseline.snapshot_type == "baseline",
        )
        .order_by(CampaignBaseline.taken_at)
        .limit(1)
    )
    baseline_result = await db.execute(baseline_q)
    baseline = baseline_result.scalar_one_or_none()

    # Get the latest check
    check_q = (
        select(CampaignBaseline)
        .where(
            CampaignBaseline.campaign_id == campaign_id,
            CampaignBaseline.snapshot_type == "check",
        )
        .order_by(CampaignBaseline.taken_at.desc())
        .limit(1)
    )
    check_result = await db.execute(check_q)
    latest_check = check_result.scalar_one_or_none()

    # Count all checks
    count_q = (
        select(func.count(CampaignBaseline.id))
        .where(
            CampaignBaseline.campaign_id == campaign_id,
            CampaignBaseline.snapshot_type == "check",
        )
    )
    count_result = await db.execute(count_q)
    checks_count = count_result.scalar() or 0

    # Calculate change
    accuracy_change = None
    if baseline and latest_check and baseline.accuracy_score is not None and latest_check.accuracy_score is not None:
        accuracy_change = round(latest_check.accuracy_score - baseline.accuracy_score, 1)

    return AccuracyComparison(
        baseline=_baseline_response(baseline) if baseline else None,
        latest_check=_baseline_response(latest_check) if latest_check else None,
        accuracy_change=accuracy_change,
        checks_count=checks_count,
    )


@router.get("/{campaign_id}/baselines/{baseline_id}", response_model=BaselineDetailResponse)
async def get_baseline_detail(
    campaign_id: int,
    baseline_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_required_user_id),
):
    """Get detailed snapshot including raw scraper results"""
    campaign = await CampaignService.get_campaign(db, campaign_id, user_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = select(CampaignBaseline).where(
        CampaignBaseline.id == baseline_id,
        CampaignBaseline.campaign_id == campaign_id,
    )
    result = await db.execute(query)
    baseline = result.scalar_one_or_none()

    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    return BaselineDetailResponse(
        id=baseline.id,
        campaign_id=baseline.campaign_id,
        snapshot_type=baseline.snapshot_type,
        taken_at=baseline.taken_at,
        sources_checked=baseline.sources_checked,
        records_found=baseline.records_found,
        accuracy_score=baseline.accuracy_score,
        data_points_total=baseline.data_points_total,
        data_points_accurate=baseline.data_points_accurate,
        raw_results=baseline.raw_results,
    )
