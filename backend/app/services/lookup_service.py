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
from app.scrapers.base import ScraperResult
from app.core.config import settings
from app.models.lookup_result import LookupResult, PersonRecord

logger = logging.getLogger(__name__)


class LookupService:
    """Service for performing data lookups across multiple sources"""
    
    # Registry of available scrapers
    SCRAPERS = {
        "truepeoplesearch": TruePeopleSearchScraper,
        "fastpeoplesearch": FastPeopleSearchScraper,
        "nuwber": NuwberScraper,
        "cyberbackgroundchecks": CyberBackgroundChecksScraper,
        "usphonebook": USPhoneBookScraper,
        "radaris": RadarisScraper,
    }
    
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
        """
        Search for a person across specified data sources
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            city: Optional city
            state: Optional state
            age: Optional age
            sources: List of source names to search (default: all enabled)
        
        Returns:
            Dictionary with results from each source
        """
        
        # Determine which sources to search
        if sources is None:
            sources = cls._get_enabled_sources()
        else:
            # Validate requested sources
            sources = [s for s in sources if s in cls.SCRAPERS]
        
        if not sources:
            return {
                "success": False,
                "error": "No valid sources specified",
                "results": []
            }
        
        logger.info(f"Starting lookup for {first_name} {last_name} across {len(sources)} sources")
        
        # Execute searches
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
                    "data": {}
                })
        
        # Compile response
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

        if settings.ENABLE_TRUEPEOPLESEARCH:
            enabled.append("truepeoplesearch")
        if settings.ENABLE_FASTPEOPLESEARCH:
            enabled.append("fastpeoplesearch")
        if settings.ENABLE_NUWBER:
            enabled.append("nuwber")
        if settings.ENABLE_CYBERBACKGROUNDCHECKS:
            enabled.append("cyberbackgroundchecks")
        if settings.ENABLE_USPHONEBOOK:
            enabled.append("usphonebook")
        if settings.ENABLE_RADARIS:
            enabled.append("radaris")

        return [s for s in enabled if s in cls.SCRAPERS]
    
    @classmethod
    def get_available_sources(cls) -> List[Dict[str, Any]]:
        """Get list of available data sources"""
        return [
            {
                "name": name,
                "enabled": cls._is_source_enabled(name),
                "display_name": name.replace("_", " ").title()
            }
            for name in cls.SCRAPERS.keys()
        ]
    
    @classmethod
    def _is_source_enabled(cls, source_name: str) -> bool:
        """Check if a source is enabled in config"""
        if source_name == "truepeoplesearch":
            return settings.ENABLE_TRUEPEOPLESEARCH
        elif source_name == "fastpeoplesearch":
            return settings.ENABLE_FASTPEOPLESEARCH
        elif source_name == "nuwber":
            return settings.ENABLE_NUWBER
        elif source_name == "cyberbackgroundchecks":
            return settings.ENABLE_CYBERBACKGROUNDCHECKS
        elif source_name == "usphonebook":
            return settings.ENABLE_USPHONEBOOK
        elif source_name == "radaris":
            return settings.ENABLE_RADARIS
        return False

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
        """
        Save lookup results to the database

        Args:
            db: Database session
            search_results: Results from search_person()
            user_id: Optional user ID who performed the search

        Returns:
            Created LookupResult object
        """
        query = search_results.get("query", {})

        # Create the lookup result record
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
        await db.flush()  # Get the ID

        # Create individual person records
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
        """
        Get a lookup result by ID

        Args:
            db: Database session
            lookup_id: ID of the lookup result
            user_id: Optional user ID to filter by (for authorization)

        Returns:
            LookupResult or None if not found
        """
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
        """
        Get paginated list of lookup results

        Args:
            db: Database session
            user_id: Optional user ID to filter by
            page: Page number (1-indexed)
            page_size: Number of items per page
            first_name: Optional filter by first name
            last_name: Optional filter by last name

        Returns:
            Dictionary with items, total, page info
        """
        # Build base query
        query = select(LookupResult).options(
            selectinload(LookupResult.person_records)
        )
        count_query = select(func.count(LookupResult.id))

        # Apply filters
        if user_id is not None:
            query = query.where(LookupResult.user_id == user_id)
            count_query = count_query.where(LookupResult.user_id == user_id)

        if first_name:
            query = query.where(LookupResult.first_name.ilike(f"%{first_name}%"))
            count_query = count_query.where(LookupResult.first_name.ilike(f"%{first_name}%"))

        if last_name:
            query = query.where(LookupResult.last_name.ilike(f"%{last_name}%"))
            count_query = count_query.where(LookupResult.last_name.ilike(f"%{last_name}%"))

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(desc(LookupResult.created_at)).offset(offset).limit(page_size)

        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()

        # Calculate pages
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
        """
        Delete a lookup result

        Args:
            db: Database session
            lookup_id: ID of the lookup result
            user_id: Optional user ID for authorization

        Returns:
            True if deleted, False if not found
        """
        lookup_result = await cls.get_lookup_result(db, lookup_id, user_id)
        if not lookup_result:
            return False

        await db.delete(lookup_result)
        await db.commit()
        logger.info(f"Deleted lookup result {lookup_id}")
        return True