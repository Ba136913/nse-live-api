from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, uvicorn, threading, time, os, httpx
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
# Teri Nayi Key yahan fit kar di hai bhai 🔥
GROQ_API_KEY = "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"

try:
    # Proxy fix for Render environment
    groq_client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client())
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
            # Wake up session
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(2)
            
            # API Calls
            g_resp = session.get("https://www.nseindia.com/api/live-analysis-variations?index=gainers", headers=headers, timeout=10).json()
            l_resp = session.get("https://www.nseindia.com/api/live-analysis-variations?index=loosers", headers=headers, timeout=10).json()
            
            g_raw = g_resp.get("FOSec", {}).get("data", [])
            l_raw = l_resp.get("FOSec", {}).get("data", [])
            
            def clean(s): return {"Symbol": s.get("symbol"), "LTP": s.get("ltp"), "Change": s.get("perChange")}
            
            cached_data["live_data"] = {
                "status": "success",
                "top_gainers": [clean(x) for x in g_raw[:15]],
                "top_losers": [clean(x) for x in l_raw[:15]]
            }
            
            # Simple Sentiment Logic
            if len(g_raw) > len(l_raw):
                cached_data["sentiment"] = {"score": 75, "label": "Bullish 🟢", "color": "#10b981"}
            else:
                cached_data["sentiment"] = {"score": 25, "label": "Bearish 🔴", "color": "#ef4444"}

            cached_data["last_updated"] = time.strftime("%H:%M:%S")
            print(f"✅ NSE Sync Done at {cached_data['last_updated']}")

        except Exception as e:
            print(f"⚠️ NSE Fetch Issue: {e}")
            # Dashboard ko crash hone se bachane ke liye "Wait" state
            cached_data["sentiment"]["label"] = "Syncing... 🔄"
        
        time.sleep(120)

# Start background sync
threading.Thread(target=fetch_nse_data, daemon=True).start()

@app.get("/api/all-data")
def get_all(): 
    return cached_data

@app.post("/api/chat")
def chat_ai(req: ChatRequest):
    if not groq_client:
        return {"reply": "Bhai, AI key initialize nahi ho payi. ⚠️"}
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are Gemini Bhai, a savage Indian Stock Market mentor. Speak in Hinglish. Be energetic!"},
                {"role": "user", "content": req.message}
            ],
            max_tokens=300
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        # Check for Invalid API Key error in logs
        print(f"❌ AI Error: {e}")
        return {"reply": "Bhai, key mein kuch gadbad lag rahi hai, check logs! ⚠️"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
