"""
DocumentParser - Extracts text and analyzes skills/services from CVs and company profiles
"""
import json
import tempfile
import os
from typing import Dict, Optional
from openai import AsyncOpenAI
from backend.config import ASI1_API_KEY, ASI1_BASE_URL, ASI1_MODEL

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document
except ImportError:
    Document = None


class DocumentParser:
    """Parse CVs and company profiles to extract skills and services"""
    
    def __init__(self):
        self.api_key = ASI1_API_KEY
        self.base_url = ASI1_BASE_URL
        self.model = ASI1_MODEL
        
        # Initialize OpenAI client (ASI-1 is compatible)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def extract_text(self, file_path: str, file_extension: str) -> str:
        """
        Extract text from PDF or DOCX files
        
        Args:
            file_path: Path to the file
            file_extension: File extension (.pdf or .docx)
        
        Returns:
            Extracted text string
        """
        text = ""
        
        if file_extension.lower() == ".pdf":
            if not fitz:
                raise ImportError("pymupdf not installed. Run: pip install pymupdf")
            
            try:
                pdf_doc = fitz.open(file_path)
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc[page_num]
                    text += page.get_text() + "\n"
                pdf_doc.close()
            except Exception as e:
                print(f"[doc_parser] PDF extraction error: {e}")
                raise
        
        elif file_extension.lower() == ".docx":
            if not Document:
                raise ImportError("python-docx not installed. Run: pip install python-docx")
            
            try:
                doc = Document(file_path)
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
            except Exception as e:
                print(f"[doc_parser] DOCX extraction error: {e}")
                raise
        
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}. Only .pdf and .docx are supported.")
        
        # Clean up excessive whitespace
        text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
        return text
    
    async def analyze_with_asi(self, text: str) -> Dict:
        """
        Analyze extracted text using ASI-1 API
        
        Args:
            text: Extracted document text
        
        Returns:
            Structured analysis dict with skills, services, and industry recommendations
        """
        
        if not self.api_key:
            print("[doc_parser] ASI1_API_KEY not configured")
            return self._create_fallback_response()
        
        # Valid industries list
        valid_industries = [
            "restaurant", "cafe", "hotel", "gym", "clinic", "dentist", "hospital", "pharmacy",
            "bank", "school", "lawyer", "accountant", "supermarket", "bar", "bakery", "beauty_salon",
            "car_repair", "electronics", "clothing", "furniture", "travel_agency", "real_estate",
            "construction", "printing", "photography", "it_company", "marketing", "logistics",
            "insurance", "event_venue"
        ]
        
        try:
            user_prompt = f"""Analyze this document (CV, bio, social media, casual description, or any format) and respond with JSON only, no markdown:
{{
  "person_or_company": "(name if found, else 'You')",
  "profile_type": "'individual' or 'company'",
  "summary": "(one sentence professional summary, max 20 words)",
  "years_experience": "(number or null)",
  "services": [
    {{ "name": "Service Name", "confidence": "'high/medium/low'", "description": "10 word description" }}
  ],
  "industries_worked_in": ["industry1", "industry2"],
  "key_skills": ["skill1", "skill2", "skill3"],
  "recommended_industries": [
    {{
      "industry": "must match valid list",
      "reason": "one sentence explaining why this person's skills fit this industry",
      "fit_score": 85
    }}
  ],
  "target_business_profile": "one sentence describing ideal business to target"
}}

SERVICE EXTRACTION (INFERENCE-BASED):
Extract sellable services by INFERRING from what the person says, not just explicit lists.
Think about what someone would PAY this person to do.

Examples of inference:
- 'I make wooden horses' → Carpentry, Custom Woodworking, Artisan Crafts
- 'I fix peoples computers' → IT Support, Computer Repair, Tech Troubleshooting
- 'I love cooking and host dinner parties' → Catering, Private Chef Services, Event Catering
- 'been doing hair for 10 years' → Hair Styling, Beauty Services, Salon Services
- 'I build apps' → Mobile App Development, Software Development, UI/UX Design

Rules:
- ALWAYS find at least 3 services even from vague descriptions
- Use professional service names (not casual language like 'making stuff' or 'helping people')
- If the document is a company profile, extract business service offerings
- confidence: 'high' if explicitly stated, 'medium' if clearly implied, 'low' if inferred
- Return 4-8 services maximum

PERSON/COMPANY NAME EXTRACTION:
- If input is casual text with a name like 'hi im andrew', extract 'Andrew' as the name
- If no name found, use 'You' not 'Unknown'

RECOMMENDED INDUSTRIES (CREATIVE THINKING):
Think creatively about who would HIRE or PARTNER with this person.
Example: A carpenter would be perfect for:
  - furniture stores (collaboration/sales)
  - construction companies (subcontracting)
  - real estate (staging homes)
  - hotels (custom furniture/repairs)
  - event venues (custom builds for events)

Think about: direct customers, B2B partnerships, supply chain fit, complementary services.

Requirements:
- Recommend 2-8 industries from this EXACT list: restaurant, cafe, hotel, gym, clinic, dentist, hospital, pharmacy, bank, school, lawyer, accountant, supermarket, bar, bakery, beauty_salon, car_repair, electronics, clothing, furniture, travel_agency, real_estate, construction, printing, photography, it_company, marketing, logistics, insurance, event_venue
- Rank by fit_score descending (highest first)
- fit_score must be 0-100 integer, only include if >= 60
- Be specific in reason - reference actual skills/experience AND the partnership opportunity

DOCUMENT TO ANALYZE:
{text[:3000]}"""  # Limit text to avoid token overflow
            
            print("[doc_parser] Sending text to ASI-1 for analysis with industry recommendations")
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a skilled profile analyzer who can extract valuable insights from ANY format of input - formal CVs, casual bios, social media posts, brief descriptions, or even single sentences. Your job is to infer what services this person or company can sell, and think creatively about who would want to hire them. Always respond with ONLY valid JSON, no markdown or explanations."
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            # Extract response text
            response_text = ""
            if response.choices and len(response.choices) > 0:
                response_text = response.choices[0].message.content.strip()
            
            print(f"[doc_parser] ASI-1 response received, length: {len(response_text)}")
            
            # Parse JSON
            try:
                # Remove markdown code blocks if present
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                result = json.loads(response_text.strip())
                print(f"[doc_parser] JSON parsed successfully")
                
                # Validate services array
                if "services" not in result:
                    result["services"] = []
                elif not isinstance(result["services"], list):
                    result["services"] = []
                
                # Ensure max 8 services
                if len(result["services"]) > 8:
                    result["services"] = result["services"][:8]
                
                # Validate and clean recommended_industries
                if "recommended_industries" not in result:
                    result["recommended_industries"] = []
                elif isinstance(result["recommended_industries"], list):
                    # Filter to only valid industries and ensure fit_score >= 60
                    validated = []
                    for industry_rec in result["recommended_industries"]:
                        if isinstance(industry_rec, dict):
                            industry_name = industry_rec.get("industry", "").lower()
                            fit_score = industry_rec.get("fit_score", 0)
                            
                            # Validate industry name and fit score
                            if industry_name in valid_industries and fit_score >= 60:
                                validated.append({
                                    "industry": industry_name,
                                    "reason": industry_rec.get("reason", ""),
                                    "fit_score": int(fit_score)
                                })
                    
                    # Sort by fit_score descending
                    validated.sort(key=lambda x: x["fit_score"], reverse=True)
                    result["recommended_industries"] = validated[:8]  # Max 8 industries
                else:
                    result["recommended_industries"] = []
                
                # Ensure target_business_profile exists
                if "target_business_profile" not in result:
                    result["target_business_profile"] = "General business seeking professional services"
                
                print(f"[doc_parser] Analysis complete. Found {len(result.get('services', []))} services and {len(result.get('recommended_industries', []))} recommended industries")
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"[doc_parser] JSON parse error: {e}")
                print(f"[doc_parser] Response was: {response_text[:500]}")
                return self._create_fallback_response()
        
        except Exception as e:
            print(f"[doc_parser] ASI-1 analysis error: {e}")
            return self._create_fallback_response()
    
    async def parse(self, file_bytes: bytes, filename: str) -> Dict:
        """
        Main entry point: parse a file and extract structured data
        
        Args:
            file_bytes: File content as bytes
            filename: Original filename (used to detect extension)
        
        Returns:
            Full analysis dict with person/company info and services
        """
        
        # Detect file extension
        _, ext = os.path.splitext(filename)
        if not ext:
            raise ValueError("Filename must include file extension (.pdf or .docx)")
        
        # Create temp file
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file_bytes)
                temp_file = tmp.name
            
            print(f"[doc_parser] Temp file created: {temp_file}")
            
            # Extract text
            print(f"[doc_parser] Extracting text from {ext} file")
            text = self.extract_text(temp_file, ext)
            print(f"[doc_parser] Text extracted, length: {len(text)}")
            
            # Analyze with ASI-1
            print(f"[doc_parser] Analyzing with ASI-1")
            result = await self.analyze_with_asi(text)
            
            # Add metadata
            result["filename"] = filename
            result["file_extension"] = ext
            result["text_length"] = len(text)
            
            print(f"[doc_parser] Parse complete for {filename}")
            return result
        
        except Exception as e:
            print(f"[doc_parser] Parse error: {e}")
            raise
        
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"[doc_parser] Temp file deleted: {temp_file}")
                except Exception as e:
                    print(f"[doc_parser] Failed to delete temp file: {e}")
    
    def _create_fallback_response(self) -> Dict:
        """Create a fallback response when analysis fails"""
        
        return {
            "person_or_company": "Unknown",
            "profile_type": "unknown",
            "summary": "Document analysis failed. Please try again.",
            "years_experience": None,
            "services": [],
            "industries_worked_in": [],
            "key_skills": [],
            "recommended_industries": [],
            "target_business_profile": "Unable to determine ideal target business",
            "error": "Analysis failed to parse response"
        }
