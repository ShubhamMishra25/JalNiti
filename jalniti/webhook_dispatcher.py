"""Background FIFO dispatcher for incoming WhatsApp messages.

The webhook must acknowledge Meta as fast as possible. If we block on the
Water Wallet backend APIs (each call can take up to 30s), Meta times out and
re-delivers the payload, causing duplicate replies and out-of-order messages.
Once we return 200 immediately, Meta stops retrying.

This module offloads processing to a single background worker thread. A
single FIFO consumer preserves message order (no "older message answered
after a newer one") and avoids concurrent reads/writes racing on the same
user's conversation state.

Note: the queue is in-memory, so a crash drops messages that were already
acked and still pending. For a higher-throughput/MVO, this is fine; for
delivery guarantees across many processes, replace with a shared queue
(e.g. Redis) keyed per user.
"""
from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Optional

from .conversation_engine import default_engine
from .services.whatsapp_client import client as whatsapp_client


@dataclass
class IncomingMessage:
    user_id: str
    body: str
    message_id: Optional[str] = None


class MessageDispatcher:
    """FIFO background worker that processes incoming messages one at a time."""

    def __init__(self, engine=None, whatsapp=None) -> None:
        self.engine = engine or default_engine()
        self.whatsapp = whatsapp or whatsapp_client
        self._queue: "queue.Queue[IncomingMessage]" = queue.Queue()
        self._thread = threading.Thread(
            target=self._run, name="webhook-dispatcher", daemon=True
        )
        self._thread.start()

    def enqueue(self, message: IncomingMessage) -> None:
        self._queue.put(message)

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    def _run(self) -> None:
        logger = logging.getLogger(__name__)
        while True:
            message = self._queue.get()
            try:
                self._process(message)
            except Exception:  # never let the worker die
                logger.exception("Failed to process message from %s", message.user_id)
            finally:
                self._queue.task_done()

    def _process(self, message: IncomingMessage) -> None:
        logger = logging.getLogger(__name__)
        logger.info(
            "Processing message %s from %s: %s", message.message_id, message.user_id, message.body
        )
        if message.message_id:
            self.whatsapp.mark_as_read(message.message_id)

        reply = self.engine.handle_incoming(message.user_id, message.body)
        if reply:
            self.whatsapp.send_text_message(message.user_id, reply)


dispatcher = MessageDispatcher()