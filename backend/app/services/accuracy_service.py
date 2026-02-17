"""
Accuracy scoring service for comparing scraper results against known real info
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AccuracyService:
    """Calculates how much of a target's real info is still visible on data broker sites"""

    @staticmethod
    def calculate_accuracy(scraper_results: List[Dict], real_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare scraper results against known real info.

        scraper_results: list of per-source result dicts from LookupService.search_person
        real_info: dict with keys like first_name, last_name, city, state, age

        Returns accuracy breakdown with score and per-category counts.
        """
        breakdown = {
            "names": {"total": 0, "accurate": 0},
            "addresses": {"total": 0, "accurate": 0},
            "phones": {"total": 0, "accurate": 0},
            "ages": {"total": 0, "accurate": 0},
            "emails": {"total": 0, "accurate": 0},
        }

        real_first = (real_info.get("first_name") or "").strip().lower()
        real_last = (real_info.get("last_name") or "").strip().lower()
        real_city = (real_info.get("city") or "").strip().lower()
        real_state = (real_info.get("state") or "").strip().lower()
        real_age = real_info.get("age")
        real_phones = {_normalize_phone(p) for p in (real_info.get("phones") or []) if p}
        real_emails = {e.strip().lower() for e in (real_info.get("emails") or []) if e}

        for source_result in scraper_results:
            if not source_result.get("success"):
                continue

            data = source_result.get("data", {})
            records = data.get("results", [])

            for record in records:
                # --- Name ---
                name = (record.get("name") or "").strip().lower()
                if name:
                    breakdown["names"]["total"] += 1
                    if real_first and real_last and real_first in name and real_last in name:
                        breakdown["names"]["accurate"] += 1

                # --- Age ---
                record_age = record.get("age")
                if record_age is not None:
                    breakdown["ages"]["total"] += 1
                    if real_age is not None:
                        try:
                            if abs(int(record_age) - int(real_age)) <= 1:
                                breakdown["ages"]["accurate"] += 1
                        except (ValueError, TypeError):
                            pass

                # --- Addresses ---
                addresses = record.get("addresses") or []
                # also check top-level location field
                location = record.get("location")
                if location:
                    addresses = list(addresses) + [location]

                for addr in addresses:
                    addr_str = (addr if isinstance(addr, str) else str(addr)).lower()
                    if addr_str:
                        breakdown["addresses"]["total"] += 1
                        if real_city and real_state and real_city in addr_str and real_state in addr_str:
                            breakdown["addresses"]["accurate"] += 1

                # --- Phones ---
                phones = record.get("phone_numbers") or record.get("phones") or []
                for phone in phones:
                    if phone:
                        breakdown["phones"]["total"] += 1
                        normalized = _normalize_phone(str(phone))
                        if real_phones and normalized in real_phones:
                            breakdown["phones"]["accurate"] += 1

                # --- Emails ---
                emails = record.get("emails") or []
                for email in emails:
                    if email:
                        breakdown["emails"]["total"] += 1
                        if real_emails and email.strip().lower() in real_emails:
                            breakdown["emails"]["accurate"] += 1

        total = sum(cat["total"] for cat in breakdown.values())
        accurate = sum(cat["accurate"] for cat in breakdown.values())
        score = (accurate / total * 100) if total > 0 else 0.0

        return {
            "accuracy_score": round(score, 1),
            "data_points_total": total,
            "data_points_accurate": accurate,
            "breakdown": breakdown,
        }


def _normalize_phone(phone: str) -> str:
    """Strip a phone number down to just digits for comparison"""
    return "".join(c for c in phone if c.isdigit())
