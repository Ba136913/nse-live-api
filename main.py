from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn
import threading
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Storage (In-Memory Cache)
cached_data = {
    "live_data": {"status": "loading", "data": None},
    "sectoral": {"status": "loading", "data": None},
    "last_updated": "Never"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nseindia.com/'
}

def fetch_from_nse():
    """Background worker jo NSE se data nikalta rahega"""
    global cached_data
    session = requests.Session()
    session.headers.update(HEADERS)
    
    while True:
        try:
            # Step 1: Visit main site for cookies
            session.get("https://www.nseindia.com", timeout=10)
            time.sleep(2)
            
            # Step 2: Fetch Gainers/Losers
            g_url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
            l_url = "https://www.nseindia.com/api/live-analysis-variations?index=loosers"
            
            g_resp = session.get(g_url, timeout=10).json()
            l_resp = session.get(l_url, timeout=10).json()
            
            def clean(stocks):
                return [{"Symbol": s.get("symbol"), "LTP": s.get("ltp"), "Change_Percent": s.get("perChange"), "Volume": s.get("trade_quantity")} for s in stocks[:20]]

            cached_data["live_data"] = {
                "status": "success",
                "timestamp": g_resp.get("FOSec", {}).get("timestamp"),
                "data": {"top_gainers": clean(g_resp.get("FOSec", {}).get("data", [])), "top_losers": clean(l_resp.get("FOSec", {}).get("data", []))}
            }

            # Step 3: Fetch Sectoral
            s_url = "https://www.nseindia.com/api/allIndices"
            s_resp = session.get(s_url, timeout=10).json()
            
            sectoral_list = []
            for item in s_resp.get("data", []):
                if item.get("key") == "SECTORAL INDICES":
                    sectoral_list.append({
                        "Index_Name": item.get("index"),
                        "Current_LTP": item.get("last"),
                        "Percent_Change": item.get("percentChange"),
                        "Open_Price": item.get("open")
                    })
            cached_data["sectoral"] = {"status": "success", "data": sectoral_list}
            cached_data["last_updated"] = time.strftime("%H:%M:%S")
            
            print(f"✅ Data Updated at {cached_data['last_updated']}")
            
        except Exception as e:
            print(f"❌ Fetch Error: {e}")
        
        # 2 Minute wait before next fetch
        time.sleep(120)

# Start background thread
threading.Thread(target=fetch_from_nse, daemon=True).start()

@app.get("/api/live-data")
def get_live_market_data():
    return cached_data["live_data"]

@app.get("/api/sectoral-indices")
def get_sectoral_indices():
    return cached_data["sectoral"]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
