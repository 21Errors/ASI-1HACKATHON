# Vendly AI

**Vendly AI** is an Autonomous B2B Lead Intelligence worldwide platform built for the ASI Hackathon. It helps freelancers, agencies, and B2B service providers find local and global business leads, analyze their online footprint, and automatically generate hyper-personalized, high-converting cold outreach pitches.

## 🚀 Features

- **Geospatial Business Discovery**: Find local businesses (restaurants, gyms, clinics, etc.) near you or globally using OSM-based reverse geocoding.
- **Intelligent Document Parsing**: Upload a casual bio, CV, or company profile, and our ASI-1 powered engine extracts professional services and recommends the best industries to target.
- **Autonomous Lead Research**: Select a business, and the AI actively browses the web to research the company's online presence, reviews, and local competitors.
- **Hyper-Personalized Pitches**: Generates custom sales emails based on real-time web data, aligning your exact skills with the business's specific pain points.
- **Automated Outreach & Tracking**: Send the generated emails seamlessly via your Gmail account with built-in open-tracking pixels.

## 🧠 Powered by ASI-1

This project makes extensive use of the **ASI-1** model via the ASI API, deeply integrated into both the backend AI processing and frontend UI.

- **Real-Time Web Search for Lead Context**: Uses `web_search=True` (passed in the `extra_body` payload) to give ASI-1 the ability to browse the real internet. It researches local competitors, regional market news, and specific pain points for the target business before generating its pitch.
- **Streaming UI (Server-Sent Events)**: Uses `stream=True` to provide a fast, dynamic UI that types out the AI's complex reasoning and sales pitch chunk-by-chunk directly to the user interface.
- **Zero-Shot Service Inference**: Replaces traditional keyword matching with deep reasoning. ASI-1 can read heavily unstructured text like "I build stuff out of wood" and infer structured, professional services like "Carpentry" or "Custom Furniture", and creatively map them to surprising B2B target industries (like recommending a carpenter partner with local event venues).
- **Strict JSON Enforcement**: Driven by strict system prompts to output highly complex, nested JSON objects powering our internal data contracts (e.g., arrays of `pain_points`, `recommended_industries` with dynamically calculated `fit_scores`, and structured seller profiles). 
- **Dual Verification UI (ASI-1 Score vs Heuristic Score)**: The frontend integrates an *ASI-1 Refined Score* feature. It actively compares the application's internal heuristic matching algorithm against ASI-1's deep reasoning score. Lead cards feature golden animated UI badges and a "Best Leads" banner that dynamically updates based exclusively on ASI-1's real-time judgement capabilities.

For a full breakdown of ASI1 integration, see [ASI1_HACKATHON_USAGE.md](ASI1_HACKATHON_USAGE.md).

## 🛠️ Setup & Installation

### Requirements
- Python 3.8+
- ASI-1 API Key

### 1. Clone & Install
```bash
git clone <repository-url>
cd asihackathon
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```
Fill out your `.env` file:
```env
ASI1_API_KEY=your_asi1_key_here
ASI1_BASE_URL=https://api.asi1.ai/v1
ASI1_MODEL=asi1-mini

# Optional: To enable email sending via Gmail
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

### 3. Run the Application
```bash
python -m uvicorn main:app --reload --port 8000
```
Then visit `http://localhost:8000` in your browser.

## 📁 Project Structure

- `frontend/` - HTML, CSS, JS containing the UI logic and Map features.
- `backend/` - FastAPI backend application.
  - `doc_parser.py` - ASI-1 CV & profile parsing logic.
  - `researcher.py` - ASI-1 Web-search powered email generation.
  - `finder.py` - Geospatial location and OSM API queries.
  - `emailer.py` - Gmail sending and pixel tracking infrastructure.
- `data/` - Caches and JSON stores for lead tracking.
- `main.py` - App entry point.

## 🤝 Hackathon Submission
Created for the ASI Hackathon. Check out the demo video to see the live ASI-1 web search capabilities in action!
