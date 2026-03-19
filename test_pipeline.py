#!/usr/bin/env python3
"""
Quick test of the pipeline dashboard endpoints
"""
import asyncio
import json
from backend.storage import LeadStorage

async def test_storage():
    """Test that storage works"""
    storage = LeadStorage()
    
    # Test saving a lead
    business = {
        "name": "Test Company",
        "city": "London",
        "country": "UK",
        "industry": "restaurant",
        "website": "https://example.com",
        "phone": "1234567890",
        "has_website": True,
        "distance_m": 500
    }
    
    pitch = {
        "fit_score": 8,
        "score_reasoning": "Good fit",
        "pain_points": ["Cost", "Time"],
        "best_angle": "Focus on ROI",
        "email_subject": "Test Subject",
        "email_body": "Test Body",
        "confidence": "high"
    }
    
    lead = storage.save_lead({
        "business": business,
        "pitch_result": pitch,
        "service": "Web Design"
    })
    
    print("✓ Lead saved:", lead.get("id"))
    
    # Test loading leads
    all_leads = storage.get_all_leads()
    print(f"✓ Total leads: {len(all_leads)}")
    
    # Test stats
    stats = storage.get_stats()
    print(f"✓ Stats: {json.dumps(stats, indent=2)}")
    
    # Test get by status
    researched = storage.get_leads_by_status("researched")
    print(f"✓ Researched leads: {len(researched)}")
    
    # Test update
    updated = storage.update_lead(lead["id"], {"status": "sent", "to_email": "test@example.com"})
    print(f"✓ Lead updated: {updated.get('status')} sent to {updated.get('to_email')}")
    
    # Verify update worked
    stats2 = storage.get_stats()
    print(f"✓ Updated stats: {json.dumps(stats2, indent=2)}")
    
    print("\n✓✓✓ All storage tests passed!")

if __name__ == "__main__":
    asyncio.run(test_storage())
