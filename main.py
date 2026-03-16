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

# Global dictionary
cached_data = {
    "status": "loading",
    "timestamp": "Wait...",
    "data": {
        "top_gainers": [],
        "top_losers": []
    }
}

# --- 180+ F&O STOCKS MASTER LIST ---
FO_STOCKS = [
    "AARTIIND","ABB","ABBOTINDIA","ABCAPITAL","ABFRL","ACC","ADANIENT","ADANIPORTS","ALKEM","AMBUJACEM","APOLLOHOSP","APOLLOTYRE",
    "ASHOKLEY","ASIANPAINT","ASTRAL","ATUL","AUBANK","AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND",
    "BALRAMCHIN","BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT","BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL",
    "BRITANNIA","BSOFT","CANBK","CANFINHOME","CHAMBLFERT","CHOLAFIN","CIPLA","COALINDIA","COFORGE","COLPAL","CONCOR","COROMANDEL",
    "CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR","DIVISLAB","DIXON","DLF","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND",
    "FEDERALBNK","GAIL","GLENMARK","GMRINFRA","GNFC","GODREJCP","GODREJPROP","GRANULES","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH",
    "HDFCAMC","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDCOPPER","HINDPETRO","HINDUNILVR","ICICIBANK","ICICIGI","ICICIPRULI",
    "IDEA","IDFCFIRSTB","IEX","IGL","INDHOTEL","INDIACEM","INDIAMART","INDIGO","INDUSINDBK","INDUSTOWER","INFY","IOC","IPCALAB","IRCTC","ITC",
    "JINDALSTEL","JKCEMENT","JSWSTEEL","JUBLFOOD","KOTAKBANK","LALPATHLAB","LAURUSLABS","LICHSGFIN","LT","LTIM","LTTS","LUPIN","M&M",
    "M&MFIN","MANAPPURAM","MARICO","MARUTI","MCX","METROPOLIS","MFSL","MGL","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN","NATIONALUM","NAUKRI",
    "NAVINFLUOR","NESTLEIND","NMDC","NTPC","OBEROIRLTY","OFSS","ONGC","PAGEIND","PEL","PERSISTENT","PETRONET","PFC","PIDILITIND","PIIND","PNB",
    "POLYCAB","POWERGRID","PVRINOX","RAMCOCEM","RBLBANK","RECLTD","RELIANCE","SAIL","SBICARD","SBILIFE","SBIN","SHREECEM","SIEMENS","SRF",
    "SUNPHARMA","SUNTV","SYNGENE","TATACHEM","TATACOMM","TATACONSUM","TATAMOTORS","TATAPOWER","TATASTEEL","TCS","TECHM","TITAN",
    "TORNTPHARM","TRENT","TVSMOTOR","UBL","ULTRACEMCO","UPLLTD","VEDL","VOLTAS","WIPRO","ZEEL","ZYDUSLIFE"
]

def format_volume(vol):
    """Volume ko readable banata hai (Lakhs/Crores me)"""
    if vol == 0 or vol == "N/A": return "N/A"
    if vol >= 10000000: return f"{vol/10000000:.2f} Cr"
    if vol >= 100000: return f"{vol/100000:.2f} L"
    return str(vol)

def fetch_yahoo_json_data():
    global cached_data
    
    # Session banate hain taaki Yahoo ko lage hum asli browser hain
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    })
    
    batch_size = 40 # Memory bachane ke liye 40-40 stocks ka batch
    
    while True:
        try:
            all_stocks_data = []
            
            # Initial dummy request to get cookies from Yahoo
            session.get("https://finance.yahoo.com", timeout=5)
            time.sleep(1)

            # Batched API Requests
            for i in range(0, len(FO_STOCKS), batch_size):
                batch = FO_STOCKS[i:i+batch_size]
                symbols_str = ",".join([s + ".NS" for s in batch])
                
                # Yahoo v7 API - Fastest & Most Accurate
                url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_str}"
                
                res = session.get(url, timeout=10)
                if res.status_code == 200:
                    results = res.json().get('quoteResponse', {}).get('result', [])
                    
                    for stock in results:
                        sym = stock.get('symbol', '').replace('.NS', '')
                        ltp = stock.get('regularMarketPrice', 0.0)
                        chg_pct = stock.get('regularMarketChangePercent', 0.0)
                        vol = stock.get('regularMarketVolume', 0)

                        if ltp > 0: # Sirf valid data add karo
                            all_stocks_data.append({
                                "Symbol": sym,
                                "LTP": round(ltp, 2),
                                "Change_Percent": round(chg_pct, 2),
                                "Volume": format_volume(vol)
                            })
                
                time.sleep(1) # Chhota break taaki Yahoo block na kare

            if all_stocks_data:
                # 2. Sort Gainers & Losers Exactly (Max positive to Max negative)
                sorted_stocks = sorted(all_stocks_data, key=lambda x: x['Change_Percent'], reverse=True)
                top_gainers = sorted_stocks[:20] 
                
                # Losers ke liye reverse order lenge (Sabse zyada gira hua pehle)
                top_losers = sorted(sorted_stocks[-20:], key=lambda x: x['Change_Percent']) 

                cached_data = {
                    "status": "success",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "data": {
                        "top_gainers": top_gainers,
                        "top_losers": top_losers
                    }
                }
                print(f"✅ Exact Data Synced! Scanned {len(all_stocks_data)} F&O Stocks.")

        except Exception as e:
            print(f"⚠️ API Fetch Error: {e}")
            if cached_data["status"] == "loading":
                cached_data["status"] = "error"
                cached_data["timestamp"] = "Fetch Failed. Retrying..."

        # Update every 2 mins
        time.sleep(120) 

# Start background thread
threading.Thread(target=fetch_yahoo_json_data, daemon=True).start()

@app.get("/api/live-data")
def get_live_market_data():
    return cached_data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
