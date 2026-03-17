from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/live-data")
def get_live_market_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    session = requests.Session()
    
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        gainers_url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
        losers_url = "https://www.nseindia.com/api/live-analysis-variations?index=loosers"
        
        gainers_response = session.get(gainers_url, headers=headers, timeout=10).json()
        losers_response = session.get(losers_url, headers=headers, timeout=10).json()
        
        raw_gainers = gainers_response.get("FOSec", {}).get("data", [])
        raw_losers = losers_response.get("FOSec", {}).get("data", [])
        
        def clean_data(stock_list):
            cleaned = []
            for stock in stock_list[:20]: 
                cleaned.append({
                    "Symbol": stock.get("symbol"),
                    "LTP": stock.get("ltp"),
                    "Change_Percent": stock.get("perChange"),
                    "Volume": stock.get("trade_quantity")
                })
            return cleaned

        return {
            "status": "success",
            "timestamp": gainers_response.get("FOSec", {}).get("timestamp"),
            "data": {
                "top_gainers": clean_data(raw_gainers),
                "top_losers": clean_data(raw_losers)
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 🚀 FIX 3: Ye line add karni zaroori hai taaki Render server start kar sake!
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
