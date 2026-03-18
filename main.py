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
    "timestamp": "Connecting to Market...",
    "data": {"indices": [], "top_gainers": [], "top_losers": []}
}

# --- 180+ F&O STOCKS MASTER LIST ---
FO_STOCKS = [
    "AARTIIND","ABB","ABBOTINDIA","ABCAPITAL","ABFRL","ACC","ADANIENT","ADANIPORTS","ALKEM","AMBUJACEM",
    "APOLLOHOSP","APOLLOTYRE","ASHOKLEY","ASIANPAINT","ASTRAL","ATUL","AUBANK","AUROPHARMA","AXISBANK",
    "BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND","BALRAMCHIN","BANDHANBNK","BANKBARODA","BATAINDIA",
    "BEL","BERGEPAINT","BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL","BRITANNIA","BSOFT",
    "CANBK","CANFINHOME","CHAMBLFERT","CHOLAFIN","CIPLA","COALINDIA","COFORGE","COLPAL","CONCOR",
    "COROMANDEL","CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR","DIVISLAB","DIXON","DLF",
    "DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","GAIL","GLENMARK","GMRINFRA","GNFC","GODREJCP",
    "GODREJPROP","GRANULES","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCAMC","HDFCBANK","HDFCLIFE",
    "HEROMOTOCO","HINDALCO","HINDCOPPER","HINDPETRO","HINDUNILVR","ICICIBANK","ICICIGI","ICICIPRULI","IDEA",
    "IDFCFIRSTB","IEX","IGL","INDHOTEL","INDIACEM","INDIAMART","INDIGO","INDUSINDBK","INDUSTOWER","INFY",
    "IOC","IPCALAB","IRCTC","ITC","JINDALSTEL","JKCEMENT","JSWSTEEL","JUBLFOOD","KOTAKBANK","LALPATHLAB",
    "LAURUSLABS","LICHSGFIN","LT","LTIM","LTTS","LUPIN","M&M","M&MFIN","MANAPPURAM","MARICO","MARUTI","MCX",
    "METROPOLIS","MFSL","MGL","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN","NATIONALUM","NAUKRI","NAVINFLUOR",
    "NESTLEIND","NMDC","NTPC","OBEROIRLTY","OFSS","ONGC","PAGEIND","PEL","PERSISTENT","PETRONET","PFC",
    "PIDILITIND","PIIND","PNB","POLYCAB","POWERGRID","PVRINOX","RAMCOCEM","RBLBANK","RECLTD","RELIANCE",
    "SAIL","SBICARD","SBILIFE","SBIN","SHREECEM","SIEMENS","SRF","SUNPHARMA","SUNTV","SYNGENE","TATACHEM",
    "TATACOMM","TATACONSUM","TATAMOTORS","TATAPOWER","TATASTEEL","TCS","TECHM","TITAN","TORNTPHARM","TRENT",
    "TVSMOTOR","UBL","ULTRACEMCO","UPLLTD","VEDL","VOLTAS","WIPRO","ZEEL","ZYDUSLIFE"
]

# 🔥 ALL SECTORAL INDICES ADDED HERE 🔥
INDICES = {
    "NSE:NIFTY": "NIFTY 50",
    "NSE:BANKNIFTY": "NIFTY BANK",
    "NSE:CNXIT": "NIFTY IT",
    "NSE:CNXAUTO": "NIFTY AUTO",
    "NSE:CNXFMCG": "NIFTY FMCG",
    "NSE:CNXMEDIA": "NIFTY MEDIA",
    "NSE:CNXMETAL": "NIFTY METAL",
    "NSE:CNXPHARMA": "NIFTY PHARMA",
    "NSE:CNXPSUBANK": "NIFTY PSU BANK",
    "NSE:CNXREALTY": "NIFTY REALTY",
    "NSE:CNXENERGY": "NIFTY ENERGY",
    "NSE:CNXCONSUM": "NIFTY CONSUMER"
}

def fetch_tradingview_data():
    global cached_data
    
    tv_stocks = ["NSE:" + s for s in FO_STOCKS]
    tv_indices = list(INDICES.keys())
    url = "https://scanner.tradingview.com/india/scan"
    
    payload_stocks = {
        "symbols": {"tickers": tv_stocks},
        "columns": ["name", "close", "change"]
    }
    
    payload_indices = {
        "symbols": {"tickers": tv_indices},
        "columns": ["name", "close", "change"]
    }
    
    while True:
        try:
            # 1. Fetch Stocks (100% Block-Proof)
            res_stocks = requests.post(url, json=payload_stocks, timeout=10)
            stock_data = res_stocks.json().get("data", [])
            
            all_stocks = []
            for item in stock_data:
                d = item.get("d", [])
                if len(d) >= 3:
                    all_stocks.append({
                        "Symbol": d[0],
                        "LTP": round(d[1], 2) if d[1] else 0,
                        "Change_Percent": round(d[2], 2) if d[2] else 0
                    })
            
            # 2. Fetch All Sectoral Indices
            res_indices = requests.post(url, json=payload_indices, timeout=10)
            idx_data = res_indices.json().get("data", [])
            
            all_indices = []
            for item in idx_data:
                ticker = item.get("s", "")
                d = item.get("d", [])
                if len(d) >= 3:
                    all_indices.append({
                        "Index": INDICES.get(ticker, d[0]),
                        "LTP": round(d[1], 2) if d[1] else 0,
                        "Change_Percent": round(d[2], 2) if d[2] else 0
                    })

            # 3. Sort & Update Data
            if all_stocks:
                sorted_stocks = sorted(all_stocks, key=lambda x: x['Change_Percent'], reverse=True)
                cached_data = {
                    "status": "success",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S") + " IST",
                    "data": {
                        "indices": all_indices,
                        "top_gainers": sorted_stocks[:20],
                        "top_losers": sorted(sorted_stocks[-20:], key=lambda x: x['Change_Percent'])
                    }
                }
                print(f"✅ Data Synced Successfully at {cached_data['timestamp']}")
            else:
                cached_data["timestamp"] = "⚠️ Fetch Error. Retrying..."
                
        except Exception as e:
            print(f"⚠️ Fetch Error: {e}")
            if cached_data["status"] == "loading":
                cached_data["timestamp"] = "Connection Error. Retrying..."
                
        time.sleep(60) # Fast 1-minute updates!

# Start background thread
threading.Thread(target=fetch_tradingview_data, daemon=True).start()

@app.get("/api/live-data")
def get_live_data():
    return cached_data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
