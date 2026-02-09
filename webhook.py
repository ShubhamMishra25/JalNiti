"""Webhook routes for WhatsApp Cloud API callbacks."""
from __future__ import annotations

import logging
import time
import random
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
                    message_id = message.get("id")
                    body = message.get("text", {}).get("body", "")
                    
                    if not user_id:
                        continue
                        
                    logger.info("Incoming message from %s: %s", user_id, body)
                    
                    # 1. Mark as read immediately (Blue ticks)
                    if message_id:
                        whatsapp_client.mark_as_read(message_id)
                    
                    # 2. Process the logic
                    reply = conversation_engine.handle_incoming(user_id, body)
                    
                    # 3. Simulate natural typing delay (Reading + Typing time)
                    # Average reading: 200 wpm (0.3s per word)
                    # Average typing: 40 wpm (1.5s per word)
                    input_words = len(body.split())
                    output_words = len(reply.split())
                    
                    # Calculate delay: small base + reading time + 10% of typing time (since it's a bot)
                    # We don't want it to be TOO slow, just "natural"
                    delay = 0.5 + (input_words * 0.1) + (output_words * 0.05)
                    delay = min(max(1.0, delay), 4.0)  # Clamp between 1s and 4s
                    
                    time.sleep(delay)
                    
                    # 4. Send the response
                    whatsapp_client.send_text_message(user_id, reply)
    except Exception as exc:  # pragma: no cover - skeleton diagnostic
        logger.exception("Failed to process webhook: %s", exc)
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"}), 200
