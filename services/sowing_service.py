"""Service for precision sowing advisory operations."""
from __future__ import annotations

import requests
from typing import TYPE_CHECKING

from translations import get_message

if TYPE_CHECKING:
    from models.conversation_state import ConversationState


class SowingService:
    """Handles all sowing advisory API operations."""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
    
    def get_sowing_advice(self, session: ConversationState) -> str:
        """Fetch and display sowing advice for the given crop and location."""
        lang = session.language
        try:
            url = f"{self.backend_url}/sowing/best-sowing-day"
            
            params = {
                "lat": session.latitude,
                "lon": session.longitude,
                "crop": session.crop
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if it's a simple advice response
                if 'advice' in data:
                    result = f"🌱 Sowing Advisory:\n\n{data.get('advice', 'No advice available')}"
                    result += get_message("menu_prompt", lang)
                    return result
                
                # Otherwise, it's a detailed response with best_day
                best_day = data.get("best_day", {})
                top_3 = data.get("top_3_days", [])
                crop_name = (data.get('crop') or session.crop or 'Unknown').title()
                
                result = get_message("sowing_result_header", lang, crop=crop_name)
                result += get_message("best_sowing_date", lang, date=best_day.get('date', 'N/A')) + "\n"
                result += get_message("score_label", lang, score=best_day.get('score', 'N/A')) + "\n\n"
                result += get_message("soil_temp_label", lang, temp=best_day.get('soil_temp', 'N/A')) + "\n"
                result += get_message("soil_moisture_label", lang, moisture=best_day.get('soil_moisture', 'N/A')) + "\n"
                result += get_message("rain_prob_label", lang, prob=best_day.get('rain_prob', 'N/A')) + "\n"
                result += get_message("expected_rain_label", lang, rain=best_day.get('rain_mm', 'N/A')) + "\n\n"
                
                if top_3:
                    result += get_message("top_3_options", lang) + "\n"
                    for i, day in enumerate(top_3, 1):
                        result += f"{i}. {day.get('date', 'N/A')} (Score: {day.get('score', 'N/A')})\n"
                    result += get_message("higher_score_tip", lang)
                
                result += get_message("menu_prompt", lang)
                return result
                
            elif response.status_code == 400:
                error_data = response.json()
                if "Crop not found" in error_data.get("error", ""):
                    return get_message("crop_not_found", lang, crop=session.crop) + get_message("menu_prompt", lang)
                else:
                    return get_message("error_generic", lang, error=error_data.get('error', 'Unknown error'))
            else:
                return get_message("error_generic", lang, error=f"API returned status code {response.status_code}")
            
        except requests.exceptions.ConnectionError:
            return get_message("connection_error", lang)
        except requests.exceptions.Timeout:
            return get_message("error_generic", lang, error="Request timed out")
        except Exception as e:
            return get_message("error_generic", lang, error=str(e))
