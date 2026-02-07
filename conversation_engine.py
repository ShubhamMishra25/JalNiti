"""Main conversation engine for JalNiti bot."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict

from models import ConversationState
from services import SolvencyService, SowingService
from translations import get_message, ENGLISH, HINDI, MARATHI


@dataclass
class ConversationEngine:
    """Main conversation engine that manages user sessions and message routing."""
    
    sessions: Dict[str, ConversationState] = field(default_factory=dict)
    backend_url: str = field(default_factory=lambda: os.getenv("BACKEND_BASE_URL"))
    
    def __post_init__(self):
        """Initialize services after dataclass initialization."""
        self.solvency_service = SolvencyService(self.backend_url)
        self.sowing_service = SowingService(self.backend_url)

    def handle_incoming(self, user_id: str, message: str) -> str:
        normalized = (message or "").strip().lower()
        session = self.sessions.setdefault(user_id, ConversationState())
        lang = session.language
        has_language = session.language_set  # Track if language was explicitly chosen

        # Full reset (clears everything including location and language)
        if normalized == "reset":
            session.full_reset()
            session.state = "SELECT_LANGUAGE"
            return get_message("welcome_language", ENGLISH)

        # Soft reset — go to menu if location is set, else continue setup
        if normalized in {"hi", "hello", "hey", "start", "menu"}:
            session.reset()
            if session.location_setup_complete:
                return get_message("main_menu", lang)
            elif has_language:
                # Language set but location not complete — continue location setup
                session.state = "SETUP_AREA_TYPE"
                return get_message("ask_area_type", lang)
            else:
                session.state = "SELECT_LANGUAGE"
                return get_message("welcome_language", ENGLISH)

        # Route to appropriate handler based on state
        if session.state == "START":
            if has_language and session.location_setup_complete:
                session.state = "MAIN_MENU"
                return get_message("main_menu", lang)
            elif has_language:
                session.state = "SETUP_AREA_TYPE"
                return get_message("ask_area_type", lang)
            else:
                session.state = "SELECT_LANGUAGE"
                return get_message("welcome_language", ENGLISH)

        if session.state == "SELECT_LANGUAGE":
            return self._handle_language_selection(normalized, session)

        # ── Location setup flow ──────────────────────────────────────────
        if session.state == "SETUP_AREA_TYPE":
            return self._handle_area_type(normalized, session)
        if session.state == "SETUP_SELECT_DISTRICT":
            return self._handle_district_selection(message, session)
        if session.state == "SETUP_SELECT_TALUKA":
            return self._handle_taluka_selection(message, session)
        if session.state == "SETUP_SELECT_VILLAGE":
            return self._handle_village_selection(message, session)
        if session.state == "SETUP_SELECT_PLOT":
            return self._handle_plot_selection(message, session)
        if session.state == "SETUP_SELECT_OWNER":
            return self._handle_owner_selection(message, session)

        # ── Main menu (after location setup) ─────────────────────────────
        if session.state == "MAIN_MENU":
            return self._handle_main_menu(normalized, session)

        # ── Service flows ────────────────────────────────────────────────
        if session.state == "SOWING_COLLECT_CROP":
            return self._handle_sowing_crop(message, session)
        if session.state == "SOLVENCY_COLLECT_CROP":
            return self._handle_solvency_crop(message, session)

        # Default fallback
        return get_message("fallback", lang)
    
    # ── Language Selection ───────────────────────────────────────────────
    
    def _handle_language_selection(self, choice: str, session: ConversationState) -> str:
        if choice == "1":
            session.language = ENGLISH
        elif choice == "2":
            session.language = HINDI
        elif choice == "3":
            session.language = MARATHI
        else:
            return get_message("invalid_language", ENGLISH)
        
        session.language_set = True  # Mark language as explicitly chosen
        lang = session.language
        # After language, start location setup
        session.state = "SETUP_AREA_TYPE"
        result = get_message("language_set", lang) + "\n\n"
        result += get_message("ask_area_type", lang)
        return result
    
    # ── Location Setup Flow ──────────────────────────────────────────────
    
    def _handle_area_type(self, choice: str, session: ConversationState) -> str:
        lang = session.language
        if choice in ['u', 'urban']:
            session.area = "U"
        elif choice in ['r', 'rural']:
            session.area = "R"
        else:
            return get_message("invalid_area_type", lang)
        return self.solvency_service.get_districts(session)
    
    def _handle_district_selection(self, message: str, session: ConversationState) -> str:
        lang = session.language
        selection = message.strip()
        if session.district_map and selection in session.district_map:
            session.district_code = session.district_map[selection]
            return self.solvency_service.get_talukas(session)
        return get_message("invalid_selection", lang)
    
    def _handle_taluka_selection(self, message: str, session: ConversationState) -> str:
        lang = session.language
        selection = message.strip()
        if session.taluka_map and selection in session.taluka_map:
            session.taluka_code = session.taluka_map[selection]
            return self.solvency_service.get_villages(session)
        return get_message("invalid_selection", lang)
    
    def _handle_village_selection(self, message: str, session: ConversationState) -> str:
        lang = session.language
        selection = message.strip()
        if session.village_map and selection in session.village_map:
            session.village_gis_code = session.village_map[selection]
            return self.solvency_service.get_surveys(session)
        return get_message("invalid_selection", lang)
    
    def _handle_plot_selection(self, message: str, session: ConversationState) -> str:
        """Handle plot selection, fetch info with owners list."""
        lang = session.language
        plot_no = message.strip()
        
        # Validate against available plots
        if session.available_plots:
            available = []
            for plot in session.available_plots:
                if isinstance(plot, dict) and 'plotNo' in plot:
                    available.append(str(plot['plotNo']))
                else:
                    available.append(str(plot))
            if plot_no not in available:
                return get_message("plot_not_found", lang, plot_no=plot_no)
        
        session.plot_no = plot_no
        
        try:
            # Get plot info with owners - state changes to SETUP_SELECT_OWNER inside
            return self.solvency_service.get_plot_info(session)
            
        except (ConnectionError, RuntimeError) as e:
            return get_message("error_generic", lang, error=str(e))
    
    def _handle_owner_selection(self, message: str, session: ConversationState) -> str:
        """Handle owner selection, save area, calculate balance, complete setup."""
        lang = session.language
        selection = message.strip()
        
        if not session.owner_map or selection not in session.owner_map:
            return get_message("invalid_owner_selection", lang)
        
        # Save selected owner's name and area
        owner_data = session.owner_map[selection]
        session.owner_name = owner_data['name']
        session.farm_area_ares = owner_data['area']
        print(f"[DEBUG] Owner selected: {session.owner_name}, area saved: {session.farm_area_ares}")
        
        try:
            # Calculate water balance SILENTLY (no display)
            self.solvency_service.calculate_water_balance(session)
            
            # Mark location setup as complete
            session.location_setup_complete = True
            session.state = "MAIN_MENU"
            
            # Show confirmation + main menu
            result = get_message("owner_selected", lang, 
                                 owner_name=session.owner_name, 
                                 area=session.farm_area_ares) + "\n"
            result += get_message("location_saved", lang) + "\n\n"
            result += get_message("main_menu", lang)
            return result
            
        except (ConnectionError, RuntimeError) as e:
            return get_message("error_generic", lang, error=str(e))
    
    # ── Main Menu ────────────────────────────────────────────────────────
    
    def _handle_main_menu(self, choice: str, session: ConversationState) -> str:
        lang = session.language
        
        if choice == "1":
            # Sowing Advisory
            session.state = "SOWING_COLLECT_CROP"
            return get_message("sowing_ask_crop", lang)
        
        elif choice == "2":
            # Solvency Check
            session.state = "SOLVENCY_COLLECT_CROP"
            return get_message("solvency_ask_crop", lang)
        
        elif choice == "3":
            # Crop Recommendation — directly fetch top crops
            result = self.solvency_service.get_top_crops(session)
            session.state = "MAIN_MENU"
            return result
        
        else:
            return get_message("invalid_menu_choice", lang)
    
    # ── Sowing Advisory ──────────────────────────────────────────────────
    
    def _handle_sowing_crop(self, message: str, session: ConversationState) -> str:
        session.crop = message.strip()
        result = self.sowing_service.get_sowing_advice(session)
        session.state = "MAIN_MENU"
        return result
    
    # ── Solvency Check ───────────────────────────────────────────────────
    
    def _handle_solvency_crop(self, message: str, session: ConversationState) -> str:
        session.crop = message.strip()
        result = self.solvency_service.get_water_requirement(session)
        session.state = "MAIN_MENU"
        return result


def default_engine() -> ConversationEngine:
    """Create and return the default conversation engine instance."""
    return ConversationEngine()
