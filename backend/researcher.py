"""
LeadResearcher - Analyze businesses and generate sales packages using ASI-1 API
"""
import asyncio
import json
from typing import Dict, AsyncGenerator, Optional
from datetime import datetime
from openai import AsyncOpenAI
from backend.config import ASI1_API_KEY, ASI1_BASE_URL, ASI1_MODEL


class LeadResearcher:
    """Research leads and generate sales packages using ASI-1"""
    
    def __init__(self):
        self.api_key = ASI1_API_KEY
        self.base_url = ASI1_BASE_URL
        self.model = ASI1_MODEL
        
        # Initialize OpenAI client (ASI-1 is compatible)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    async def research(
        self, 
        business: Dict, 
        service: str,
        seller_profile: Dict = None
    ) -> AsyncGenerator[str, None]:
        """
        Research a business and generate sales package via SSE streaming
        
        Args:
            business: Business dict from finder.py with name, industry, address, etc.
            service: Service being sold
            seller_profile: Seller profile dict from document analysis (optional)
        
        Yields:
            SSE events as JSON strings
        """
        
        if not self.api_key:
            yield json.dumps({
                "type": "error",
                "message": "ASI1_API_KEY not configured"
            }) + "\n"
            return
        
        try:
            print("[researcher] Step 1: Building prompt")
            # Step 1: Build the prompt
            prompt = self._build_prompt(business, service, seller_profile)
            print(f"[researcher] Step 1: Prompt built successfully, length: {len(prompt)}")
            
            print("[researcher] Step 2: Calling ASI-1 API with web search")
            # Step 2: Call ASI-1 API with streaming and web search enabled
            full_response = ""
            stream = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert global B2B sales consultant with web search capability. When analyzing a business, search the web for: the business's online presence and reviews, recent news about the business or its industry in that region, competitor landscape in that city, and common pain points for this type of business in this country. Use what you find to make the pitch hyper-specific and grounded in real data. Respond with ONLY valid JSON, no markdown or explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                stream=True,
                extra_body={"web_search": True}
            )
            print("[researcher] Step 2: Stream created successfully with web_search enabled")
            
            print("[researcher] Step 3: Streaming chunks")
            # Step 3: Yield chunks as SSE events
            chunk_count = 0
            async for chunk in stream:
                chunk_count += 1
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'content') and choice.delta.content:
                        text = choice.delta.content
                        full_response += text
                        
                        yield json.dumps({
                            "type": "chunk",
                            "content": text
                        }) + "\n"
                        
                        await asyncio.sleep(0.01)  # Small delay for streaming effect
            
            print(f"[researcher] Step 3: Received {chunk_count} chunks, total response length: {len(full_response)}")
            
            print("[researcher] Step 4: Parsing and validating JSON")
            # Step 4: Parse and validate the JSON response
            try:
                # Try to extract JSON from response (may have markdown)
                json_str = self._extract_json(full_response)
                print(f"[researcher] Step 4a: Extracted JSON string, length: {len(json_str)}")
                result = json.loads(json_str)
                print(f"[researcher] Step 4b: JSON parsed successfully, keys: {list(result.keys())}")
                
                # Validate and normalize pain_points
                if "pain_points" not in result or not isinstance(result.get("pain_points"), list):
                    print("[researcher] Step 4c: pain_points missing or not a list, using defaults")
                    result["pain_points"] = ["Limited online presence", "No dedicated marketing channel", "Unknown service costs"]
                else:
                    pain_points = result["pain_points"]
                    print(f"[researcher] Step 4c: pain_points is a list with {len(pain_points)} items")
                    # Pad or truncate to exactly 3 items
                    if len(pain_points) < 3:
                        while len(pain_points) < 3:
                            pain_points.append("No additional pain points identified")
                        print(f"[researcher] Step 4c: Padded pain_points to {len(pain_points)} items")
                    else:
                        result["pain_points"] = pain_points[:3]
                        print(f"[researcher] Step 4c: Truncated pain_points to 3 items")
                
                # Validate other required fields exist
                required_fields = ["fit_score", "score_reasoning", "best_angle", "email_subject", "email_body", "confidence"]
                for field in required_fields:
                    if field not in result:
                        print(f"[researcher] Step 4d: Missing field '{field}', using fallback")
                        result[field] = self._create_fallback_response(business, service)[field]
                
                print("[researcher] Step 4e: All validations passed")
                        
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback with empty response
                print(f"[researcher] Step 4: JSON parsing failed - {str(e)}")
                print(f"[researcher] Step 4: Full response was: {full_response[:500]}")
                result = self._create_fallback_response(business, service, seller_profile)
            
            print("[researcher] Step 5: Contact email (discovered separately)")
            # Step 5: Contact email would be discovered separately if needed
            # ASI-1 web search provides context about business online presence
            result["contact_email"] = None  # Will be discovered in separate call if needed
            result["email_source"] = "not_found"
            print(f"[researcher] Step 5: Contact email discovery is handled separately")
            
            print("[researcher] Step 6: Yielding complete event")
            # Step 6: Yield final complete event with debug info
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            yield json.dumps({
                "type": "complete",
                "result": result,
                "debug": {
                    "prompt_sent": prompt,
                    "raw_response": full_response[:500],  # First 500 chars to avoid bloat
                    "model": self.model,
                    "timestamp": timestamp,
                    "web_search": "ASI-1 web search enabled",
                    "chunks_streamed": chunk_count
                }
            }) + "\n"
            print("[researcher] Step 6: Complete event yielded successfully")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[researcher.py] FULL ERROR:\n{tb}")
            tb_lines = traceback.extract_tb(e.__traceback__)
            line_no = tb_lines[-1].lineno if tb_lines else 0
            
            error_event = {
                "type": "error",
                "message": str(e),
                "traceback": tb,
                "error_line": line_no,
                "error_type": type(e).__name__
            }
            
            yield json.dumps(error_event) + "\n"
            print(f"[researcher] ERROR event yielded")
    
    def _build_prompt(self, business: Dict, service: str, seller_profile: Dict = None) -> str:
        """Build the detailed prompt for ASI-1 with web search instructions"""
        
        # Extract business details
        name = business.get("name", "Unknown")
        industry = business.get("industry", "Unknown")
        address = business.get("address", "")
        city = business.get("city", "Unknown")
        country = business.get("country", "Unknown")
        has_website = business.get("has_website", False)
        has_phone = business.get("has_phone", False)
        distance_m = business.get("distance_m", 0)
        
        # Build seller profile section if provided
        seller_section = ""
        if seller_profile:
            seller_name = seller_profile.get("person_or_company", "Unknown")
            seller_summary = seller_profile.get("summary", "")
            seller_experience = seller_profile.get("years_experience")
            seller_services = seller_profile.get("services", [])
            
            services_list = ", ".join([s.get("name", "") for s in seller_services]) if seller_services else "Not specified"
            
            seller_section = f"""
SELLER PROFILE (Who is sending the email):
- Name/Company: {seller_name}
- Professional Summary: {seller_summary}
- Years of Experience: {seller_experience if seller_experience else 'Not specified'}
- Services Offered: {services_list}

This email is being sent FROM this person's perspective. Reference their actual background and services in the pitch."""
        
        # Add industry context for fit scoring if seller has experience
        industry_context = ""
        if seller_profile and seller_profile.get("industries_worked_in"):
            seller_industries = seller_profile.get("industries_worked_in", [])
            if industry in seller_industries or any(ind.lower() in industry.lower() for ind in seller_industries):
                industry_context = f"\nNOTE: The seller has direct experience in {industry} industry - this is a strong match. Boost fit_score reasoning accordingly."
        
        prompt = f"""Analyze this real business and create a compelling sales package.

BUSINESS DETAILS:
- Name: {name}
- Type: {industry}
- Location: {address}, {city}, {country}
- Has website: {has_website}
- Has phone listed: {has_phone}
- Distance from prospect: {distance_m}m

WEB RESEARCH INSTRUCTIONS:
Use your web search capability to find:
- The business's online presence, website content, and reviews
- Recent news about the business or its industry in that region
- Competitor landscape in that city
- Common pain points for {industry} businesses in {country}

Use real data from your web search to make the pitch hyper-specific and grounded.

SERVICE BEING SOLD: {service}{seller_section}{industry_context}

Respond with ONLY a valid JSON object (no markdown, no explanations), with these exact fields:
{{
  "fit_score": <integer 1-10>,
  "score_reasoning": "<2 sentences max, specific to their business type and location>",
  "pain_points": ["<specific pain point 1>", "<specific pain point 2>", "<specific pain point 3>"],
  "best_angle": "<1 sentence, strongest hook for this specific business>",
  "email_opening": "<personalized first line if seller provided, generic if not>",
  "email_subject": "<compelling subject line>",
  "email_body": "<Write a natural, warm outreach email under 180 words. Structure it like this:
    - Line 1: A warm, specific opener that shows you noticed something real about THEIR business (reference their city, their type of business, or something specific from the web intel). Do NOT start with 'I noticed' - vary the opening.
    - Line 2-3: A brief, confident introduction of who you are and your most relevant experience. One sentence max.
    - Line 4-5: Connect YOUR skills directly to THEIR specific pain point. Make it feel like you understand their world.
    - Line 6: A soft, specific call to action. Not 'let me know if interested' - something more direct like 'Would a 15-minute call this week work?' or 'I can have a proposal ready by Friday if you'd like.'
    - Sign off with the seller's actual name if available, otherwise 'Best regards'
    
    The email should sound like it was written by a real human who did their homework, not a template. Use conversational language. Avoid: 'I hope this finds you well', 'I wanted to reach out', 'leverage', 'synergy', 'cutting-edge'.>",
  "confidence": "<low|medium|high based on web data found>"
}}"""
        
        return prompt
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that may have markdown code blocks"""
        
        # Try direct JSON parse first
        text = text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        
        if start != -1 and end > start:
            return text[start:end]
        
        return text
    
    def _create_fallback_response(self, business: Dict, service: str, seller_profile: Dict = None) -> Dict:
        """Create a default response if ASI-1 fails"""
        
        email_opening = ""
        if seller_profile:
            seller_name = seller_profile.get("person_or_company", "Unknown")
            seller_summary = seller_profile.get("summary", "")
            years = seller_profile.get("years_experience")
            years_text = f" with {years}+ years of experience" if years else ""
            email_opening = f"I'm {seller_name}, a {seller_summary}{years_text}."
        else:
            email_opening = "I work with businesses like yours to improve their operations."
        
        email_body = ""
        if seller_profile:
            seller_name = seller_profile.get("person_or_company", "Unknown")
            email_body = f"Hi,\n\nI specialize in {service} and noticed {business.get('name')} could benefit from my expertise. I've worked with {business.get('industry', 'similar')} companies before and have a track record of delivering results.\n\nWould love to discuss how I can help.\n\nBest regards,\n{seller_name}"
        else:
            email_body = f"Hi there,\n\nI noticed {business.get('name')} could benefit from {service}. Would love to discuss how we can help.\n\nBest regards"
        
        return {
            "fit_score": 5,
            "score_reasoning": f"Business appears suitable for {service} services.",
            "pain_points": [
                "Limited online presence",
                "No dedicated marketing channel",
                "Unknown service costs"
            ],
            "best_angle": f"Help {business.get('name', 'this business')} reach more customers through {service}.",
            "email_opening": email_opening,
            "email_subject": f"{service} Solution for {business.get('name', 'Your Business')}",
            "email_body": email_body,
            "confidence": "low"
        }
