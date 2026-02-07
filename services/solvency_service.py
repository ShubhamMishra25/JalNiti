"""Service for crop solvency check operations."""
from __future__ import annotations

import requests
from typing import TYPE_CHECKING, Optional

from translations import get_message

if TYPE_CHECKING:
    from models.conversation_state import ConversationState


class SolvencyService:
    """Handles all crop solvency check and recommendation API operations."""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
    
    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_numeric(data, field_names: list) -> Optional[float]:
        """Try to extract a numeric value from data using common field names."""
        if isinstance(data, (int, float)):
            return float(data)
        if isinstance(data, dict):
            for name in field_names:
                if name in data:
                    try:
                        return float(data[name])
                    except (ValueError, TypeError):
                        continue
        return None
    
    # ── location hierarchy APIs ──────────────────────────────────────────
    
    def get_districts(self, session: ConversationState) -> str:
        """Fetch and display districts."""
        lang = session.language
        try:
            url = f"{self.backend_url}/levels/districts"
            params = {"area": session.area}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return get_message("no_districts", lang)
            
            session.state = "SETUP_SELECT_DISTRICT"
            
            # Create numbered mapping
            session.district_map = {}
            header_key = "districts_header_urban" if session.area == "U" else "districts_header_rural"
            result = get_message(header_key, lang)
            
            for i, district in enumerate(data, 1):
                session.district_map[str(i)] = district['code']
                result += f"{i}. {district['name']}\n"
            
            result += get_message("select_district", lang)
            return result
            
        except requests.exceptions.ConnectionError:
            return get_message("connection_error", lang)
        except Exception as e:
            return get_message("error_generic", lang, error=str(e))
    
    def get_talukas(self, session: ConversationState) -> str:
        """Fetch and display talukas."""
        lang = session.language
        try:
            url = f"{self.backend_url}/levels/talukas"
            params = {"area": session.area, "districtCode": session.district_code}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return get_message("no_talukas", lang)
            
            session.state = "SETUP_SELECT_TALUKA"
            
            # Create numbered mapping
            session.taluka_map = {}
            result = get_message("talukas_header", lang)
            
            for i, taluka in enumerate(data, 1):
                session.taluka_map[str(i)] = taluka['code']
                result += f"{i}. {taluka['name']}\n"
            
            result += get_message("select_taluka", lang)
            return result
            
        except requests.exceptions.ConnectionError:
            return get_message("connection_error", lang)
        except Exception as e:
            return get_message("error_generic", lang, error=str(e))
    
    def get_villages(self, session: ConversationState) -> str:
        """Fetch and display villages."""
        lang = session.language
        try:
            url = f"{self.backend_url}/levels/villages"
            params = {
                "area": session.area, 
                "districtCode": session.district_code,
                "talukaCode": session.taluka_code
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return get_message("no_villages", lang)
            
            session.state = "SETUP_SELECT_VILLAGE"
            
            # Create numbered mapping - use gisCode if available, otherwise code
            session.village_map = {}
            result = get_message("villages_header", lang)
            
            for i, village in enumerate(data, 1):
                # Try gisCode first, then villageGisCode, then code
                village_code = village.get('gisCode') or village.get('villageGisCode') or village.get('code')
                session.village_map[str(i)] = village_code
                result += f"{i}. {village['name']}\n"
            
            result += get_message("select_village", lang)
            return result
            
        except requests.exceptions.ConnectionError:
            return get_message("connection_error", lang)
        except Exception as e:
            return get_message("error_generic", lang, error=str(e))
    
    def get_surveys(self, session: ConversationState) -> str:
        """Fetch available plots and ask user to enter their plot number."""
        lang = session.language
        try:
            url = f"{self.backend_url}/levels/surveys"
            params = {
                "area": session.area, 
                "districtCode": session.district_code,
                "talukaCode": session.taluka_code,
                "villageCode": session.village_gis_code  # surveys uses villageCode
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return get_message("no_plots", lang)
            
            # Store available plots for validation
            session.available_plots = data
            session.state = "SETUP_SELECT_PLOT"
            
            plot_count = len(data)
            result = get_message("plots_header", lang)
            result += get_message("plots_found", lang, count=plot_count)
            
            return result
            
        except requests.exceptions.ConnectionError:
            return get_message("connection_error", lang)
        except Exception as e:
            return get_message("error_generic", lang, error=str(e))
    
    # ── plot info (lat/long extraction) ──────────────────────────────────

    def get_plot_info(self, session: ConversationState) -> str:
        """Fetch plot info and save lat/long to session.
        
        Returns formatted plot info with numbered owner list for selection.
        """
        lang = session.language
        try:
            plot_url = f"{self.backend_url}/levels/plot-info"
            plot_params = {
                "area": session.area,
                "districtCode": session.district_code,
                "talukaCode": session.taluka_code,
                "villageGisCode": session.village_gis_code,
                "plotNo": session.plot_no
            }
            
            plot_response = requests.get(plot_url, params=plot_params, timeout=30)
            plot_response.raise_for_status()
            plot_data = plot_response.json()
            
            # Save coordinates for reuse
            session.latitude = plot_data.get('latitude')
            session.longitude = plot_data.get('longitude')
            
            owners = plot_data.get('owners', [])
            session.plot_owners = owners
            
            # Format plot details
            result = get_message("plot_info_header", lang)
            result += get_message("plot_no_label", lang, plot_no=session.plot_no) + "\n"
            
            # Handle None coordinates safely
            lat_str = f"{session.latitude:.6f}" if session.latitude else "N/A"
            lon_str = f"{session.longitude:.6f}" if session.longitude else "N/A"
            result += get_message("coordinates_label", lang, lat=lat_str, lon=lon_str) + "\n"
            
            # Show ALL owners as numbered list for selection
            if owners:
                result += get_message("plot_owners_header", lang)
                session.owner_map = {}
                for i, owner in enumerate(owners, 1):
                    owner_name = owner.get('ownerName', 'N/A')
                    owner_area = owner.get('totalArea', 'N/A')
                    print(f"[DEBUG] Owner {i}: name={owner_name}, totalArea from API={owner_area}")
                    session.owner_map[str(i)] = {
                        'name': owner_name,
                        'area': float(owner_area) if owner_area != 'N/A' else 0
                    }
                    result += f"{i}. {owner_name} ({owner_area} ares)\n"
                
                result += get_message("select_owner_prompt", lang)
                session.state = "SETUP_SELECT_OWNER"
            else:
                # No owners found - use default and complete setup
                session.farm_area_ares = 0
                session.owner_name = "Unknown"
                session.location_setup_complete = True
                session.state = "MAIN_MENU"
                result += get_message("location_saved", lang) + "\n\n"
                result += get_message("main_menu", lang)
            
            return result
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(get_message("connection_error", lang))
        except Exception as e:
            raise RuntimeError(get_message("error_generic", lang, error=str(e)))
    
    # ── groundwater balance (silent calculation) ─────────────────────────

    def calculate_water_balance(self, session: ConversationState) -> None:
        """Fetch groundwater balance and save to session SILENTLY.
        
        Does not return any message - just stores the value for later comparison.
        Raises exception on error.
        """
        try:
            balance_url = f"{self.backend_url}/balance/gw-balance"
            balance_payload = {
                "latitude": session.latitude,
                "longitude": session.longitude,
                "farm_area_ares": session.farm_area_ares
            }
            
            balance_response = requests.post(
                balance_url, 
                json=balance_payload, 
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            balance_response.raise_for_status()
            balance_data = balance_response.json()
            
            # Save raw data and extract numeric balance
            session.water_balance_data = balance_data if isinstance(balance_data, dict) else {"balance": balance_data}
            session.water_balance_value = self._extract_numeric(
                balance_data,
                ['balance', 'gw_balance', 'available_water', 'groundwater_balance',
                 'total_balance', 'water_balance', 'net_balance',
                 'water_required_litres', 'available_litres', 'total_water']
            )
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Unable to connect to balance API.")
        except Exception as e:
            raise RuntimeError(f"Error getting groundwater balance: {str(e)}")

    # ── water requirement ────────────────────────────────────────────────

    def get_water_requirement(self, session: ConversationState) -> str:
        """Calculate water requirement for a crop and compare with groundwater balance.
        
        If requirement exceeds balance, automatically fetches top crop recommendations.
        """
        lang = session.language
        try:
            # Debug: log the farm area being used
            print(f"[DEBUG] get_water_requirement called with farm_area_ares={session.farm_area_ares}")
            
            url = f"{self.backend_url}/crop/water-requirement"
            payload = {
                "latitude": session.latitude,
                "longitude": session.longitude,
                "crop": session.crop,
                "farm_area": session.farm_area_ares
            }
            
            response = requests.post(
                url, json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse response fields
            crop_used = data.get('crop_used') or session.crop or 'Unknown'
            season = data.get('season') or 'N/A'
            station = data.get('station') or 'N/A'
            crop_et_mm = data.get('crop_et_mm')
            effective_rain_mm = data.get('effective_rain_mm')
            net_irrigation_mm = data.get('net_irrigation_mm')
            seasonal_rain_mm = data.get('seasonal_rain_mm')
            total_revenue = data.get('total_revenue') or data.get('total_profit')
            water_required = data.get('water_required_litres')
            
            water_bal = session.water_balance_value
            
            result = get_message("water_req_header", lang, crop=crop_used.title())
            result += get_message("station_label", lang, station=station.title()) + "\n"
            result += get_message("season_label", lang, season=season.title()) + "\n\n"
            result += get_message("crop_et_label", lang, value=crop_et_mm or 'N/A') + "\n"
            result += get_message("seasonal_rain_label", lang, value=seasonal_rain_mm or 'N/A') + "\n"
            result += get_message("effective_rain_label", lang, value=effective_rain_mm or 'N/A') + "\n"
            result += get_message("net_irrigation_label", lang, value=net_irrigation_mm or 'N/A') + "\n"
            result += get_message("total_water_label", lang, value=f"{water_required:,.0f}" if water_required is not None else 'N/A') + "\n"
            result += get_message("estimated_profit_label", lang, value=f"{total_revenue:,.2f}" if total_revenue is not None else 'N/A') + "\n\n"
            
            # Compare with groundwater balance
            if water_required is not None and water_bal is not None:
                if water_required <= water_bal:
                    result += get_message("solvency_success", lang,
                                          balance=f"{water_bal:,.0f}",
                                          required=f"{water_required:,.0f}",
                                          crop=crop_used.title())
                    result += get_message("menu_prompt", lang)
                    return result
                else:
                    result += get_message("solvency_fail", lang,
                                          balance=f"{water_bal:,.0f}",
                                          required=f"{water_required:,.0f}",
                                          crop=crop_used.title())
                    result += "\n\n"
                    # Fetch and append top crop recommendations
                    top_crops_result = self.get_top_crops(session)
                    return f"{result}{top_crops_result}"
            else:
                result += get_message("menu_prompt", lang)
                return result
            
        except requests.exceptions.ConnectionError:
            return get_message("connection_error", lang)
        except Exception as e:
            return get_message("error_generic", lang, error=str(e))
    
    # ── top crop recommendations ─────────────────────────────────────────

    def get_top_crops(self, session: ConversationState) -> str:
        """Fetch top crop recommendations for the user's location."""
        lang = session.language
        try:
            url = f"{self.backend_url}/crop/top-crops"
            params = {
                "latitude": session.latitude,
                "longitude": session.longitude
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            season = data.get('season') or 'N/A'
            station = data.get('station') or 'N/A'
            crops = data.get('top_3_crops', [])
            
            result = get_message("recommendations_header", lang)
            result += get_message("station_label", lang, station=station.title()) + "\n"
            result += get_message("season_label", lang, season=season.title()) + "\n\n"
            
            if crops:
                for i, crop in enumerate(crops, 1):
                    crop_name = crop.get('crop') or 'Unknown'
                    profit_metric = crop.get('profit_metric')
                    line = f"{i}. {crop_name.title()}"
                    if profit_metric is not None:
                        line += f"  {get_message('profit_score_label', lang, score=f'{profit_metric:.4f}')}"
                    result += line + "\n"
            else:
                result += "No crop recommendations available.\n"
            
            result += get_message("recommendations_tip", lang)
            result += get_message("menu_prompt", lang)
            return result
        
        except requests.exceptions.ConnectionError:
            return get_message("connection_error", lang)
        except Exception as e:
            return get_message("error_generic", lang, error=str(e))
