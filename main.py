"""
Vendly AI - FastAPI backend
Main application server with all endpoints
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import os
import traceback
import base64
from datetime import datetime

from backend.config import ASI1_API_KEY, ASI1_MODEL, get_all_industries
from backend.finder import BusinessFinder
from backend.researcher import LeadResearcher
from backend.emailer import EmailSender
from backend.storage import LeadStorage
from backend.doc_parser import DocumentParser


# Request models
class LocateRequest(BaseModel):
    """Reverse geocode coordinates"""
    lat: float
    lon: float


class FindRequest(BaseModel):
    """Find businesses near coordinates across multiple industries"""
    lat: Optional[float] = None  # Optional if city_override provided
    lon: Optional[float] = None  # Optional if city_override provided
    city_override: Optional[str] = None  # Manual city name to geocode instead of using lat/lon
    range: str = "nearby"  # Range: nearby/district/country/international
    industries: list  # Array of industry strings
    service: str
    seller_profile: Optional[dict] = None  # From document analysis
    limit: int = 10


class ResearchRequest(BaseModel):
    """Research a business and generate sales package"""
    business: dict
    service: str
    seller_profile: Optional[dict] = None  # From document analysis


class DocumentAnalysisRequest(BaseModel):
    """Analyze uploaded document"""
    filename: str
    file_content: str  # base64 encoded


# Initialize app
app = FastAPI(
    title="Vendly AI",
    description="Autonomous B2B Lead Intelligence Worldwide",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
finder = BusinessFinder()
researcher = LeadResearcher()
email_sender = EmailSender()
lead_storage = LeadStorage()
doc_parser = DocumentParser()

# In-memory tracking storage (lead_id -> {opened: bool, opened_at: timestamp, ip: str})
email_tracking = {}


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    if not ASI1_API_KEY:
        print("⚠️  WARNING: ASI1_API_KEY not set. API calls will fail.")
    else:
        print("✓ ASI1_API_KEY configured")
    print(f"✓ Using model: {ASI1_MODEL}")
    
    # Validate Gmail configuration
    gmail_address = os.getenv("GMAIL_ADDRESS", "")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "")
    
    if not gmail_address or not gmail_app_password:
        print("⚠️  WARNING: Gmail not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env to enable email sending.")
    else:
        print(f"✓ Gmail configured: {gmail_address}")
        # Try to validate Gmail credentials
        result = email_sender.validate_credentials()
        if result.get("valid"):
            print(f"✓ Gmail credentials valid")
        else:
            print(f"⚠️  Gmail validation failed: {result.get('error', 'Unknown error')}")


@app.get("/")
async def root():
    """Serve frontend"""
    return FileResponse("frontend/index.html", media_type="text/html")


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "asi1_model": ASI1_MODEL,
        "api_key_set": bool(ASI1_API_KEY),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/api/industries")
async def get_industries():
    """Get all supported industry types"""
    industries = get_all_industries()
    return {
        "industries": industries,
        "total": len(industries)
    }


@app.post("/api/locate")
async def locate(request: LocateRequest):
    """
    Reverse geocode coordinates to get city and country
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        { city, country, display_name }
    """
    try:
        result = await finder.reverse_geocode(request.lat, request.lon)
        
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/range-options")
async def get_range_options(lat: float, lon: float):
    """
    Get range options relevant to the user's location.
    Returns contextual range options based on geographic hierarchy.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        {
            options: [
                { value, label, radius, multi_country (optional) },
                ...
            ]
        }
    """
    try:
        print(f"\n=== /api/range-options START ===")
        print(f"Request: lat={lat}, lon={lon}")
        
        # Reverse geocode to get country code and district
        geocode_result = await finder.reverse_geocode(lat, lon)
        country_code = geocode_result.get("country_code", "").upper()
        country_name = geocode_result.get("country", "Unknown")
        district_name = geocode_result.get("city", "District")  # Use city as district name
        
        print(f"Geocoded: {country_code}, {country_name}, {district_name}")
        
        # Get range options for this location
        options = finder.get_range_options(country_code, district_name, country_name)
        
        print(f"Returning {len(options)} range options")
        print(f"=== /api/range-options SUCCESS ===\n")
        
        return {
            "options": options,
            "country_code": country_code,
            "country_name": country_name,
            "district_name": district_name
        }
    
    except Exception as e:
        print(f"\n=== /api/range-options ERROR ===")
        print(f"Exception: {str(e)}")
        traceback.print_exc()
        print(f"=== /api/range-options ERROR END ===\n")
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/find")
async def find_businesses(request: FindRequest):
    """
    Find businesses near coordinates across multiple industries with fit scoring
    
    Args:
        lat: Latitude (optional if city_override provided)
        lon: Longitude (optional if city_override provided)
        city_override: Manual city name to geocode instead of using lat/lon
        range: Range preset (nearby/district/country/international) - default "nearby"
        industries: List of industry strings (e.g., ["restaurant", "gym", "cafe"])
        service: Service being sold
        seller_profile: Optional seller profile from document analysis
        limit: Max results to return (default 10)
    
    Returns:
        {
            businesses: [...sorted by fit score],
            total: int,
            location: { city, country, display_name },
            industries_searched: [...],
            ranked: bool
        }
    """
    try:
        print(f"\n=== /api/find START ===")
        print(f"Request: city_override={request.city_override}, range={request.range}, industries={request.industries}, service={request.service}, limit={request.limit}")
        
        # Validate input
        if not request.industries or not isinstance(request.industries, list):
            raise ValueError("Industries array required")
        
        if not request.service:
            raise ValueError("Service required")
        
        if request.limit < 1 or request.limit > 50:
            request.limit = 10
        
        # Determine lat/lon from city_override or use provided coordinates
        lat = request.lat
        lon = request.lon
        location = {}
        
        if request.city_override:
            # Geocode the city to get coordinates
            print(f"Geocoding city override: {request.city_override}")
            try:
                geocode_result = await finder.geocode_city(request.city_override)
                lat = geocode_result["lat"]
                lon = geocode_result["lon"]
                location = {
                    "city": request.city_override,
                    "country": geocode_result.get("country", ""),
                    "display_name": geocode_result.get("display_name", request.city_override)
                }
                print(f"City geocoded: {request.city_override} → lat={lat}, lon={lon}")
            except Exception as e:
                raise ValueError(f"Failed to geocode city '{request.city_override}': {str(e)}")
        else:
            # Use provided coordinates
            if lat is None or lon is None:
                raise ValueError("Either lat/lon or city_override must be provided")
            
            # Get location info from reverse geocode
            print(f"Calling reverse_geocode() for lat={lat}, lon={lon}...")
            reverse_geo = await finder.reverse_geocode(lat, lon)
            location = {
                "city": reverse_geo.get("city", "Unknown"),
                "country": reverse_geo.get("country", "Unknown"),
                "display_name": reverse_geo.get("display_name", "")
            }
        
        city = location.get("city", "Unknown")
        country = location.get("country", "Unknown")
        print(f"Location resolved: {city}, {country}")
        
        # Find businesses across multiple industries concurrently with range
        print(f"Calling BusinessFinder.find_multi_industry() with industries: {request.industries}, range={request.range}")
        
        # Handle special "southern_africa" range
        if request.range == "southern_africa":
            # Get country code from reverse geocode
            reverse_geo = await finder.reverse_geocode(lat, lon)
            country_code = reverse_geo.get("country_code", "").upper()
            
            if not country_code:
                raise ValueError("Could not determine country code for southern_africa search")
            
            print(f"Using southern_africa range with country code: {country_code}")
            businesses = await finder.find_southern_africa(
                lat=lat,
                lon=lon,
                industries=request.industries,
                country_code=country_code,
                limit_per_country=request.limit
            )
        else:
            businesses = await finder.find_multi_industry(
                lat=lat,
                lon=lon,
                industries=request.industries,
                range=request.range,
                limit_per_industry=request.limit
            )
        
        print(f"Got {len(businesses)} total businesses from multi-industry search")
        assert isinstance(businesses, list), "find_multi_industry() must return a list"
        
        # Score each business if seller_profile provided
        ranked = False
        if request.seller_profile:
            print(f"Seller profile provided, scoring all businesses...")
            for business in businesses:
                fit_result = finder.quick_fit_score(business, request.seller_profile)
                business["quick_fit_score"] = fit_result["score"]
                business["quick_fit_reasons"] = fit_result["reasons"]
            
            # Sort by quick_fit_score descending
            businesses.sort(key=lambda b: b.get("quick_fit_score", 0), reverse=True)
            ranked = True
            print(f"Scored and ranked all businesses")
        else:
            print(f"No seller profile provided, skipping fit scoring (will use default sort)")
        
        # Return top `limit` results
        results = businesses[:request.limit]
        
        print(f"=== /api/find SUCCESS (returning {len(results)}/{len(businesses)} results) ===\n")
        
        return {
            "businesses": results,
            "total": len(results),
            "location": location,
            "industries_searched": request.industries,
            "ranked": ranked
        }
    
    except Exception as e:
        print(f"\n=== /api/find ERROR ===")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        traceback.print_exc()
        print(f"=== /api/find ERROR END ===\n")
        
        return JSONResponse(
            status_code=500, 
            content={
                "error": str(e), 
                "traceback": traceback.format_exc()
            }
        )



async def research_stream(business: dict, service: str, seller_profile: dict = None):
    """Generator for streaming research results"""
    # ASI-1 will handle web search internally via web_search=True parameter
    print(f"[research_stream] Starting ASI-1 research for {business.get('name')}...")
    
    # Pass directly to researcher - ASI-1 will perform web search
    async for event in researcher.research(business, service, seller_profile):
        # Format as SSE
        yield f"data: {event}"


@app.post("/api/research")
async def research_lead(request: ResearchRequest):
    """
    Research a business and generate sales package via SSE streaming
    
    Args:
        business: Business dict (from /api/find)
        service: Service being sold
        seller_profile: Optional seller profile from document analysis
    
    Returns:
        StreamingResponse with SSE events
    """
    try:
        if not request.business or not request.service:
            raise HTTPException(status_code=400, detail="Business and service required")
        
        return StreamingResponse(
            research_stream(request.business, request.service, request.seller_profile),
            media_type="text/event-stream"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-finder")
async def test_finder():
    """
    Test route: directly call BusinessFinder with hardcoded London coordinates
    Useful for debugging the find_near() method
    """
    try:
        print("\n=== /api/test-finder START ===")
        print("Testing BusinessFinder.find_near() with hardcoded London coordinates...")
        
        # Hardcoded test parameters
        lat = 51.5074
        lon = -0.1278
        industry = "restaurant"
        radius_m = 5000
        limit = 5
        
        print(f"Parameters: lat={lat}, lon={lon}, industry={industry}, radius={radius_m}m, limit={limit}")
        
        # Call find_near directly
        results = await finder.find_near(
            lat=lat,
            lon=lon,
            industry=industry,
            radius_m=radius_m,
            limit=limit
        )
        
        print(f"Results type: {type(results)}")
        print(f"Results: {results}")
        
        if isinstance(results, dict) and "error" in results:
            print(f"=== /api/test-finder ERROR ===\n")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": results.get("error"),
                    "error_details": "BusinessFinder.find_near() returned an error dict"
                }
            )
        
        print(f"=== /api/test-finder SUCCESS ===\n")
        
        return {
            "status": "success",
            "count": len(results),
            "results": results
        }
    
    except Exception as e:
        print(f"\n=== /api/test-finder EXCEPTION ===")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        traceback.print_exc()
        print(f"=== /api/test-finder EXCEPTION END ===\n")
        
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        )


# ============ EMAIL SENDING ============
class SendEmailRequest(BaseModel):
    """Send pitch email"""
    to_email: str
    subject: str
    body: str
    lead_id: str
    business_name: str


@app.post("/api/send-email")
async def send_email(request: SendEmailRequest):
    """
    Send a pitch email via Gmail with open tracking
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        lead_id: Unique lead identifier for tracking
        business_name: Name of the business
    
    Returns:
        { success: bool, message_id: str, sent_at: ISO timestamp, error: str }
    """
    try:
        result = email_sender.send_pitch_email(
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            lead_id=request.lead_id,
            business_name=request.business_name
        )
        
        if result.get("success"):
            # Track the email
            email_tracking[request.lead_id] = {
                "to_email": request.to_email,
                "business_name": request.business_name,
                "sent_at": result.get("sent_at"),
                "opened": False,
                "opened_at": None,
                "open_count": 0
            }
            
            print(f"✓ Email sent to {request.to_email} for {request.business_name}")
            return JSONResponse(status_code=200, content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@app.get("/api/email-status")
async def email_status():
    """
    Get email delivery and open status
    
    Returns:
        { total_sent: int, total_opened: int, open_rate: float, emails: [...] }
    """
    total_sent = len(email_tracking)
    total_opened = sum(1 for e in email_tracking.values() if e["opened"])
    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    
    return {
        "total_sent": total_sent,
        "total_opened": total_opened,
        "open_rate": round(open_rate, 2),
        "emails": [
            {
                "lead_id": lead_id,
                "business_name": data.get("business_name"),
                "to_email": data.get("to_email"),
                "sent_at": data.get("sent_at"),
                "opened": data.get("opened"),
                "opened_at": data.get("opened_at"),
                "open_count": data.get("open_count", 0)
            }
            for lead_id, data in email_tracking.items()
        ]
    }


@app.get("/api/validate-gmail")
async def validate_gmail():
    """
    Validate Gmail credentials
    
    Returns:
        { valid: bool, email: str, error: str (optional) }
    """
    result = email_sender.validate_credentials()
    return JSONResponse(
        status_code=200 if result.get("valid") else 400,
        content=result
    )


@app.get("/api/email/validate")
async def validate_email():
    """
    Validate email (Gmail) configuration
    
    Returns:
        { valid: bool, email: str, error: str (optional) }
    """
    result = email_sender.validate_credentials()
    return JSONResponse(
        status_code=200 if result.get("valid") else 400,
        content=result
    )


@app.get("/api/track/open/{lead_id}")
async def track_email_open(lead_id: str, request = None):
    """
    Track email open via tracking pixel
    
    When someone opens the email, the invisible tracking pixel loads this endpoint.
    Updates the open status in both email_tracking and lead storage.
    
    Args:
        lead_id: Unique lead identifier
    
    Returns:
        1x1 transparent PNG pixel
    """
    # Update email tracking
    if lead_id in email_tracking:
        # Update tracking data
        if not email_tracking[lead_id]["opened"]:
            email_tracking[lead_id]["opened"] = True
            email_tracking[lead_id]["opened_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Increment open count
        email_tracking[lead_id]["open_count"] = email_tracking[lead_id].get("open_count", 0) + 1
        
        business_name = email_tracking[lead_id].get("business_name", "Unknown")
        print(f"✓ Email opened: {business_name} (open count: {email_tracking[lead_id]['open_count']})")
    
    # Update lead storage status to "opened"
    lead = lead_storage.get_lead(lead_id)
    if lead:
        lead_storage.update_lead(lead_id, {"status": "opened"})
        print(f"✓ Lead status updated to 'opened': {lead.get('business_name', 'Unknown')}")
    
    # Return 1x1 transparent PNG
    pixel = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\xeb\xef\xb5\xae\x00\x00\x00\x00IEND\xaeB`\x82'
    return StreamingResponse(iter([pixel]), media_type="image/png")




# ============ LEAD STORAGE & PIPELINE ============
class SaveLeadRequest(BaseModel):
    """Save a researched lead with business, pitch, and service info"""
    business: dict  # From /api/find (name, city, country, industry, has_website, website, phone, etc.)
    pitch_result: dict  # From ASI-1 (fit_score, pain_points, best_angle, email_subject, email_body, confidence)
    service: str  # Service being sold


@app.post("/api/leads/save")
async def save_lead(request: SaveLeadRequest):
    """
    Save a researched lead to pipeline
    
    Args:
        business: Business dict from /api/find
        pitch_result: Pitch dict from ASI-1 /api/research
        service: Service being sold
    
    Returns:
        { lead_id: str, lead: dict }
    """
    try:
        # Extract data from business and pitch
        lead_data = {
            "business_name": request.business.get("name", ""),
            "city": request.business.get("city", ""),
            "country": request.business.get("country", ""),
            "industry": request.business.get("industry", ""),
            "website": request.business.get("website", None),
            "phone": request.business.get("phone", None),
            "has_website": request.business.get("has_website", False),
            "service": request.service,
            "fit_score": request.pitch_result.get("fit_score"),
            "pain_points": request.pitch_result.get("pain_points", []),
            "best_angle": request.pitch_result.get("best_angle", ""),
            "email_subject": request.pitch_result.get("email_subject", ""),
            "email_body": request.pitch_result.get("email_body", ""),
            "contact_email": request.pitch_result.get("contact_email"),
            "email_source": request.pitch_result.get("email_source", "not_found"),
            "status": "researched"
        }
        
        lead = lead_storage.save_lead(lead_data)
        
        return JSONResponse(status_code=201, content={
            "lead_id": lead.get("id"),
            "lead": lead
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


class SendLeadEmailRequest(BaseModel):
    """Send email for a lead"""
    lead_id: str
    to_email: str


@app.post("/api/leads/send-email")
async def send_lead_email(request: SendLeadEmailRequest):
    """
    Send pitch email for a lead and update status
    
    Args:
        lead_id: ID of lead to email
        to_email: Recipient email address
    
    Returns:
        { success: bool, message: str, lead: dict (optional) }
    """
    try:
        print(f"[/api/leads/send-email] Attempting to send email to {request.to_email} for lead {request.lead_id}")
        
        # Get lead from storage
        lead = lead_storage.get_lead(request.lead_id)
        if not lead:
            print(f"[/api/leads/send-email] Lead not found: {request.lead_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "Lead not found",
                    "error": "Lead not found"
                }
            )
        
        print(f"[/api/leads/send-email] Lead found: {lead.get('business_name')} - subject: {lead.get('email_subject', 'N/A')[:50]}")
        
        # Send email via Gmail
        print(f"[/api/leads/send-email] Calling email_sender.send_pitch_email() with to_email={request.to_email}")
        email_result = email_sender.send_pitch_email(
            to_email=request.to_email,
            subject=lead.get("email_subject", ""),
            body=lead.get("email_body", ""),
            lead_id=request.lead_id,
            business_name=lead.get("business_name", "")
        )
        
        print(f"[/api/leads/send-email] Email send result: {email_result}")
        
        if not email_result.get("success"):
            error_msg = email_result.get("error", "Failed to send email")
            print(f"[/api/leads/send-email] Email send failed: {error_msg}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": error_msg,
                    "error": error_msg
                }
            )
        
        # Update lead status to "sent"
        updated_lead = lead_storage.update_lead(
            request.lead_id,
            {
                "status": "sent",
                "to_email": request.to_email
            }
        )
        
        print(f"[/api/leads/send-email] ✓ Email sent successfully to {request.to_email}, lead status updated")
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": f"Email sent to {request.to_email}",
            "error": None,
            "lead": updated_lead
        })
    
    except Exception as e:
        error_msg = str(e)
        print(f"[/api/leads/send-email] ✗ Exception: {error_msg}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": error_msg,
                "error": error_msg
            }
        )


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: str):
    """
    Get a single lead by ID
    
    Returns:
        Lead dict with all details
    """
    lead = lead_storage.get_lead(lead_id)
    if lead:
        return JSONResponse(status_code=200, content=lead)
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Lead not found"}
        )


@app.get("/api/leads")
async def list_leads(status: Optional[str] = None):
    """
    Get all leads in pipeline, optionally filtered by status
    
    Args:
        status: Optional filter (researched, sent, opened, replied)
    
    Returns:
        { leads: [...], stats: {...}, total: int }
    """
    if status:
        leads = lead_storage.get_leads_by_status(status)
    else:
        leads = lead_storage.get_all_leads()
    
    stats = lead_storage.get_stats()
    
    return {
        "leads": leads,
        "stats": stats,
        "total": len(leads)
    }


class UpdateLeadRequest(BaseModel):
    """Update lead fields"""
    status: Optional[str] = None
    to_email: Optional[str] = None
    notes: Optional[str] = None
    fit_score: Optional[int] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


@app.patch("/api/leads/{lead_id}")
async def update_lead(lead_id: str, request: UpdateLeadRequest):
    """
    Update a lead
    
    Returns:
        Updated lead dict, or error if not found
    """
    lead = lead_storage.update_lead(lead_id, request.dict(exclude_unset=True))
    if lead:
        return JSONResponse(status_code=200, content=lead)
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Lead not found"}
        )


@app.post("/api/leads/{lead_id}/reply")
async def mark_lead_replied(lead_id: str):
    """
    Mark a lead as replied (manually set by user)
    
    Updates status to "replied" and sets replied_at timestamp
    
    Returns:
        Updated lead dict, or error if not found
    """
    lead = lead_storage.update_lead(lead_id, {"status": "replied"})
    if lead:
        return JSONResponse(status_code=200, content=lead)
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Lead not found"}
        )


@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str):
    """
    Delete a lead
    
    Returns:
        { success: bool, deleted_id: str }
    """
    if lead_storage.delete_lead(lead_id):
        return JSONResponse(status_code=200, content={
            "success": True,
            "deleted_id": lead_id
        })
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Lead not found"}
        )


@app.get("/api/leads/stats")
async def get_pipeline_stats():
    """
    Get pipeline statistics
    
    Returns:
        {
            total: int,
            researched: int,
            sent: int,
            opened: int,
            replied: int,
            by_status: { status -> count }
        }
    """
    stats = lead_storage.get_stats()
    return JSONResponse(status_code=200, content=stats)


@app.post("/api/leads/search")
async def search_leads(query: str):
    """
    Search leads by text
    
    Args:
        query: Search text (searches business_name, city, industry, service)
    
    Returns:
        { results: [...], count: int }
    """
    results = lead_storage.search_leads(query)
    return {
        "results": results,
        "count": len(results)
    }


@app.post("/api/leads/export-csv")
async def export_leads_csv():
    """
    Export all leads to CSV file
    
    Returns:
        { success: bool, filepath: str, error?: str }
    """
    try:
        output_path = "data/leads.csv"
        if lead_storage.export_csv(output_path):
            return {
                "success": True,
                "filepath": output_path
            }
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "No leads to export"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/upload-profile")
async def upload_profile(file: UploadFile = File(...)):
    """
    Upload and analyze a CV or company profile document
    
    Accepts: multipart/form-data with file field
    Validates: .pdf and .docx only, max 10MB
    
    Returns:
        {
            person_or_company: str,
            profile_type: 'individual' or 'company',
            summary: str,
            years_experience: int or null,
            services: [{ name, confidence, description }],
            industries_worked_in: [str],
            key_skills: [str],
            filename: str,
            file_extension: str,
            text_length: int
        }
    """
    try:
        # Validate file extension
        filename = file.filename
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if ext not in ['.pdf', '.docx']:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file format: {ext}. Only .pdf and .docx are allowed."}
            )
        
        # Read file bytes
        file_bytes = await file.read()
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if len(file_bytes) > max_size:
            return JSONResponse(
                status_code=400,
                content={"error": f"File too large. Maximum size is 10MB. Received: {len(file_bytes) / 1024 / 1024:.1f}MB"}
            )
        
        print(f"[main] Uploading profile: {filename} ({len(file_bytes)} bytes)")
        
        # Parse the document
        result = await doc_parser.parse(file_bytes, filename)
        
        print(f"[main] Profile analysis complete: {filename}")
        return JSONResponse(status_code=200, content=result)
        
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f"[main] Profile upload error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Profile analysis failed: {str(e)}"}
        )


@app.post("/api/documents/analyze")
async def analyze_document(request: DocumentAnalysisRequest):
    """
    Analyze an uploaded CV or company profile
    
    Args:
        filename: Original filename (used to detect .pdf or .docx)
        file_content: Base64-encoded file content
    
    Returns:
        {
            person_or_company: str,
            profile_type: 'individual' or 'company',
            summary: str,
            years_experience: int or null,
            services: [{ name, confidence, description }],
            industries_worked_in: [str],
            key_skills: [str],
            filename: str,
            file_extension: str,
            text_length: int
        }
    """
    try:
        # Decode base64 file content
        try:
            file_bytes = base64.b64decode(request.file_content)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid base64 encoding: {str(e)}"}
            )
        
        print(f"[main] Analyzing document: {request.filename} ({len(file_bytes)} bytes)")
        
        # Parse the document
        result = await doc_parser.parse(file_bytes, request.filename)
        
        print(f"[main] Document analysis complete: {request.filename}")
        return JSONResponse(status_code=200, content=result)
        
    except ValueError as e:
        # Unsupported file type
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f"[main] Document analysis error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Document analysis failed: {str(e)}"}
        )


@app.get("/api/documents/supported-formats")
async def get_supported_formats():
    """
    Get list of supported document formats
    
    Returns:
        { formats: ['.pdf', '.docx'], description: str }
    """
    return {
        "formats": [".pdf", ".docx"],
        "description": "Supports PDF and DOCX documents",
        "max_file_size_mb": 10
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
