"""
WebIntel - Contact email discovery for businesses
ASI-1 handles all web research via built-in web_search capability.
This module is kept only for find_contact_email().
"""
import asyncio
import httpx
import re
from typing import Optional
from googlesearch import search as google_search_fn


async def find_contact_email(business_name: str, city: str, website: Optional[str] = None) -> dict:
    """
    Find contact email for a business.

    Steps:
    1. If website provided, check /contact, /about, and homepage for emails
    2. If no email found, Google search for contact email
    3. Return {email, source} where source is "website", "google", or "not_found"
    """
    email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    exclude_patterns = [
        'noreply@', 'support@', 'privacy@', 'legal@',
        'example.com', 'sentry.io', 'gravatar.com', 'wordpress.com'
    ]

    def is_valid_email(email: str) -> bool:
        if not email:
            return False
        email_lower = email.lower()
        return not any(p in email_lower for p in exclude_patterns)

    # Step 1: Try website pages if website is provided
    if website:
        try:
            if not website.startswith(("http://", "https://")):
                website = f"https://{website}"

            for page_url in [f"{website}/contact", f"{website}/about", website]:
                try:
                    async with httpx.AsyncClient(timeout=5, verify=False) as client:
                        response = await client.get(page_url)
                        response.raise_for_status()

                    for email in email_regex.findall(response.text):
                        if is_valid_email(email):
                            print(f"[find_contact_email] Found {email} on {page_url}")
                            return {"email": email, "source": "website"}
                except Exception:
                    continue
        except Exception:
            pass

    # Step 2: Google search fallback
    try:
        query = f'"{business_name}" "{city}" contact email'
        urls_checked = 0
        for url in google_search_fn(query, num_results=5):
            if urls_checked >= 2:
                break
            try:
                async with httpx.AsyncClient(timeout=5, verify=False) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                for email in email_regex.findall(response.text):
                    if is_valid_email(email):
                        print(f"[find_contact_email] Found {email} via Google")
                        return {"email": email, "source": "google"}

                urls_checked += 1
            except Exception:
                continue

        await asyncio.sleep(1)
    except Exception:
        pass

    print(f"[find_contact_email] No email found for {business_name}")
    return {"email": None, "source": "not_found"}
