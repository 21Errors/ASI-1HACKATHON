"""
BusinessFinder - Discover real businesses from OpenStreetMap
Uses Overpass API for OSM queries and Nominatim for reverse geocoding
"""
import httpx
import asyncio
import math
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from backend.config import INDUSTRIES


class BusinessFinder:
    """Find real businesses near coordinates using OpenStreetMap"""
    
    # Range options mapped to radius in meters
    RANGE_MAP = {
        "nearby": 5000,        # 5km
        "district": 25000,     # 25km
        "country": 100000,     # 100km
        "international": 50000 # 50km (special case - uses geocoded city center)
    }
    
    # Southern Africa geographic hierarchy
    SOUTHERN_AFRICA_COUNTRIES = {
        "BW": {"name": "Botswana", "neighbors": ["ZA", "ZW", "NA", "ZM"]},
        "ZA": {"name": "South Africa", "neighbors": ["BW", "ZW", "MZ", "NA", "LS", "SZ"]},
        "ZW": {"name": "Zimbabwe", "neighbors": ["ZA", "BW", "MZ", "ZM"]},
        "NA": {"name": "Namibia", "neighbors": ["ZA", "BW", "ZM", "AO"]},
        "ZM": {"name": "Zambia", "neighbors": ["ZW", "BW", "MZ", "TZ", "CD", "AO"]},
        "MZ": {"name": "Mozambique", "neighbors": ["ZA", "ZW", "ZM", "TZ"]},
        "LS": {"name": "Lesotho", "neighbors": ["ZA"]},
        "SZ": {"name": "Eswatini", "neighbors": ["ZA", "MZ"]},
    }
    
    def __init__(self):
        # Multiple Overpass API endpoints (tried in order)
        self.OVERPASS_ENDPOINTS = [
            "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
            "https://overpass-api.de/api/interpreter",
        ]
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.user_agent = "VendlyAI/1.0"
        self.timeout = 30
        
        # Build industry map from config - convert {"key": "value"} to "key=value"
        self.INDUSTRY_MAP = {}
        for industry_name, tags_dict in INDUSTRIES.items():
            if isinstance(tags_dict, dict) and tags_dict:
                # Get first key=value pair
                for key, value in tags_dict.items():
                    self.INDUSTRY_MAP[industry_name] = f"{key}={value}"
                    break
        
        print(f"[finder.py] INDUSTRY_MAP initialized with {len(self.INDUSTRY_MAP)} entries")
        print(f"[finder.py] Overpass endpoints: {len(self.OVERPASS_ENDPOINTS)} available")
        print(f"[finder.py] RANGE_MAP: {self.RANGE_MAP}")
    
    def get_range_options(self, country_code: str, district_name: str, country_name: str) -> List[Dict]:
        """
        Get range options relevant to the user's location.
        Returns different options based on whether they're in Southern Africa or elsewhere.
        
        Args:
            country_code: ISO country code (e.g., "BW", "GB")
            district_name: District or province name (e.g., "Kwarapata")
            country_name: Full country name (e.g., "Botswana")
        
        Returns:
            List of range options with value, label, and radius
        """
        if country_code in self.SOUTHERN_AFRICA_COUNTRIES:
            return [
                {
                    "value": "nearby",
                    "label": " Nearby (5km)",
                    "radius": 5000,
                    "city_filter": None
                },
                {
                    "value": "district",
                    "label": f"🏘️ {district_name} District (25km)",
                    "radius": 25000
                },
                {
                    "value": "country",
                    "label": f" All of {country_name}",
                    "radius": 500000
                },
                {
                    "value": "southern_africa",
                    "label": "🌍 Southern Africa (neighbouring countries)",
                    "radius": None,
                    "multi_country": True
                }
            ]
        else:
            return [
                {
                    "value": "nearby",
                    "label": " Nearby (5km)",
                    "radius": 5000
                },
                {
                    "value": "district",
                    "label": "City area (25km)",
                    "radius": 25000
                },
                {
                    "value": "country",
                    "label": " Wider region (100km)",
                    "radius": 100000
                },
                {
                    "value": "international",
                    "label": " International (500km)",
                    "radius": 500000
                }
            ]
    
    async def find_near(
        self, 
        lat: float, 
        lon: float, 
        industry: str, 
        range: str = "nearby",
        radius_m: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find businesses near coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            industry: Industry type (e.g., "restaurant", "gym")
            range: Range preset (nearby/district/country/international) - default "nearby"
            radius_m: Override radius in meters (optional, takes precedence over range)
            limit: Maximum number of results (default 10)
        
        Returns:
            List of business dictionaries sorted by distance (empty list if none found)
        
        Raises:
            Exception: If API queries fail
        """
        # Determine radius from range or use provided value
        if radius_m is None:
            radius_m = self.RANGE_MAP.get(range, self.RANGE_MAP["nearby"])
        
        print(f"[finder.py] find_near() called with lat={lat}, lon={lon}, industry={industry}, range={range}, radius={radius_m}m")
        
        # Get reverse geocode data for fallback
        geocode_data = await self.reverse_geocode(lat, lon)
        print(f"[finder.py] Reverse geocode: {geocode_data.get('city')}, {geocode_data.get('country')}")
        
        # Query Overpass API
        businesses = await self._query_overpass(lat, lon, industry, radius_m, limit, geocode_data)
        print(f"[finder.py] Initial query returned {len(businesses)} businesses")
        
        # If too few results, retry with larger radius
        if len(businesses) < 5:
            print(f"[finder.py] Only {len(businesses)} results, retrying with expanded radius...")
            expanded_radius = radius_m * 3
            businesses = await self._query_overpass(lat, lon, industry, expanded_radius, limit, geocode_data)
            print(f"[finder.py] Expanded query returned {len(businesses)} businesses")
        
        # Sort by distance (closest first)
        businesses.sort(key=lambda b: b.get("distance_m", float("inf")))
        print(f"[finder.py] find_near() returning {len(businesses)} results")
        
        # Return up to limit results
        return businesses[:limit]
    
    async def find_multi_industry(
        self,
        lat: float,
        lon: float,
        industries: List[str],
        range: str = "nearby",
        radius_m: Optional[int] = None,
        limit_per_industry: int = 10
    ) -> List[Dict]:
        """
        Find businesses across multiple industries concurrently
        
        Args:
            lat: Latitude
            lon: Longitude
            industries: List of industry strings (e.g., ["restaurant", "gym", "cafe"])
            range: Range preset (nearby/district/country/international) - default "nearby"
            radius_m: Override radius in meters (optional, takes precedence over range)
            limit_per_industry: Max results per industry (default 10)
        
        Returns:
            Combined list of businesses with industry_source field, deduplicated by osm_id
        """
        # Determine radius from range or use provided value
        if radius_m is None:
            radius_m = self.RANGE_MAP.get(range, self.RANGE_MAP["nearby"])
        
        print(f"[finder.py] find_multi_industry() called with {len(industries)} industries: {industries}, range={range}, radius={radius_m}m")
        
        if not industries:
            print("[finder.py] No industries provided, returning empty list")
            return []
        
        # Run find_near() for each industry concurrently
        tasks = [
            self.find_near(lat, lon, industry, range=range, radius_m=radius_m, limit=limit_per_industry)
            for industry in industries
        ]
        
        results_by_industry = await asyncio.gather(*tasks, return_exceptions=True)
        print(f"[finder.py] Completed concurrent searches for {len(industries)} industries")
        
        # Flatten and add industry_source field
        all_businesses = []
        seen_osm_ids = set()
        
        for industry, result in zip(industries, results_by_industry):
            if isinstance(result, Exception):
                print(f"[finder.py] Error searching industry '{industry}': {result}")
                continue
            
            for business in result:
                osm_id = business.get("osm_id")
                
                # Deduplicate by osm_id - only add if not seen before
                if osm_id not in seen_osm_ids:
                    business["industry_source"] = industry
                    all_businesses.append(business)
                    seen_osm_ids.add(osm_id)
                else:
                    # Update existing entry to note additional industries
                    for b in all_businesses:
                        if b.get("osm_id") == osm_id:
                            # Keep original industry_source, but note in logs
                            print(f"[finder.py] Business {osm_id} found in multiple industries, keeping first: {b.get('industry_source')}")
                            break
        
        print(f"[finder.py] find_multi_industry() returning {len(all_businesses)} deduplicated businesses")
        return all_businesses
    
    async def find_southern_africa(
        self,
        lat: float,
        lon: float,
        industries: List[str],
        country_code: str,
        limit_per_country: int = 5
    ) -> List[Dict]:
        """
        Find businesses across Southern Africa (current country + neighbors)
        
        Args:
            lat: Current latitude (for current country search)
            lon: Current longitude (for current country search)
            industries: List of industry strings
            country_code: Current country code (e.g., "BW")
            limit_per_country: Max results per country (default 5)
        
        Returns:
            Combined list of businesses from all countries with country field added
        """
        if country_code not in self.SOUTHERN_AFRICA_COUNTRIES:
            print(f"[finder.py] Country {country_code} not in Southern Africa countries, using standard search")
            return []
        
        country_info = self.SOUTHERN_AFRICA_COUNTRIES[country_code]
        neighbor_codes = country_info.get("neighbors", [])
        
        print(f"[finder.py] find_southern_africa() for {country_code}, neighbors: {neighbor_codes}")
        
        all_businesses = []
        seen_osm_ids = set()
        
        # Search current country first (using provided lat/lon)
        current_results = await self.find_multi_industry(
            lat, lon, industries,
            range="country",
            limit_per_industry=limit_per_country
        )
        
        for business in current_results:
            business["country_code"] = country_code
            osm_id = business.get("osm_id")
            if osm_id not in seen_osm_ids:
                all_businesses.append(business)
                seen_osm_ids.add(osm_id)
        
        print(f"[finder.py] Current country ({country_code}) returned {len(current_results)} businesses")
        
        # Search neighbor countries
        for neighbor_code in neighbor_codes:
            try:
                neighbor_name = self.SOUTHERN_AFRICA_COUNTRIES.get(neighbor_code, {}).get("name", neighbor_code)
                
                # Geocode the capital city of the neighbor country
                # Use a simple approach: search for "capital country_name"
                capital_lat, capital_lon = await self._geocode_capital(neighbor_code, neighbor_name)
                
                if capital_lat is None:
                    print(f"[finder.py] Could not geocode capital for {neighbor_code}, skipping")
                    continue
                
                # Search in that country with wide radius
                neighbor_results = await self.find_multi_industry(
                    capital_lat, capital_lon, industries,
                    range="country",
                    limit_per_industry=limit_per_country
                )
                
                for business in neighbor_results:
                    business["country_code"] = neighbor_code
                    osm_id = business.get("osm_id")
                    if osm_id not in seen_osm_ids:
                        all_businesses.append(business)
                        seen_osm_ids.add(osm_id)
                
                print(f"[finder.py] Neighbor {neighbor_code} returned {len(neighbor_results)} businesses")
            except Exception as e:
                print(f"[finder.py] Error searching neighbor {neighbor_code}: {e}")
                continue
        
        print(f"[finder.py] find_southern_africa() returning {len(all_businesses)} total businesses")
        return all_businesses
    
    async def _geocode_capital(self, country_code: str, country_name: str) -> tuple:
        """
        Geocode the capital city of a country
        
        Args:
            country_code: ISO country code
            country_name: Full country name
        
        Returns:
            Tuple of (lat, lon) or (None, None) if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Search for capital city
                search_query = f"capital of {country_name}"
                response = await client.get(
                    f"{self.nominatim_url}/search",
                    params={
                        "q": search_query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": country_code
                    },
                    headers={"User-Agent": self.user_agent}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    if results:
                        lat = float(results[0]["lat"])
                        lon = float(results[0]["lon"])
                        print(f"[finder.py] Geocoded capital of {country_name}: {lat}, {lon}")
                        return lat, lon
        except Exception as e:
            print(f"[finder.py] Error geocoding capital of {country_name}: {e}")
        
        return None, None
    
    async def _query_overpass(
        self, 
        lat: float, 
        lon: float, 
        industry: str, 
        radius_m: int,
        limit: int,
        geocode_data: Dict
    ) -> List[Dict]:
        """Query Overpass API with fallback endpoints
        
        Args:
            geocode_data: Result from reverse_geocode to use as fallback
        
        Returns:
            List of businesses (empty list if none found)
        
        Raises:
            Exception if all API endpoints fail
        """
        
        # Get OSM tag for industry
        osm_tag = self.INDUSTRY_MAP.get(industry.lower(), f'name~"{industry}"')
        print(f"[finder.py] Using OSM tag: {osm_tag}")
        
        # Parse tag into key and value
        if "=" in osm_tag:
            tag_key, tag_value = osm_tag.split("=", 1)
        else:
            tag_key = "name"
            tag_value = industry
        
        # Build Overpass QL query with JSON output (simplified - no limit in query)
        query = f"""[out:json][timeout:20];
(
  node["{tag_key}"="{tag_value}"](around:{radius_m},{lat},{lon});
  way["{tag_key}"="{tag_value}"](around:{radius_m},{lat},{lon});
);
out center;
"""
        
        print(f"[finder.py] Overpass QL Query:\n{query}")
        
        # Try each endpoint
        last_error = None
        for endpoint_idx, endpoint_url in enumerate(self.OVERPASS_ENDPOINTS):
            try:
                print(f"[finder.py] Trying endpoint {endpoint_idx + 1}/{len(self.OVERPASS_ENDPOINTS)}: {endpoint_url}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint_url,
                        data=query,
                        headers={"User-Agent": self.user_agent}
                    )
                    print(f"[finder.py] Overpass HTTP Status: {response.status_code}")
                    
                    # Check for rate limiting / gateway errors
                    if response.status_code in [429, 502, 503, 504]:
                        last_error = f"HTTP {response.status_code} - trying next endpoint"
                        print(f"[finder.py] {last_error}")
                        if endpoint_idx < len(self.OVERPASS_ENDPOINTS) - 1:
                            await asyncio.sleep(2)  # Wait 2 seconds before next endpoint
                        continue
                    
                    response.raise_for_status()
                    
                    response_text = response.text
                    print(f"[finder.py] Overpass Response (first 500 chars):\n{response_text[:500]}")
                    
                    # Parse JSON response
                    results = self._parse_overpass_response(response_text, lat, lon, industry, geocode_data)
                    print(f"[finder.py] Parsed {len(results)} results from Overpass")
                    
                    # Slice to limit after parsing
                    return results[:limit]
            
            except httpx.TimeoutException as e:
                last_error = f"Timeout on {endpoint_url}"
                print(f"[finder.py] {last_error}")
                if endpoint_idx < len(self.OVERPASS_ENDPOINTS) - 1:
                    await asyncio.sleep(2)
                continue
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP Error {e.response.status_code} on {endpoint_url}"
                print(f"[finder.py] {last_error}")
                if endpoint_idx < len(self.OVERPASS_ENDPOINTS) - 1:
                    await asyncio.sleep(2)
                continue
            except Exception as e:
                last_error = f"Error on {endpoint_url}: {type(e).__name__}: {str(e)}"
                print(f"[finder.py] {last_error}")
                if endpoint_idx < len(self.OVERPASS_ENDPOINTS) - 1:
                    await asyncio.sleep(2)
                continue
        
        # All endpoints failed
        error_msg = f"All Overpass API endpoints failed. Last error: {last_error}"
        print(f"[finder.py] {error_msg}")
        raise Exception(error_msg)
    
    def _parse_overpass_response(
        self, 
        json_text: str, 
        user_lat: float, 
        user_lon: float,
        industry: str,
        geocode_data: Dict
    ) -> List[Dict]:
        """Parse Overpass API JSON response"""
        results = []
        
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"[finder.py] Failed to parse JSON: {e}")
            return []
        
        elements = data.get("elements", [])
        print(f"[finder.py] Parsing {len(elements)} elements from Overpass response")
        
        for element in elements:
            business = self._extract_business_from_element(element, user_lat, user_lon, industry, geocode_data)
            if business and business.get("name"):
                results.append(business)
        
        return results
    
    def _extract_business_from_element(
        self, 
        element: Dict, 
        user_lat: float, 
        user_lon: float,
        industry: str,
        geocode_data: Dict
    ) -> Optional[Dict]:
        """Extract business info from OSM element (node or way)"""
        
        try:
            osm_id = element.get("id")
            tags = element.get("tags", {})
            
            name = tags.get("name")
            if not name:
                return None
            
            # Get coordinates - different for nodes vs ways
            if element.get("type") == "node":
                lat = element.get("lat")
                lon = element.get("lon")
            elif element.get("type") == "way":
                center = element.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")
            else:
                return None
            
            if lat is None or lon is None:
                return None
            
            # Calculate distance using user's coordinates
            distance_m = self._calculate_distance(user_lat, user_lon, lat, lon)
            
            # City: try OSM tags with priority, then fallback to reverse geocode
            city = (tags.get("addr:city") or 
                   tags.get("addr:town") or 
                   tags.get("addr:suburb") or 
                   geocode_data.get("city"))
            
            # Country: try OSM tags, then fallback to reverse geocode
            country = tags.get("addr:country") or geocode_data.get("country")
            
            return {
                "osm_id": osm_id,
                "name": name,
                "industry": industry,
                "address": tags.get("addr:street", ""),
                "city": city or "",
                "country": country or "",
                "lat": lat,
                "lon": lon,
                "website": tags.get("website"),
                "phone": tags.get("phone"),
                "has_website": bool(tags.get("website")),
                "has_phone": bool(tags.get("phone")),
                "distance_m": distance_m
            }
        except Exception as e:
            print(f"[finder.py] Error extracting business: {e}")
            return None
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        """Calculate distance between two coordinates using Haversine formula"""
        
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return int(distance)
    
    async def reverse_geocode(self, lat: float, lon: float) -> Dict:
        """
        Get city and country from coordinates using Nominatim
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            { city, country, display_name }
        """
        try:
            url = f"{self.nominatim_url}/reverse"
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={"User-Agent": self.user_agent}
                )
                response.raise_for_status()
                data = response.json()
            
            # Extract from response
            address = data.get("address", {})
            city = address.get("city") or address.get("town") or address.get("village")
            country = address.get("country")
            display_name = data.get("display_name", "")
            
            return {
                "city": city,
                "country": country,
                "display_name": display_name
            }
        
        except Exception as e:
            print(f"[finder.py] Reverse geocoding failed: {e}")
            return {
                "error": f"Reverse geocoding failed: {str(e)}",
                "city": None,
                "country": None,
                "display_name": ""
            }
    
    async def geocode_city(self, city_name: str) -> Dict:
        """
        Get coordinates from city name using Nominatim
        
        Args:
            city_name: City name to geocode (e.g., "London", "New York")
        
        Returns:
            { lat, lon, display_name, country }
        
        Raises:
            Exception: If city not found
        """
        try:
            url = f"{self.nominatim_url}/search"
            params = {
                "q": city_name,
                "format": "json",
                "limit": 1
            }
            
            print(f"[finder.py] Geocoding city: {city_name}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={"User-Agent": self.user_agent}
                )
                response.raise_for_status()
                data = response.json()
            
            if not data or len(data) == 0:
                raise Exception(f"City not found: {city_name}")
            
            # Extract from first result
            result = data[0]
            lat = float(result.get("lat"))
            lon = float(result.get("lon"))
            display_name = result.get("display_name", city_name)
            
            # Extract country from address
            address = result.get("address", {})
            country = address.get("country", "")
            
            print(f"[finder.py] City geocoded: {city_name} → lat={lat}, lon={lon}, country={country}")
            
            return {
                "lat": lat,
                "lon": lon,
                "display_name": display_name,
                "country": country
            }
        
        except Exception as e:
            print(f"[finder.py] Geocoding failed for '{city_name}': {e}")
            raise Exception(f"Failed to geocode city '{city_name}': {str(e)}")
    
    def quick_fit_score(self, business, seller_profile):
        """
        Calculate fit score using simple heuristics (no ASI-1 call)
        
        Args:
            business: Business dict from find_near() with osm_id, name, industry, distance_m, has_website, phone, etc.
            seller_profile: Optional seller profile from document analysis
                - industries_worked_in: list of industries
                - recommended_industries: list with fit_score per industry
                - summary: seller summary
        
        Returns:
            { score: 0-100, reasons: [list of scoring reason strings] }
        """
        score = 50  # Base score
        reasons = []
        
        if not business:
            return {"score": 0, "reasons": ["No business data"]}
        
        if not seller_profile:
            return {"score": score, "reasons": ["No seller profile provided (using baseline)"]}
        
        # Rule 1: Business has no website + seller does web dev
        if not business.get("has_website"):
            seller_summary = (seller_profile.get("summary") or "").lower()
            seller_services = [s.get("name", "").lower() for s in seller_profile.get("services", [])]
            
            is_web_dev = (
                "web" in seller_summary or "web dev" in " ".join(seller_services)
            )
            
            if is_web_dev:
                score += 30
                reasons.append("Business has no website + seller does web development (+30)")
        
        # Rule 2: Business industry in seller's industries_worked_in
        business_industry = (business.get("industry") or "").lower()
        seller_industries = [
            ind.lower() for ind in seller_profile.get("industries_worked_in", [])
        ]
        
        if business_industry in seller_industries:
            score += 25
            reasons.append(f"Seller has experience in {business_industry} industry (+25)")
        
        # Rule 3: Business industry matches a recommended_industry (use its fit_score)
        recommended = seller_profile.get("recommended_industries", [])
        for rec in recommended:
            if (rec.get("industry") or "").lower() == business_industry:
                fit_score_boost = rec.get("fit_score", 0)
                # Only apply if significantly strong (>= 70)
                if fit_score_boost >= 70:
                    # Already counted in Rule 2 if in industries_worked_in, so add bonus
                    bonus = max(0, fit_score_boost - 70)  # 70-100 → 0-30 bonus
                    score += bonus
                    reasons.append(f"Strong match to recommended industry {business_industry} ({fit_score_boost} fit score, +{bonus} bonus)")
                elif fit_score_boost >= 60:
                    score += 15
                    reasons.append(f"Recommended industry match: {business_industry} (fit score {fit_score_boost}, +15)")
        
        # Rule 4: Business has no phone listed (harder to reach, less competition)
        if not business.get("phone"):
            score += 10
            reasons.append("Business has no phone listed (less easy reach, lower competition, +10)")
        
        # Rule 5: Distance scoring
        distance = business.get("distance_m", 999999)
        
        if distance < 500:
            score += 20
            reasons.append(f"Very close (< 500m, {distance}m) - easy to visit (+20)")
        elif distance < 1000:
            score += 10
            reasons.append(f"Close (< 1000m, {distance}m) - convenient (+10)")
        
        # Cap score at 100
        final_score = min(100, score)
        
        # If no boosts were applied, add note
        if len(reasons) == 0:
            reasons.append("No additional factors - using baseline score")
        
        print(f"[finder.py] quick_fit_score() for {business.get('name')}: {final_score} - {reasons}")
        
        return {
            "score": final_score,
            "reasons": reasons
        }
