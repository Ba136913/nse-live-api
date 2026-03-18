from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn
import time
import os
import threading

app = FastAPI()

# Ye line bohot zaroori hai taaki GitHub Pages Render se data le sake
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cached_data = {"status": "loading", "timestamp": "Initializing...", "data": {"top_gainers": [], "top_losers": []}}

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

def fetch_data_job():
    global cached_data
    headers = {"User-Agent": "Mozilla/5.0"}
    batch_size = 40 
    all_stocks_data = []
    
    for i in range(0, len(FO_STOCKS), batch_size):
        batch = FO_STOCKS[i:i+batch_size]
        symbols_str = ",".join([s + ".NS" for s in batch])
        url = f"https://query2.finance.yahoo.com/v8/finance/spark?symbols={symbols_str}&range=1d"
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                results = res.json().get('spark', {}).get('result', [])
                for stock in results:
                    try:
                        sym = stock.get('symbol', '').replace('.NS', '')
                        meta = stock.get('response', [{}])[0].get('meta', {})
                        ltp = meta.get('regularMarketPrice', 0.0)
                        prev = meta.get('chartPreviousClose', 0.0)
                        
                        if ltp > 0 and prev > 0:
                            chg_pct = ((ltp - prev) / prev) * 100
                            all_stocks_data.append({"Symbol": sym, "LTP": round(ltp, 2), "Change_Percent": round(chg_pct, 2), "Volume": "Live"})
                    except: continue
        except Exception as e: print(f"Batch Error: {e}")
        time.sleep(0.5)

    if all_stocks_data:
        sorted_stocks = sorted(all_stocks_data, key=lambda x: x['Change_Percent'], reverse=True)
        cached_data = {
            "status": "success",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": {"top_gainers": sorted_stocks[:20], "top_losers": sorted(sorted_stocks[-20:], key=lambda x: x['Change_Percent'])}
        }

def background_loop():
    while True:
        time.sleep(120)
        fetch_data_job()

fetch_data_job()
threading.Thread(target=background_loop, daemon=True).start()

@app.get("/api/live-data")
def get_live_market_data():
    return cached_data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
