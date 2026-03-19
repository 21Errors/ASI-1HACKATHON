#!/usr/bin/env python3
"""
Complete project setup script
Creates the exact clean structure needed
"""
import os
import shutil
import sys

def setup_project():
    root = r'C:\Users\kamog\asihackathon'
    os.chdir(root)
    
    print("="*60)
    print("Vendly AI - Project Setup")
    print("="*60)
    
    # Step 1: Create directories
    print("\n[1/4] Creating directories...")
    for d in ['backend', 'frontend']:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"  ✓ Created {d}/")
        else:
            print(f"  ✓ {d}/ already exists")
    
    # Step 2: Create backend/__init__.py
    print("\n[2/4] Creating backend/__init__.py...")
    with open('backend/__init__.py', 'w') as f:
        f.write('"""Backend package"""')
    print("  ✓ backend/__init__.py")
    
    # Step 3: Create backend/config.py
    print("\n[3/4] Creating backend/config.py...")
    config_content = '''"""
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
'''
    with open('backend/config.py', 'w') as f:
        f.write(config_content)
    print("  ✓ backend/config.py")
    
    # Step 4: Create other backend files (empty)
    print("\n[4/4] Creating remaining files...")
    for f in ['backend/finder.py', 'backend/researcher.py', 'backend/web_intel.py', 'frontend/index.html']:
        open(f, 'w').close()
        print(f"  ✓ {f}")
    
    # Update main.py
    with open('main.py', 'w') as f:
        f.write('')
    print("  ✓ main.py (emptied)")
    
    # Display result
    print("\n" + "="*60)
    print("PROJECT STRUCTURE CREATED")
    print("="*60)
    
    print("\nRoot directory:")
    items = sorted(os.listdir('.'))
    for item in items:
        if item.startswith('.') and item not in ['.env', '.env.example']:
            continue
        path = os.path.join('.', item)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            print(f"  {item}")
        elif os.path.isdir(path):
            print(f"  [{item}/]")
    
    print("\nbackend/ directory:")
    for item in sorted(os.listdir('backend')):
        print(f"  {item}")
    
    print("\nfrontend/ directory:")
    for item in sorted(os.listdir('frontend')):
        print(f"  {item}")
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("  1. Edit .env to add ASI1_API_KEY")
    print("  2. Run: pip install -r requirements.txt")
    print("  3. Create backend/finder.py, researcher.py, web_intel.py with implementation")
    print("  4. Create frontend/index.html with UI")
    print("  5. Create main.py with FastAPI routes")

if __name__ == "__main__":
    try:
        setup_project()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
