"""Configuration helpers for the JalNiti WhatsApp skeleton."""
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    verify_token: str = os.getenv("VERIFY_TOKEN")
    access_token: Optional[str] = os.getenv("ACCESS_TOKEN")
    phone_number_id: Optional[str] = os.getenv("PHONE_NUMBER_ID")
    api_version: str = os.getenv("WHATSAPP_API_VERSION", "v17.0")
    app_id: Optional[str] = os.getenv("APP_ID")
    app_secret: Optional[str] = os.getenv("APP_SECRET")
    business_account_id: Optional[str] = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
    test_number: Optional[str] = os.getenv("TEST_NUMBER")

    def credentials_ready(self) -> bool:
        return bool(self.access_token and self.phone_number_id)


settings = Settings()
