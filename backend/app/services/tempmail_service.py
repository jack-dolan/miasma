"""
Temporary email service using the mail.tm API.

Creates disposable email addresses and retrieves incoming messages.
Used by submitters that need email verification (About.me, Gravatar, etc).

API docs: https://docs.mail.tm
No API key needed. 8 QPS rate limit.
"""

import asyncio
import logging
import re
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.mail.tm"


class TempMailService:
    """
    Create temp email accounts and read incoming messages via mail.tm.

    Usage:
        mail = TempMailService()
        account = await mail.create_account()
        # account = {"address": "abc123@domain.com", "password": "..."}

        # ... trigger a verification email from some site ...

        # Poll for the verification email
        messages = await mail.wait_for_message(account, timeout=60)
        link = mail.extract_verification_link(messages[0])
    """

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Account creation
    # ------------------------------------------------------------------

    async def get_domains(self) -> List[str]:
        """Fetch available email domains."""
        resp = await self._client.get(f"{API_BASE}/domains")
        resp.raise_for_status()
        data = resp.json()

        # Response is {"hydra:member": [{"domain": "..."}]}
        domains = [d["domain"] for d in data.get("hydra:member", [])]
        if not domains:
            raise RuntimeError("No domains available from mail.tm")

        logger.debug(f"Available domains: {domains}")
        return domains

    async def create_account(
        self, username: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a new temp email account.

        Returns {"address": "user@domain.com", "password": "...", "token": "..."}
        """
        import secrets
        import string

        domains = await self.get_domains()
        domain = domains[0]

        # Generate a random username if not provided
        if not username:
            chars = string.ascii_lowercase + string.digits
            username = "".join(secrets.choice(chars) for _ in range(12))

        address = f"{username}@{domain}"
        password = secrets.token_urlsafe(16)

        # Create the account
        resp = await self._client.post(
            f"{API_BASE}/accounts",
            json={"address": address, "password": password},
        )

        if resp.status_code == 422:
            # Address already taken — retry with different username
            logger.warning(f"Address {address} taken, retrying...")
            return await self.create_account()

        resp.raise_for_status()

        # Get auth token
        token = await self._get_token(address, password)

        logger.info(f"Created temp email: {address}")
        return {
            "address": address,
            "password": password,
            "token": token,
        }

    async def _get_token(self, address: str, password: str) -> str:
        """Get a bearer token for the account."""
        resp = await self._client.post(
            f"{API_BASE}/token",
            json={"address": address, "password": password},
        )
        resp.raise_for_status()
        return resp.json()["token"]

    # ------------------------------------------------------------------
    # Message retrieval
    # ------------------------------------------------------------------

    async def get_messages(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all messages for an account."""
        resp = await self._client.get(
            f"{API_BASE}/messages",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json().get("hydra:member", [])

    async def get_message(self, token: str, message_id: str) -> Dict[str, Any]:
        """Fetch a single message by ID (includes full body)."""
        resp = await self._client.get(
            f"{API_BASE}/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def wait_for_message(
        self,
        account: Dict[str, str],
        timeout: int = 120,
        poll_interval: int = 5,
        sender_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Poll for new messages until one arrives or timeout.

        Args:
            account: Dict with "token" key from create_account()
            timeout: Max seconds to wait
            poll_interval: Seconds between polls
            sender_filter: Optional substring to match in sender address

        Returns list of full message dicts (with body).
        """
        token = account["token"]
        elapsed = 0

        while elapsed < timeout:
            messages = await self.get_messages(token)

            if messages:
                # Filter by sender if specified
                if sender_filter:
                    messages = [
                        m for m in messages
                        if sender_filter.lower() in m.get("from", {}).get("address", "").lower()
                    ]

                if messages:
                    # Fetch full message bodies
                    full_messages = []
                    for m in messages:
                        full = await self.get_message(token, m["id"])
                        full_messages.append(full)
                    return full_messages

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(f"No messages received after {timeout}s")
        return []

    # ------------------------------------------------------------------
    # Verification link extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_verification_link(
        message: Dict[str, Any],
        patterns: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Extract a verification/confirmation link from an email.

        Searches the HTML body first, falls back to text body.
        Looks for common verification URL patterns.
        """
        # Common patterns for verification links
        if patterns is None:
            patterns = [
                r'https?://[^\s"<>]+(?:verify|confirm|activate|validate|click)[^\s"<>]*',
                r'https?://[^\s"<>]+(?:token|code|key)=[^\s"<>]+',
            ]

        # Try HTML body first (has the actual href attributes)
        html_body = ""
        for part in message.get("html", []):
            html_body += part

        # Also check text body
        text_body = message.get("text", "")

        for body in [html_body, text_body]:
            if not body:
                continue
            for pattern in patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    url = match.group(0)
                    # Clean up trailing HTML artifacts
                    url = url.rstrip("\"'>);")
                    return url

        # Fallback: find any URL in the body
        all_urls = re.findall(r'https?://[^\s"<>]+', html_body or text_body)
        # Filter out common non-verification URLs
        skip = ["unsubscribe", "privacy", "terms", "logo", "image", "font", "css"]
        for url in all_urls:
            if not any(s in url.lower() for s in skip):
                return url.rstrip("\"'>);")

        return None
