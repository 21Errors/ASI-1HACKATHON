"""
Vendly AI Configuration
Load all settings from environment variables with sensible defaults
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Core API Configuration
ASI1_API_KEY = os.getenv("ASI1_API_KEY", "")
ASI1_BASE_URL = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1")
ASI1_MODEL = os.getenv("ASI1_MODEL", "asi1-mini")

# Search Configuration
SEARCH_RADIUS_M = int(os.getenv("SEARCH_RADIUS_M", "5000"))
MAX_LEADS = int(os.getenv("MAX_LEADS", "20"))
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# Industry Mappings (OSM tags)
INDUSTRIES = {
    "restaurant": {"amenity": "restaurant"},
    "gym": {"leisure": "fitness_centre"},
    "clinic": {"amenity": "clinic"},
    "hotel": {"tourism": "hotel"},
    "pharmacy": {"amenity": "pharmacy"},
    "bank": {"amenity": "bank"},
    "school": {"amenity": "school"},
    "supermarket": {"shop": "supermarket"},
    "cafe": {"amenity": "cafe"},
    "bar": {"amenity": "bar"},
    "lawyer": {"office": "lawyer"},
    "accountant": {"office": "accountant"},
    "real_estate": {"office": "real_estate"},
    "car_repair": {"shop": "car_repair"},
    "beauty_salon": {"shop": "beauty"},
    "dentist": {"amenity": "dentist"},
    "hospital": {"amenity": "hospital"},
    "construction": {"office": "construction"},
    "bakery": {"shop": "bakery"},
    "clothing_store": {"shop": "clothes"},
    "electronics": {"shop": "electronics"},
    "furniture": {"shop": "furniture"},
    "travel_agency": {"shop": "travel_agency"},
    "insurance": {"office": "insurance"},
    "marketing_agency": {"office": "marketing"},
    "it_company": {"office": "it"},
    "logistics": {"office": "logistics"},
    "printing": {"shop": "printing"},
    "photography": {"office": "photographer"},
    "event_venue": {"amenity": "event_venue"}
}

def get_industry_tag(industry: str):
    """Get OSM tag for an industry"""
    industry_lower = industry.lower()
    return INDUSTRIES.get(industry_lower, {})

def get_all_industries():
    """Get all supported industries with OSM mappings"""
    result = []
    for name, tags in INDUSTRIES.items():
        result.append({
            "id": name,
            "name": name.replace("_", " ").title(),
            "osm_tags": tags
        })
    return result
