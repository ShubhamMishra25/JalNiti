"""Webhook routes for WhatsApp Cloud API callbacks."""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from ..config import settings
from ..session_store import message_ledger
from ..webhook_dispatcher import dispatcher, IncomingMessage

webhook_bp = Blueprint("webhook", __name__)
logger = logging.getLogger(__name__)


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
    """Acknowledge Meta immediately and enqueue messages for background
    processing.

    Processing must NOT happen inline here: the Water Wallet backend calls
    can take up to 30s each, and Meta re-delivers webhooks it doesn't see
    acknowledged in time, which causes duplicate replies and messages
    arriving out of order.
    """
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

                    if not message_ledger.register(message_id):
                        logger.info("Skipping duplicate message_id=%s", message_id)
                        continue

                    dispatcher.enqueue(
                        IncomingMessage(user_id=user_id, body=body, message_id=message_id)
                    )

    except Exception:
        # Always ack Meta even on internal failure, so it doesn't retry
        # the same payload repeatedly once we fix whatever broke.
        logger.exception("Failed to parse webhook payload")

    return jsonify({"status": "ok"}), 200