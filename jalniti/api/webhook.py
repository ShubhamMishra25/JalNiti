"""Webhook routes for WhatsApp Cloud API callbacks."""
from __future__ import annotations

import logging
from collections import deque

from flask import Blueprint, jsonify, request

from config import settings
from conversation import default_engine
from whatsapp_client import client as whatsapp_client

webhook_bp = Blueprint("webhook", __name__)
logger = logging.getLogger(__name__)
conversation_engine = default_engine()

# Simple in-memory dedup for message IDs. Bounded deque + set so it doesn't
# grow forever; not persistent across restarts, but fine for now.
_MAX_SEEN = 1000
_seen_ids: set[str] = set()
_seen_order: deque[str] = deque(maxlen=_MAX_SEEN)


def _already_processed(message_id: str | None) -> bool:
    if not message_id:
        return False
    if message_id in _seen_ids:
        return True
    if len(_seen_order) == _MAX_SEEN:
        oldest = _seen_order[0]
        _seen_ids.discard(oldest)
    _seen_order.append(message_id)
    _seen_ids.add(message_id)
    return False


@webhook_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta challenge endpoint used during webhook registration."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == settings.verify_token:
        logger.info("Webhook verified successfully")
        return challenge or "", 200

    logger.warning("Webhook verification failed: mode=%s token=%s", mode, token)
    return "Forbidden", 403


@webhook_bp.route("/webhook", methods=["POST"])
def handle_message():
    """Receive WhatsApp message events and send a canned reply."""
    try:
        data = request.get_json(silent=True) or {}
        if data.get("object") != "whatsapp_business_account":
            return jsonify({"status": "ignored"}), 200

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    user_id = message.get("from")
                    message_id = message.get("id")
                    body = message.get("text", {}).get("body", "")

                    if not user_id:
                        continue

                    if _already_processed(message_id):
                        logger.info("Skipping duplicate message_id=%s", message_id)
                        continue

                    logger.info("Incoming message from %s: %s", user_id, body)

                    if message_id:
                        whatsapp_client.mark_as_read(message_id)

                    reply = conversation_engine.handle_incoming(user_id, body)
                    whatsapp_client.send_text_message(user_id, reply)

    except Exception:
        # Always ack Meta even on internal failure, so it doesn't retry
        # the same message repeatedly and cause duplicate replies once
        # we do fix whatever broke.
        logger.exception("Failed to process webhook payload")

    return jsonify({"status": "ok"}), 200