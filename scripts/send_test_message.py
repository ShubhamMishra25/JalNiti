"""CLI helper to send a one-off message via WhatsApp Cloud API."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running the script directly (python scripts/send_test_message.py)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from whatsapp_client import WhatsAppClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a WhatsApp test message using existing credentials.")
    parser.add_argument("--to", default=settings.test_number, help="Destination WhatsApp number (E.164 format)")
    parser.add_argument("--message", default="JalNiti skeleton test", help="Body of the message")
    args = parser.parse_args(argv)

    if not args.to:
        parser.error("Please provide a destination number via --to or TEST_NUMBER in .env")

    client = WhatsAppClient()
    try:
        client.send_text_message(args.to, args.message)
    except Exception as exc:  # pragma: no cover - command line convenience
        print(f"Failed to send message: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# python scripts/send_test_message.py --message "hi" --to "+918010200339"
