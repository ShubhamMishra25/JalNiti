"""Webhook routes for WhatsApp Cloud API callbacks."""
from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request

from config import settings
from conversation import default_engine
from whatsapp_client import client as whatsapp_client

webhook_bp = Blueprint("webhook", __name__)
logger = logging.getLogger(__name__)
conversation_engine = default_engine()


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
    data = request.get_json(silent=True) or {}
    if data.get("object") != "whatsapp_business_account":
        return jsonify({"status": "ignored"}), 200

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    user_id = message.get("from")
                    body = message.get("text", {}).get("body", "")
                    if not user_id:
                        continue
                    logger.info("Incoming message from %s: %s", user_id, body)
                    reply = conversation_engine.handle_incoming(user_id, body)
                    whatsapp_client.send_text_message(user_id, reply)
    except Exception as exc:  # pragma: no cover - skeleton diagnostic
        logger.exception("Failed to process webhook: %s", exc)
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"}), 200
