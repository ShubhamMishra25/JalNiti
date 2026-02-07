"""Conversation state model for tracking user sessions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ConversationState:
    """Tracks the state of a user's conversation session."""
    
    state: str = "START"
    
    # Language preference (persisted)
    language: str = "en"  # en, hi, mr
    language_set: bool = False  # True once user explicitly selects language
    
    # Permanent location data (set once during initial setup)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    farm_area_ares: Optional[float] = None  # Area in ares
    area: Optional[str] = None  # R or U (Rural/Urban)
    district_code: Optional[str] = None
    taluka_code: Optional[str] = None
    village_code: Optional[str] = None
    village_gis_code: Optional[str] = None
    plot_no: Optional[str] = None
    plot_owners: Optional[list] = None  # Store all plot owner info
    owner_name: Optional[str] = None  # Selected owner name
    owner_map: Optional[Dict[str, dict]] = None  # Map index to owner data
    location_setup_complete: bool = False  # True once location is fully set up
    
    # Water balance (calculated once after location setup)
    water_balance_value: Optional[float] = None
    water_balance_data: Optional[dict] = None
    
    # Temporary flow data (reset on menu)
    crop: Optional[str] = None
    available_plots: Optional[list] = None
    district_map: Optional[Dict[str, str]] = None
    taluka_map: Optional[Dict[str, str]] = None
    village_map: Optional[Dict[str, str]] = None
    
    def has_location(self) -> bool:
        """Check if full location data is available."""
        return self.location_setup_complete
    
    def has_coordinates(self) -> bool:
        """Check if at least lat/long are available."""
        return self.latitude is not None and self.longitude is not None
    
    def reset(self) -> None:
        """Reset flow data but preserve location and language."""
        self.state = "MAIN_MENU" if self.location_setup_complete else "START"
        self.crop = None
        self.available_plots = None
        self.district_map = None
        self.taluka_map = None
        self.village_map = None
        self.owner_map = None
    
    def full_reset(self) -> None:
        """Fully reset all session data including saved location and language."""
        self.state = "START"
        self.language = "en"
        self.language_set = False
        self.latitude = None
        self.longitude = None
        self.farm_area_ares = None
        self.area = None
        self.district_code = None
        self.taluka_code = None
        self.village_code = None
        self.village_gis_code = None
        self.plot_no = None
        self.plot_owners = None
        self.owner_name = None
        self.owner_map = None
        self.location_setup_complete = False
        self.water_balance_value = None
        self.water_balance_data = None
        self.crop = None
        self.available_plots = None
        self.district_map = None
        self.taluka_map = None
        self.village_map = None
