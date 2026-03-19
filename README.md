# Vendly AI

**Vendly AI** is an Autonomous B2B Lead Intelligence worldwide platform built for the ASI Hackathon. It helps freelancers, agencies, and B2B service providers find local and global business leads, analyze their online footprint, and automatically generate hyper-personalized, high-converting cold outreach pitches.

## 🚀 Features

- **Find Local Businesses**: Easily find local businesses (like restaurants, gyms, or clinics) anywhere in the world right on our interactive map.
- **Smart Profile Reader**: Just upload your casual bio or resume, and our AI will figure out exactly what professional services you offer and who you should sell them to.
- **Auto-Researcher**: Pick a business from the map, and our AI will automatically search the internet to read their website, check their reviews, and find out what they might need help with.
- **Perfect Sales Emails**: The AI writes a custom email for you that sounds totally natural and specifically mentions the business's current needs and how your unique skills can help them.
- **Easy Email Sending**: Send those perfect emails straight from your Gmail account without leaving the app, and see exactly when the business opens them!

## 🧠 Powered by ASI-1

We use the **ASI-1** AI model as the brain of Vendly AI. Here is how it works behind the scenes in simple terms:

### 1. The Smart Researcher & Writer (Using Web Search)
When you choose a business to contact, ASI-1 goes out onto the real internet. It reads their website, looks at their recent customer reviews, and figures out what problems they are currently facing. Then, it uses everything it found to write a highly personal, customized email that sounds like a real human wrote it. You can even watch it thinking and typing on the screen in real-time!

### 2. The Resume Reader (Smart Document Parser)
You can upload a super casual bio like "I build stuff out of wood," and ASI-1 is smart enough to understand that you are a professional Carpenter. It doesn't just look for exact keywords; it understands what your skills mean. Then, it uses that understanding to suggest the best types of businesses you should try to partner with.

### 3. Double-Checking the Match (AI Scoring)
Our app has a basic formula to guess if a business is a good match for you. But we also ask ASI-1 to give its own "Smart Score." When ASI-1's deep thinking decides a business is a perfect match, that business gets a special gold badge on the screen so you know exactly who to email first!

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
or
python main.py
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
