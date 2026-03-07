"""
Standardized result format shared by all scrapers.

Pulled out of base.py so scrapers that don't use Selenium
(e.g. Camoufox-based) can import it without Selenium as a dependency.
"""

from datetime import datetime
from typing import Dict, Optional, Any


class ScraperResult:
    """Standardized result format for all scrapers"""

    def __init__(
        self,
        source: str,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.source = source
        self.success = success
        self.data = data or {}
        self.error = error
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }
