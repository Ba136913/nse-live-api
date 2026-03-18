from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn
import time
import os
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cached_data = {
    "status": "loading",
    "timestamp": "Connecting to NSE India...",
    "data": {"indices": [], "top_gainers": [], "top_losers": []}
}

def fetch_nse_official_data():
    global cached_data
    
    # 🕵️‍♂️ Anti-Bot Headers (NSE ko lagna chahiye hum Chrome browser use kar rahe hain)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/live-market-indices"
    }
    
    while True:
        try:
            session = requests.Session()
            
            # Step 1: Wake up NSE & get cookies
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(1) 
            
            # Step 2: Fetch EXACT F&O Stocks from NSE
            fo_url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
            fo_res = session.get(fo_url, headers=headers, timeout=10)
            
            if fo_res.status_code == 200:
                fo_data = fo_res.json().get("data", [])
                
                clean_fo = []
                for stock in fo_data:
                    # Ignore the NIFTY 50 row that comes inside the data
                    if stock.get("symbol") != "NIFTY 50" and stock.get("lastPrice"):
                        clean_fo.append({
                            "Symbol": stock.get("symbol"),
                            "LTP": round(stock.get("lastPrice", 0), 2),
                            "Change_Percent": round(stock.get("pChange", 0), 2)
                        })
                
                # Sort exactly like NSE Top Gainers/Losers
                sorted_fo = sorted(clean_fo, key=lambda x: x['Change_Percent'], reverse=True)
                top_gainers = sorted_fo[:20]
                
                # Losers (Lowest negative first)
                top_losers = sorted(clean_fo, key=lambda x: x['Change_Percent'])[:20]
            else:
                raise Exception(f"NSE Blocked F&O (Status: {fo_res.status_code})")

            # Step 3: Fetch Sectoral Indices from NSE
            idx_url = "https://www.nseindia.com/api/allIndices"
            idx_res = session.get(idx_url, headers=headers, timeout=10)
            
            if idx_res.status_code == 200:
                idx_data = idx_res.json().get("data", [])
                target_indices = ["NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY AUTO", "NIFTY PHARMA", "NIFTY METAL"]
                
                clean_indices = []
                for idx in idx_data:
                    if idx.get("index") in target_indices:
                        clean_indices.append({
                            "Index": idx.get("index"),
                            "LTP": round(idx.get("last", 0), 2),
                            "Change_Percent": round(idx.get("percentChange", 0), 2)
                        })
            else:
                raise Exception("NSE Blocked Indices")

            # Update Final Data
            cached_data = {
                "status": "success",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S") + " IST",
                "data": {
                    "indices": clean_indices,
                    "top_gainers": top_gainers,
                    "top_losers": top_losers
                }
            }
            print(f"✅ EXACT NSE Data Synced at {cached_data['timestamp']}")
            
        except Exception as e:
            print(f"⚠️ NSE Fetch Error: {e}")
            if cached_data["status"] == "loading":
                cached_data["timestamp"] = "Connection Error (NSE Blocked). Retrying..."
                
        time.sleep(60) # Refresh har 1 minute mein

# Background loop chalu karo
threading.Thread(target=fetch_nse_official_data, daemon=True).start()

@app.get("/api/live-data")
def get_live_data():
    return cached_data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
