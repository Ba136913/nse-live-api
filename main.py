from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import uvicorn
import threading
import time
import os
import httpx
from groq import Groq

app = FastAPI()

# CORS Bypass taaki frontend connect ho sake
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
# Teri key maine yahan integrate kar di hai bhai 🔥
GROQ_API_KEY = "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"

# Groq initialization with "Proxy Fix" for Render
try:
    groq_client = Groq(
        api_key=GROQ_API_KEY,
        http_client=httpx.Client()
    )
except Exception as e:
    print(f"❌ Groq Init Error: {e}")
    groq_client = None

cached_data = {
    "live_data": {"status": "loading", "top_gainers": [], "top_losers": []},
    "sectoral": {"status": "loading", "data": []},
    "sentiment": {"score": 50, "label": "Neutral 🟡", "color": "#f59e0b"},
    "last_updated": "Wait..."
}

class ChatRequest(BaseModel):
    message: str

# --- LOGIC: MARKET MOOD ---
def calculate_sentiment(gainers, losers):
    g_count = len(gainers)
    l_count = len(losers)
    total = g_count + l_count
    if total == 0: return {"score": 50, "label": "Neutral 🟡", "color": "#f59e0b"}
    
    score = (g_count / total) * 100
    if score > 70: return {"score": score, "label": "Extreme Bullish 🔥", "color": "#10b981"}
    if score > 55: return {"score": score, "label": "Bullish 🟢", "color": "#22c55e"}
    if score < 35: return {"score": score, "label": "Extreme Bearish 💀", "color": "#ef4444"}
    if score < 45: return {"score": score, "label": "Bearish 🔴", "color": "#f87171"}
    return {"score": score, "label": "Neutral 🟡", "color": "#f59e0b"}

# --- NSE DATA FETCHER (Runs in Background) ---
def fetch_nse_data():
    global cached_data
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Referer': 'https://www.nseindia.com/'
    }
    
    while True:
        try:
            # Wake up NSE Session
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(2)
            
            # 1. Top Gainers/Losers
            g_url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
            l_url = "https://www.nseindia.com/api/live-analysis-variations?index=loosers"
            
            g_raw = session.get(g_url, headers=headers).json().get("FOSec", {}).get("data", [])
            l_raw = session.get(l_url, headers=headers).json().get("FOSec", {}).get("data", [])
            
            cached_data["sentiment"] = calculate_sentiment(g_raw, l_raw)
            
            def clean(s): return {"Symbol": s.get("symbol"), "LTP": s.get("ltp"), "Change": s.get("perChange")}
            
            cached_data["live_data"] = {
                "status": "success",
                "top_gainers": [clean(x) for x in g_raw[:20]],
                "top_losers": [clean(x) for x in l_raw[:20]]
            }

            # 2. Sectoral Performance
            s_url = "https://www.nseindia.com/api/allIndices"
            s_raw = session.get(s_url, headers=headers).json().get("data", [])
            
            cached_data["sectoral"] = {
                "status": "success",
                "data": [{"name": i['index'], "ltp": i['last'], "chng": i['percentChange']} for i in s_raw if i['key'] == "SECTORAL INDICES"]
            }
            
            cached_data["last_updated"] = time.strftime("%H:%M:%S")
            print(f"✅ Data Synced Successfully at {cached_data['last_updated']}")

        except Exception as e:
            print(f"❌ NSE Error: {e}")
        
        time.sleep(120) # Update every 2 mins

# Background Thread Start
threading.Thread(target=fetch_nse_data, daemon=True).start()

# --- API ENDPOINTS ---
@app.get("/api/all-data")
def get_all():
    return cached_data

@app.post("/api/chat")
def chat_ai(req: ChatRequest):
    if not groq_client:
        return {"reply": "Bhai, AI start nahi ho raha. Check logs! ⚠️"}
    try:
        mood = cached_data['sentiment']['label']
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": f"You are Gemini Bhai, a savage Desi Stock Market Mentor. Answer in Hinglish. Current Market Mood: {mood}. Be bold, energetic, and helpful."},
                {"role": "user", "content": req.message}
            ]
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Bhai AI ne mana kar diya: {str(e)}"}

if __name__ == "__main__":
    # Render Dynamic Port logic
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
