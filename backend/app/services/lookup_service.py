"""
Lookup service for coordinating data broker searches
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.scrapers.truepeoplesearch import TruePeopleSearchScraper
from app.scrapers.fastpeoplesearch import FastPeopleSearchScraper
from app.scrapers.nuwber import NuwberScraper
from app.scrapers.cyberbackgroundchecks import CyberBackgroundChecksScraper
from app.scrapers.usphonebook import USPhoneBookScraper
from app.scrapers.radaris import RadarisScraper
from app.scrapers.thatsthem import ThatsThemScraper
from app.scrapers.fastbackgroundcheck import FastBackgroundCheckScraper
from app.scrapers.voterrecords import VoterRecordsScraper
from app.scrapers.base import ScraperResult

# Stealth scraper - optional, needs seleniumbase installed
try:
    from app.scrapers.cyberbackgroundchecks_stealth import CyberBackgroundChecksStealthScraper
    _HAS_STEALTH = True
except ImportError:
    _HAS_STEALTH = False
from app.core.config import settings
from app.models.lookup_result import LookupResult, PersonRecord

logger = logging.getLogger(__name__)


# Scraper registry with metadata
SCRAPER_REGISTRY = {
    "truepeoplesearch": {
        "class": TruePeopleSearchScraper,
        "display_name": "TruePeopleSearch",
        "config_key": "ENABLE_TRUEPEOPLESEARCH",
        "block_reason": "CAPTCHA protection",
    },
    "fastpeoplesearch": {
        "class": FastPeopleSearchScraper,
        "display_name": "FastPeopleSearch",
        "config_key": "ENABLE_FASTPEOPLESEARCH",
        "block_reason": "CAPTCHA protection",
    },
    "nuwber": {
        "class": NuwberScraper,
        "display_name": "Nuwber",
        "config_key": "ENABLE_NUWBER",
        "block_reason": "Cloudflare protection",
    },
    "cyberbackgroundchecks": {
        "class": CyberBackgroundChecksScraper,
        "display_name": "CyberBackgroundChecks",
        "config_key": "ENABLE_CYBERBACKGROUNDCHECKS",
        "block_reason": "Bot detection",
    },
    "usphonebook": {
        "class": USPhoneBookScraper,
        "display_name": "USPhoneBook",
        "config_key": "ENABLE_USPHONEBOOK",
        "block_reason": "Cloudflare protection",
    },
    "radaris": {
        "class": RadarisScraper,
        "display_name": "Radaris",
        "config_key": "ENABLE_RADARIS",
        "block_reason": None,
    },
    "thatsthem": {
        "class": ThatsThemScraper,
        "display_name": "ThatsThem",
        "config_key": "ENABLE_THATSTHEM",
        "block_reason": None,
    },
    "fastbackgroundcheck": {
        "class": FastBackgroundCheckScraper,
        "display_name": "FastBackgroundCheck",
        "config_key": "ENABLE_FASTBACKGROUNDCHECK",
        "block_reason": "Cloudflare protection",
    },
    "voterrecords": {
        "class": VoterRecordsScraper,
        "display_name": "VoterRecords",
        "config_key": "ENABLE_VOTERRECORDS",
        "block_reason": "Cloudflare protection",
    },
}

# Add stealth scraper if available
if _HAS_STEALTH:
    SCRAPER_REGISTRY["cyberbackgroundchecks_stealth"] = {
        "class": CyberBackgroundChecksStealthScraper,
        "display_name": "CyberBackgroundChecks (Stealth)",
        "config_key": "ENABLE_CYBERBACKGROUNDCHECKS_STEALTH",
        "block_reason": None,
    }


class LookupService:
    """Service for performing data lookups across multiple sources"""

    SCRAPERS = {k: v["class"] for k, v in SCRAPER_REGISTRY.items()}

    @classmethod
    async def search_person(
        cls,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Search for a person across specified data sources"""

        if sources is None:
            sources = cls._get_enabled_sources()
        else:
            sources = [s for s in sources if s in cls.SCRAPERS]

        if not sources:
            return {
                "success": False,
                "error": "No valid sources specified",
                "results": []
            }

        logger.info(f"Starting lookup for {first_name} {last_name} across {len(sources)} sources")

        results = []
        for source_name in sources:
            try:
                result = await cls._search_source(
                    source_name=source_name,
                    first_name=first_name,
                    last_name=last_name,
                    city=city,
                    state=state,
                    age=age
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Error searching {source_name}: {e}")
                results.append({
                    "source": source_name,
                    "success": False,
                    "error": str(e),
                    "data": {},
                    "timestamp": datetime.utcnow().isoformat()
                })

        successful_sources = [r for r in results if r.get("success")]
        total_records_found = sum(
            len(r.get("data", {}).get("results", []))
            for r in successful_sources
        )

        return {
            "success": True,
            "query": {
                "first_name": first_name,
                "last_name": last_name,
                "city": city,
                "state": state,
                "age": age
            },
            "sources_searched": len(sources),
            "sources_successful": len(successful_sources),
            "total_records_found": total_records_found,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    async def _search_source(
        cls,
        source_name: str,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute search on a single source"""

        scraper_class = cls.SCRAPERS.get(source_name)
        if not scraper_class:
            raise ValueError(f"Unknown source: {source_name}")

        scraper = scraper_class()
        result: ScraperResult = await scraper.scrape(
            first_name=first_name,
            last_name=last_name,
            city=city,
            state=state,
            age=age
        )

        return result.to_dict()

    @classmethod
    def _get_enabled_sources(cls) -> List[str]:
        """Get list of enabled sources from config"""
        enabled = []
        for name, meta in SCRAPER_REGISTRY.items():
            if getattr(settings, meta["config_key"], False):
                enabled.append(name)
        return enabled

    @classmethod
    def get_available_sources(cls) -> List[Dict[str, Any]]:
        """Get list of available data sources with status info"""
        sources = []
        for name, meta in SCRAPER_REGISTRY.items():
            enabled = getattr(settings, meta["config_key"], False)
            sources.append({
                "name": name,
                "display_name": meta["display_name"],
                "enabled": enabled,
                "block_reason": meta["block_reason"] if not enabled else None,
            })
        return sources

    # =========================================================================
    # Database Operations
    # =========================================================================

    @classmethod
    async def save_lookup_result(
        cls,
        db: AsyncSession,
        search_results: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> LookupResult:
        """Save lookup results to the database"""
        query = search_results.get("query", {})

        lookup_result = LookupResult(
            user_id=user_id,
            first_name=query.get("first_name", ""),
            last_name=query.get("last_name", ""),
            city=query.get("city"),
            state=query.get("state"),
            age=query.get("age"),
            sources_searched=search_results.get("sources_searched", 0),
            sources_successful=search_results.get("sources_successful", 0),
            total_records_found=search_results.get("total_records_found", 0),
            raw_results=search_results.get("results", [])
        )

        db.add(lookup_result)
        await db.flush()

        for source_result in search_results.get("results", []):
            if not source_result.get("success"):
                continue

            source_name = source_result.get("source", "unknown")
            data = source_result.get("data", {})
            records = data.get("results", [])

            for record in records:
                person_record = PersonRecord(
                    lookup_result_id=lookup_result.id,
                    source=source_name,
                    name=record.get("name"),
                    age=record.get("age"),
                    location=record.get("location"),
                    addresses=record.get("addresses", []),
                    phone_numbers=record.get("phone_numbers", []),
                    emails=record.get("emails", []),
                    relatives=record.get("relatives", []),
                    profile_url=record.get("profile_url"),
                    raw_data=record
                )
                db.add(person_record)

        await db.commit()
        await db.refresh(lookup_result)

        logger.info(f"Saved lookup result {lookup_result.id} with {lookup_result.total_records_found} records")
        return lookup_result

    @classmethod
    async def get_lookup_result(
        cls,
        db: AsyncSession,
        lookup_id: int,
        user_id: Optional[int] = None
    ) -> Optional[LookupResult]:
        """Get a lookup result by ID"""
        query = select(LookupResult).options(
            selectinload(LookupResult.person_records)
        ).where(LookupResult.id == lookup_id)

        if user_id is not None:
            query = query.where(LookupResult.user_id == user_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_lookup_results(
        cls,
        db: AsyncSession,
        user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of lookup results"""
        query = select(LookupResult).options(
            selectinload(LookupResult.person_records)
        )
        count_query = select(func.count(LookupResult.id))

        if user_id is not None:
            query = query.where(LookupResult.user_id == user_id)
            count_query = count_query.where(LookupResult.user_id == user_id)

        if first_name:
            query = query.where(LookupResult.first_name.ilike(f"%{first_name}%"))
            count_query = count_query.where(LookupResult.first_name.ilike(f"%{first_name}%"))

        if last_name:
            query = query.where(LookupResult.last_name.ilike(f"%{last_name}%"))
            count_query = count_query.where(LookupResult.last_name.ilike(f"%{last_name}%"))

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(desc(LookupResult.created_at)).offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }

    @classmethod
    async def delete_lookup_result(
        cls,
        db: AsyncSession,
        lookup_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """Delete a lookup result"""
        lookup_result = await cls.get_lookup_result(db, lookup_id, user_id)
        if not lookup_result:
            return False

        await db.delete(lookup_result)
        await db.commit()
        logger.info(f"Deleted lookup result {lookup_id}")
        return True
