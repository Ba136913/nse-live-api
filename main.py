from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # Pydantic v1 syntax
import requests
import uvicorn
import threading
import time
from groq import Groq
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
GROQ_API_KEY = "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" 
groq_client = Groq(api_key=GROQ_API_KEY)

cached_data = {
    "live_data": {"status": "loading", "top_gainers": [], "top_losers": []},
    "sectoral": {"status": "loading", "data": []},
    "sentiment": {"score": 50, "label": "Neutral 🟡", "color": "#f59e0b"},
    "last_updated": "Wait..."
}

# Pydantic v1 Model
class ChatRequest(BaseModel):
    message: str

# --- SENTIMENT LOGIC ---
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

# --- NSE BACKGROUND SYNC ---
def fetch_nse_data():
    global cached_data
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    while True:
        try:
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(1)
            g_data = session.get("https://www.nseindia.com/api/live-analysis-variations?index=gainers", headers=headers).json().get("FOSec", {}).get("data", [])
            l_data = session.get("https://www.nseindia.com/api/live-analysis-variations?index=loosers", headers=headers).json().get("FOSec", {}).get("data", [])
            cached_data["sentiment"] = calculate_sentiment(g_data, l_data)
            def clean(s): return {"Symbol": s.get("symbol"), "LTP": s.get("ltp"), "Change": s.get("perChange")}
            cached_data["live_data"] = {"status": "success", "top_gainers": [clean(x) for x in g_data[:20]], "top_losers": [clean(x) for x in l_data[:20]]}
            s_data = session.get("https://www.nseindia.com/api/allIndices", headers=headers).json().get("data", [])
            cached_data["sectoral"] = {"status": "success", "data": [{"name": i['index'], "ltp": i['last'], "chng": i['percentChange']} for i in s_data if i['key'] == "SECTORAL INDICES"]}
            cached_data["last_updated"] = time.strftime("%H:%M:%S")
        except: pass
        time.sleep(120)

threading.Thread(target=fetch_nse_data, daemon=True).start()

@app.get("/api/all-data")
def get_all(): return cached_data

@app.post("/api/chat")
def chat_ai(req: ChatRequest):
    try:
        mood = cached_data['sentiment']['label']
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": f"You are Gemini Bhai, a Desi Trader. Mood: {mood}"}, {"role": "user", "content": req.message}]
        )
        return {"reply": response.choices[0].message.content}
    except: return {"reply": "Bhai, AI thoda busy hai!"}

if __name__ == "__main__":
    # Render port dynamically assign karta hai, isliye os.environ zaroori hai
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
