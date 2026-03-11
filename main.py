from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Frontend ko is API se connect karne ki permission (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Koi bhi website is API ko call kar sakti hai
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
        # Cookies set karo
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        # Data fetch karo
        gainers_url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
        losers_url = "https://www.nseindia.com/api/live-analysis-variations?index=loosers"
        
        gainers_response = session.get(gainers_url, headers=headers, timeout=10).json()
        losers_response = session.get(losers_url, headers=headers, timeout=10).json()
        
        raw_gainers = gainers_response.get("FOSec", {}).get("data", [])
        raw_losers = losers_response.get("FOSec", {}).get("data", [])
        
        def clean_data(stock_list):
            cleaned = []
            for stock in stock_list[:20]: # Top 20 
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