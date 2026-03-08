"""
Background campaign execution engine.
Runs campaigns as asyncio tasks, generating fake profiles and submitting them to broker sites.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.models.submission import Submission, SubmissionStatus
from app.services.data_generator_service import DataGeneratorService
from app.services.submission_engine import get_submitter, SubmissionResult
from app.services.lookup_service import LookupService
from app.services.optout_handlers import get_optout_handler
from app.core.config import settings

logger = logging.getLogger(__name__)


class CampaignExecutor:
    _running_tasks: dict[int, asyncio.Task] = {}

    @classmethod
    async def start_campaign(cls, campaign_id: int, db_session_factory: async_sessionmaker):
        """Kick off campaign execution as a background asyncio task."""
        if campaign_id in cls._running_tasks:
            logger.warning(f"Campaign {campaign_id} is already running")
            return

        task = asyncio.create_task(cls._execute_campaign(campaign_id, db_session_factory))
        cls._running_tasks[campaign_id] = task

        # clean up when done
        def _on_done(t):
            cls._running_tasks.pop(campaign_id, None)

        task.add_done_callback(_on_done)
        logger.info(f"Started campaign {campaign_id}")

    @classmethod
    async def pause_campaign(cls, campaign_id: int):
        """Cancel the running task for a campaign."""
        task = cls._running_tasks.get(campaign_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Paused campaign {campaign_id}")
        else:
            logger.warning(f"No running task for campaign {campaign_id}")

    @classmethod
    async def resume_campaign(cls, campaign_id: int, db_session_factory: async_sessionmaker):
        """Resume a paused campaign - picks up remaining PENDING submissions."""
        if campaign_id in cls._running_tasks:
            logger.warning(f"Campaign {campaign_id} is already running")
            return

        task = asyncio.create_task(cls._resume_campaign(campaign_id, db_session_factory))
        cls._running_tasks[campaign_id] = task

        def _on_done(t):
            cls._running_tasks.pop(campaign_id, None)

        task.add_done_callback(_on_done)
        logger.info(f"Resumed campaign {campaign_id}")

    @classmethod
    def get_running_campaigns(cls) -> list[int]:
        return list(cls._running_tasks.keys())

    @classmethod
    async def _execute_campaign(cls, campaign_id: int, db_session_factory: async_sessionmaker):
        """Main execution loop for a fresh campaign run."""
        try:
            async with db_session_factory() as db:
                campaign = await db.get(Campaign, campaign_id)
                if not campaign:
                    logger.error(f"Campaign {campaign_id} not found")
                    return
                campaign_type = (
                    campaign.campaign_type.value
                    if isinstance(campaign.campaign_type, CampaignType)
                    else campaign.campaign_type
                )

            if campaign_type == CampaignType.OPTOUT.value:
                await cls._execute_optout_campaign(campaign_id, db_session_factory)
            else:
                await cls._execute_poisoning_campaign(campaign_id, db_session_factory)

        except asyncio.CancelledError:
            logger.info(f"Campaign {campaign_id} task cancelled (paused)")
            raise
        except Exception:
            logger.exception(f"Campaign {campaign_id} failed with unrecoverable error")
            try:
                async with db_session_factory() as db:
                    campaign = await db.get(Campaign, campaign_id)
                    if campaign:
                        campaign.status = CampaignStatus.FAILED
                        await db.commit()
            except Exception:
                logger.exception(f"Failed to mark campaign {campaign_id} as failed")

    @classmethod
    async def _execute_poisoning_campaign(cls, campaign_id: int, db_session_factory: async_sessionmaker):
        """Execution path for poisoning campaigns."""
        async with db_session_factory() as db:
            campaign = await db.get(Campaign, campaign_id)
            target_sites = campaign.target_sites or []
            if not target_sites:
                logger.error(f"Campaign {campaign_id} has no target sites")
                campaign.status = CampaignStatus.FAILED
                await db.commit()
                return

            generator = DataGeneratorService()
            if campaign.target_first_name and campaign.target_last_name:
                profiles = generator.generate_poisoning_profiles(
                    first_name=campaign.target_first_name,
                    last_name=campaign.target_last_name,
                    count=campaign.target_count,
                    real_state=campaign.target_state,
                    real_age=campaign.target_age,
                )
            else:
                profiles = generator.generate_profiles(
                    campaign.target_count, campaign.profile_template
                )

            submissions = []
            for profile in profiles:
                for site in target_sites:
                    sub = Submission(
                        campaign_id=campaign_id,
                        site=site,
                        status=SubmissionStatus.PENDING,
                        profile_data=profile,
                    )
                    db.add(sub)
                    submissions.append(sub)

            campaign.last_execution = datetime.now(timezone.utc)
            await db.commit()
            for sub in submissions:
                await db.refresh(sub)

        await cls._process_submission_batch(
            campaign_id=campaign_id,
            db_session_factory=db_session_factory,
            submissions=submissions,
            submit_fn=cls._submit_single,
        )

    @classmethod
    async def _execute_optout_campaign(cls, campaign_id: int, db_session_factory: async_sessionmaker):
        """Execution path for opt-out campaigns: scan -> create -> execute."""
        async with db_session_factory() as db:
            campaign = await db.get(Campaign, campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return

            if not campaign.target_first_name or not campaign.target_last_name:
                campaign.status = CampaignStatus.FAILED
                await db.commit()
                logger.error("Campaign %s missing target name for opt-out scan", campaign_id)
                return

            scan_sources = campaign.target_sites or []
            scan = await LookupService.search_person(
                first_name=campaign.target_first_name,
                last_name=campaign.target_last_name,
                city=campaign.target_city,
                state=campaign.target_state,
                age=campaign.target_age,
                sources=scan_sources if scan_sources else None,
            )

            candidates = []
            for result in scan.get("results", []):
                if not result.get("success"):
                    continue
                records = result.get("data", {}).get("results", [])
                if not records:
                    continue
                source = result.get("source")
                if source:
                    candidates.append(
                        {
                            "site": source,
                            "records_found": len(records),
                            "sample_record": records[0] if records else None,
                        }
                    )

            if not candidates:
                campaign.status = CampaignStatus.FAILED
                campaign.last_execution = datetime.now(timezone.utc)
                await db.commit()
                logger.warning("Campaign %s scan found no opt-out candidates", campaign_id)
                return

            submissions = []
            for candidate in candidates:
                sub = Submission(
                    campaign_id=campaign_id,
                    site=candidate["site"],
                    status=SubmissionStatus.PENDING,
                    profile_data={
                        "first_name": campaign.target_first_name,
                        "last_name": campaign.target_last_name,
                        "age": campaign.target_age,
                        "addresses": (
                            [{"city": campaign.target_city, "state": campaign.target_state}]
                            if campaign.target_city or campaign.target_state
                            else []
                        ),
                        "scan_candidate": candidate,
                    },
                )
                db.add(sub)
                submissions.append(sub)

            campaign.last_execution = datetime.now(timezone.utc)
            await db.commit()
            for sub in submissions:
                await db.refresh(sub)

        await cls._process_submission_batch(
            campaign_id=campaign_id,
            db_session_factory=db_session_factory,
            submissions=submissions,
            submit_fn=cls._submit_single_optout,
        )

    @classmethod
    async def _process_submission_batch(
        cls,
        campaign_id: int,
        db_session_factory: async_sessionmaker,
        submissions: list[Submission],
        submit_fn,
    ):
        """Process a batch of submissions sequentially with pacing and status checks."""
        total = len(submissions)
        if total == 0:
            async with db_session_factory() as db:
                campaign = await db.get(Campaign, campaign_id)
                campaign.status = CampaignStatus.COMPLETED
                await db.commit()
            return

        delay_per_sub = (settings.CAMPAIGN_EXECUTION_DELAY_HOURS * 3600) / total

        for sub in submissions:
            if asyncio.current_task().cancelled():
                return

            async with db_session_factory() as db:
                campaign = await db.get(Campaign, campaign_id)
                if campaign.status not in (CampaignStatus.RUNNING,):
                    logger.info(f"Campaign {campaign_id} is no longer running, stopping")
                    return

            await submit_fn(sub.id, db_session_factory)

            jitter = delay_per_sub * random.uniform(-0.2, 0.2)
            wait = max(0, delay_per_sub + jitter)
            if wait > 0:
                await asyncio.sleep(wait)

        async with db_session_factory() as db:
            campaign = await db.get(Campaign, campaign_id)
            if campaign.status == CampaignStatus.RUNNING:
                campaign.status = CampaignStatus.COMPLETED
                await db.commit()
                logger.info(f"Campaign {campaign_id} completed")

    @classmethod
    async def _resume_campaign(cls, campaign_id: int, db_session_factory: async_sessionmaker):
        """Resume processing - pick up PENDING submissions."""
        try:
            async with db_session_factory() as db:
                result = await db.execute(
                    select(Submission)
                    .where(
                        Submission.campaign_id == campaign_id,
                        Submission.status == SubmissionStatus.PENDING,
                    )
                    .order_by(Submission.id)
                )
                pending = result.scalars().all()

            if not pending:
                async with db_session_factory() as db:
                    campaign = await db.get(Campaign, campaign_id)
                    campaign.status = CampaignStatus.COMPLETED
                    await db.commit()
                logger.info(f"Campaign {campaign_id} has no pending submissions, marking complete")
                return

            total = len(pending)
            delay_per_sub = (settings.CAMPAIGN_EXECUTION_DELAY_HOURS * 3600) / total

            for sub in pending:
                if asyncio.current_task().cancelled():
                    return

                async with db_session_factory() as db:
                    campaign = await db.get(Campaign, campaign_id)
                    if campaign.status not in (CampaignStatus.RUNNING,):
                        logger.info(f"Campaign {campaign_id} no longer running, stopping resume")
                        return

                await cls._submit_single(sub.id, db_session_factory)

                jitter = delay_per_sub * random.uniform(-0.2, 0.2)
                wait = max(0, delay_per_sub + jitter)
                if wait > 0:
                    await asyncio.sleep(wait)

            async with db_session_factory() as db:
                campaign = await db.get(Campaign, campaign_id)
                if campaign.status == CampaignStatus.RUNNING:
                    campaign.status = CampaignStatus.COMPLETED
                    await db.commit()
                    logger.info(f"Campaign {campaign_id} completed after resume")

        except asyncio.CancelledError:
            logger.info(f"Campaign {campaign_id} resume cancelled (paused)")
            raise
        except Exception:
            logger.exception(f"Campaign {campaign_id} failed during resume")
            try:
                async with db_session_factory() as db:
                    campaign = await db.get(Campaign, campaign_id)
                    if campaign:
                        campaign.status = CampaignStatus.FAILED
                        await db.commit()
            except Exception:
                logger.exception(f"Failed to mark campaign {campaign_id} as failed")

    @classmethod
    async def _submit_single(cls, submission_id: int, db_session_factory: async_sessionmaker):
        """Process a single submission using the submission engine."""
        async with db_session_factory() as db:
            sub = await db.get(Submission, submission_id)
            if not sub or sub.status != SubmissionStatus.PENDING:
                return

            submitter = get_submitter(sub.site)

            if not submitter:
                sub.status = SubmissionStatus.SKIPPED
                sub.error_message = f"No submitter for site: {sub.site}"

                campaign = await db.get(Campaign, sub.campaign_id)
                if campaign:
                    campaign.submissions_failed = (campaign.submissions_failed or 0) + 1

                await db.commit()
                logger.warning(f"Submission {submission_id} skipped: no submitter for {sub.site}")
                return

            try:
                result = await asyncio.wait_for(
                    submitter.execute(sub.profile_data),
                    timeout=120,
                )

                if result.success:
                    sub.status = SubmissionStatus.SUBMITTED
                    sub.submitted_at = datetime.now(timezone.utc)
                    sub.reference_id = result.reference_id

                    campaign = await db.get(Campaign, sub.campaign_id)
                    if campaign:
                        campaign.submissions_completed = (campaign.submissions_completed or 0) + 1
                else:
                    sub.status = SubmissionStatus.FAILED
                    sub.error_message = (result.error or "Unknown error")[:500]

                    campaign = await db.get(Campaign, sub.campaign_id)
                    if campaign:
                        campaign.submissions_failed = (campaign.submissions_failed or 0) + 1

                await db.commit()

            except asyncio.TimeoutError:
                await db.rollback()
                sub.status = SubmissionStatus.FAILED
                sub.error_message = "Submission timed out after 120s"

                campaign = await db.get(Campaign, sub.campaign_id)
                if campaign:
                    campaign.submissions_failed = (campaign.submissions_failed or 0) + 1

                await db.commit()
                logger.warning(f"Submission {submission_id} timed out")

            except Exception as e:
                await db.rollback()
                sub.status = SubmissionStatus.FAILED
                sub.error_message = str(e)[:500]

                campaign = await db.get(Campaign, sub.campaign_id)
                if campaign:
                    campaign.submissions_failed = (campaign.submissions_failed or 0) + 1

                await db.commit()
                logger.warning(f"Submission {submission_id} failed: {e}")

    @classmethod
    async def _submit_single_optout(cls, submission_id: int, db_session_factory: async_sessionmaker):
        """Process a single opt-out submission using site opt-out handlers."""
        async with db_session_factory() as db:
            sub = await db.get(Submission, submission_id)
            if not sub or sub.status != SubmissionStatus.PENDING:
                return

            handler = get_optout_handler(sub.site)
            if not handler:
                sub.status = SubmissionStatus.SKIPPED
                sub.error_message = f"No opt-out handler for site: {sub.site}"
                campaign = await db.get(Campaign, sub.campaign_id)
                if campaign:
                    campaign.submissions_failed = (campaign.submissions_failed or 0) + 1
                await db.commit()
                return

            try:
                result = await asyncio.wait_for(
                    handler.execute(sub.profile_data or {}),
                    timeout=180,
                )
                if result.success and result.removed:
                    sub.status = SubmissionStatus.REMOVED
                    sub.submitted_at = datetime.now(timezone.utc)
                    sub.reference_id = result.reference_id
                    campaign = await db.get(Campaign, sub.campaign_id)
                    if campaign:
                        campaign.submissions_completed = (campaign.submissions_completed or 0) + 1
                else:
                    sub.status = SubmissionStatus.FAILED
                    sub.error_message = (result.error or "Opt-out failed")[:500]
                    campaign = await db.get(Campaign, sub.campaign_id)
                    if campaign:
                        campaign.submissions_failed = (campaign.submissions_failed or 0) + 1

                await db.commit()
            except asyncio.TimeoutError:
                await db.rollback()
                sub.status = SubmissionStatus.FAILED
                sub.error_message = "Opt-out timed out after 180s"
                campaign = await db.get(Campaign, sub.campaign_id)
                if campaign:
                    campaign.submissions_failed = (campaign.submissions_failed or 0) + 1
                await db.commit()
            except Exception as e:
                await db.rollback()
                sub.status = SubmissionStatus.FAILED
                sub.error_message = str(e)[:500]
                campaign = await db.get(Campaign, sub.campaign_id)
                if campaign:
                    campaign.submissions_failed = (campaign.submissions_failed or 0) + 1
                await db.commit()
