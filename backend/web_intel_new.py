"""
WebIntel - Minimal version with email discovery only
Email discovery is still used by the frontend for contact information.
ASI-1 now handles web search natively.
"""
import asyncio
import httpx
import re
from typing import Dict, Optional
from googlesearch import search as google_search_fn


class WebIntel:
    """Find contact emails for businesses (minimal version)"""
    
    def __init__(self):
        self.user_agent = "VendlyAI/1.0"
        self.timeout = 10
    
    async def find_contact_email(self, business_name: str, city: str, website: Optional[str] = None) -> Dict:
        """
        Find contact email for a business
        
        Steps:
        1. If website provided, check /contact, /about, and homepage for emails
        2. If no email found, Google search for contact email
        3. Return {email, source} where source is "website", "google", or "not_found"
        """
        email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        
        # Filter patterns to exclude
        exclude_patterns = [
            'noreply@', 'support@', 'privacy@', 'legal@', 
            'example.com', 'sentry.io', 'gravatar.com', 'wordpress.com'
        ]
        
        def is_valid_email(email: str) -> bool:
            """Check if email is valid and not in exclude list"""
            if not email:
                return False
            email_lower = email.lower()
            for pattern in exclude_patterns:
                if pattern in email_lower:
                    return False
            return True
        
        # Step 1: Try website pages if website is provided
        if website:
            try:
                if not website.startswith(("http://", "https://")):
                    website = f"https://{website}"
                
                # Try contact, about, and homepage
                pages_to_check = [
                    f"{website}/contact",
                    f"{website}/about",
                    website
                ]
                
                for page_url in pages_to_check:
                    try:
                        async with httpx.AsyncClient(timeout=5, verify=False) as client:
                            response = await client.get(page_url)
                            response.raise_for_status()
                        
                        # Find all emails
                        emails = email_regex.findall(response.text)
                        
                        # Return first valid email
                        for email in emails:
                            if is_valid_email(email):
                                print(f"[find_contact_email] Found email {email} on {page_url}")
                                return {"email": email, "source": "website"}
                    
                    except Exception:
                        continue
            
            except Exception:
                pass
        
        # Step 2: If no email from website, search Google
        try:
            query = f'"{business_name}" "{city}" contact email'
            
            urls_checked = 0
            for url in google_search_fn(query, num_results=5):
                if urls_checked >= 2:  # Only check first 2 results
                    break
                
                try:
                    async with httpx.AsyncClient(timeout=5, verify=False) as client:
                        response = await client.get(url)
                        response.raise_for_status()
                    
                    # Find all emails
                    emails = email_regex.findall(response.text)
                    
                    # Return first valid email
                    for email in emails:
                        if is_valid_email(email):
                            print(f"[find_contact_email] Found email {email} via Google search")
                            return {"email": email, "source": "google"}
                    
                    urls_checked += 1
                
                except Exception:
                    continue
            
            await asyncio.sleep(1)  # Rate limiting
        
        except Exception:
            pass
        
        # Step 3: No email found
        print(f"[find_contact_email] No email found for {business_name}")
        return {"email": None, "source": "not_found"}
