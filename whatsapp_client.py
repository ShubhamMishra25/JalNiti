"""Utility wrapper around WhatsApp Cloud API."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import requests

from config import settings

logger = logging.getLogger(__name__)


class WhatsAppClient:
    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        api_version: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.access_token = access_token or settings.access_token
        self.phone_number_id = phone_number_id or settings.phone_number_id
        self.api_version = api_version or settings.api_version
        self.session = session or requests.Session()

    def send_text_message(self, to: str, body: str) -> Dict[str, Any]:
        if not (self.access_token and self.phone_number_id):
            logger.warning(
                "Credentials missing: falling back to console output. Set ACCESS_TOKEN and PHONE_NUMBER_ID for real delivery."
            )
            print(f"\n[MOCK OUTGOING] To: {to}\nMessage: {body}\n")
            return {"status": "mock", "to": to, "body": body}

        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }

        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("WhatsApp API timed out sending to %s", to)
            return {"status": "error", "error": "timeout", "to": to}
        except requests.exceptions.ConnectionError:
            logger.error("WhatsApp API connection failed sending to %s", to)
            return {"status": "error", "error": "connection_error", "to": to}
        except requests.HTTPError:
            logger.error("WhatsApp API error sending to %s: %s", to, response.text)
            return {"status": "error", "error": "http_error", "detail": response.text, "to": to}

        logger.info("WhatsApp message sent to %s", to)
        return response.json()

    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark a message as read to show blue ticks."""
        if not (self.access_token and self.phone_number_id):
            return {"status": "mock"}

        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("Timed out marking message as read: %s", message_id)
            return {"status": "error", "error": "timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("Connection failed marking message as read: %s", message_id)
            return {"status": "error", "error": "connection_error"}
        except requests.HTTPError:
            logger.error("Failed to mark message as read: %s", response.text)
            return {"status": "error", "error": "http_error", "detail": response.text}

        logger.info("Message marked as read: %s", message_id)
        return response.json()


client = WhatsAppClient()