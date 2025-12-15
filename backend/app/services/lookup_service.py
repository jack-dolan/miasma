"""
Lookup service for coordinating data broker searches
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.scrapers.truepeoplesearch import TruePeopleSearchScraper
from app.scrapers.fastpeoplesearch import FastPeopleSearchScraper
from app.scrapers.nuwber import NuwberScraper
from app.scrapers.cyberbackgroundchecks import CyberBackgroundChecksScraper
from app.scrapers.usphonebook import USPhoneBookScraper
from app.scrapers.radaris import RadarisScraper
from app.scrapers.base import ScraperResult
from app.core.config import settings

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