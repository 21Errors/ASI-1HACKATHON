# How We Used ASI1 in Vendly AI

This document explains the powerful ways we leveraged the **ASI1 API** to build the core intelligence of **Vendly AI**. We used ASI-1 as the central brain of our application, utilizing its advanced reasoning, structured JSON output capabilities, streaming features, and most importantly, its **native web search** functionality.

Here are the two major integrations:

## 1. The Autonomous Lead Researcher (with Web Search & Streaming)
**File**: `backend/researcher.py`

This is where ASI-1 truly shines. When a user selects a potential business lead, we don't just generate a generic email. We use ASI-1 to actively research the business in real-time.

**Key Technical Details:**
* **`web_search=True`**: We pass this parameter in the `extra_body` of our API call. This instructs ASI-1 to act as an "expert global B2B sales consultant with web search capability." It actively searches the internet for:
  * The specific business's online presence, website content, and reviews.
  * Recent news about the business or its industry in that specific city/region.
  * Local competitor landscape.
  * Specific pain points for that industry in that country.
* **Hyper-Personalized Sales Pitches**: Using the web search data, ASI-1 crafts a highly customized, natural-sounding cold outreach email. It writes a "best angle," identifies specific "pain points," and generates a confidence score.
* **Server-Sent Events (SSE) Streaming**: We utilize `stream=True` to stream chunks of the AI's thought process and generated pitch directly to the frontend, creating a responsive and engaging user experience.
* **JSON Enforcement**: We use strict system prompts to force ASI-1 to return ONLY a structured JSON object containing the `fit_score`, `score_reasoning`, `pain_points`, `best_angle`, and `email_body`.

## 2. The Intelligent Document Parser (Inference Engine)
**File**: `backend/doc_parser.py`

To understand the seller's profile, we use ASI-1 to parse unstructured documents (like CVs, casual bios, or social media text) and build a structured "Seller Profile".

**Key Technical Details:**
* **Inference-Based Service Extraction**: Instead of just extracting literal words, we prompt ASI-1 to *infer* what services someone can sell. For example, if a bio says "I make wooden horses," ASI-1 correctly infers and standardizes the services to "Carpentry, Custom Woodworking, Artisan Crafts".
* **Creative Industry Matching**: We use ASI-1's reasoning to recommend B2B industries that the seller should target. For example, it might figure out that a carpenter could partner with real estate companies for home staging, or event venues for custom builds.
* **Complex JSON Schemas**: We guide ASI-1 to return a deeply nested JSON structure containing arrays of services (with confidence scores), skill lists, and a ranked list of target industries with calculated `fit_scores` based on the seller's background.

## Summary of ASI1 Features Used:
* `web_search=True` integration for real-time intelligence gathering.
* `stream=True` for fast, responsive UI updates.
* Strict JSON formatting for reliable frontend-backend data contracts.
* Advanced contextual inference (reading between the lines of a CV).
