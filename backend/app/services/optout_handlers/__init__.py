"""
Site-specific opt-out handlers.
"""

from app.services.optout_handlers.fastpeoplesearch import FastPeopleSearchOptoutHandler

__all__ = ["FastPeopleSearchOptoutHandler"]


def get_optout_handler(site: str):
    """Return an opt-out handler instance for a broker site."""
    handlers = {
        "fastpeoplesearch": FastPeopleSearchOptoutHandler,
    }
    handler_cls = handlers.get((site or "").lower())
    return handler_cls() if handler_cls else None
