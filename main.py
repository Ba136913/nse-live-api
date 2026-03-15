from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pro-Level Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# Global Session: Ek baar session banega aur wahi reuse hoga
session = requests.Session()
session.headers.update(HEADERS)

def refresh_nse_session():
    """NSE ki main site visit karke cookies collect karne ke liye"""
    try:
        session.get("https://www.nseindia.com", timeout=10)
        # Chhota sa delay taaki NSE ko natural lage
        time.sleep(1) 
    except Exception as e:
        print(f"Session Refresh Error: {e}")

@app.get("/api/live-data")
def get_live_market_data():
    try:
        refresh_nse_session() # Har baar fresh cookies ensure karega
        
        gainers_url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
        losers_url = "https://www.nseindia.com/api/live-analysis-variations?index=loosers"
        
        gainers_resp = session.get(gainers_url, timeout=10).json()
        losers_resp = session.get(losers_url, timeout=10).json()
        
        raw_gainers = gainers_resp.get("FOSec", {}).get("data", [])
        raw_losers = losers_resp.get("FOSec", {}).get("data", [])
        
        def clean_data(stock_list):
            return [{"Symbol": s.get("symbol"), "LTP": s.get("ltp"), "Change_Percent": s.get("perChange"), "Volume": s.get("trade_quantity")} for s in stock_list[:20]]

        return {
            "status": "success",
            "timestamp": gainers_resp.get("FOSec", {}).get("timestamp"),
            "data": {"top_gainers": clean_data(raw_gainers), "top_losers": clean_data(raw_losers)}
        }
    except Exception as e:
        return {"status": "error", "message": f"NSE is blocking us or down: {str(e)}"}

@app.get("/api/sectoral-indices")
def get_sectoral_indices():
    try:
        refresh_nse_session()
        url = "https://www.nseindia.com/api/allIndices"
        response = session.get(url, timeout=10).json()
        
        sectoral_data = []
        for item in response.get("data", []):
            if item.get("key") == "SECTORAL INDICES":
                sectoral_data.append({
                    "Index_Name": item.get("index"),
                    "Current_LTP": item.get("last"),
                    "Percent_Change": item.get("percentChange"),
                    "Open_Price": item.get("open")
                })
        return {"status": "success", "data": sectoral_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
