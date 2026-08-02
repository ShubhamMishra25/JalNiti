"""Configuration helpers for the JalNiti WhatsApp skeleton."""
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    verify_token: Optional[str] = os.getenv("VERIFY_TOKEN")
    access_token: Optional[str] = os.getenv("ACCESS_TOKEN")
    phone_number_id: Optional[str] = os.getenv("PHONE_NUMBER_ID")
    api_version: str = os.getenv("WHATSAPP_API_VERSION", "v17.0")
    app_id: Optional[str] = os.getenv("APP_ID")
    app_secret: Optional[str] = os.getenv("APP_SECRET")
    business_account_id: Optional[str] = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
    test_number: Optional[str] = os.getenv("TEST_NUMBER")
    backend_url: Optional[str] = os.getenv("BACKEND_BASE_URL")

    def credentials_ready(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    def validate(self) -> None:
        """Fail fast if required env vars are missing, instead of failing
        confusingly deep inside a request later."""
        required = {
            "VERIFY_TOKEN": self.verify_token,
            "ACCESS_TOKEN": self.access_token,
            "PHONE_NUMBER_ID": self.phone_number_id,
            "BACKEND_BASE_URL": self.backend_url,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                f"Check your .env file."
            )


settings = Settings()
settings.validate()