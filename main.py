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

# Global dictionary to store data so API is fast
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

def fetch_google_finance_data():
    global cached_data
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    while True:
        try:
            all_stocks_data = []
            
            # Fetch data for each stock from Google Finance (HTML parsing based on specific classes)
            # This is slower but highly resistant to blocking compared to Yahoo/NSE
            for symbol in FO_STOCKS:
                url = f"https://www.google.com/finance/quote/{symbol}:NSE"
                try:
                    response = requests.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        text = response.text
                        
                        # Very basic text extraction (Jugaad method to avoid heavy BeautifulSoup library)
                        # Finding LTP
                        ltp_marker = 'class="YMlKec fxKbKc">'
                        ltp_start = text.find(ltp_marker)
                        if ltp_start != -1:
                            ltp_start += len(ltp_marker)
                            ltp_end = text.find('<', ltp_start)
                            ltp_str = text[ltp_start:ltp_end].replace('₹', '').replace(',', '')
                            ltp = float(ltp_str)
                            
                            # Finding Percentage Change
                            chg_marker = 'class="JwB6zf" style="font-size:16px;">'
                            chg_start = text.find(chg_marker)
                            chg = 0.0
                            if chg_start != -1:
                                chg_start += len(chg_marker)
                                chg_end = text.find('%', chg_start)
                                chg_str = text[chg_start:chg_end]
                                # Google formats negative changes with a specific character, check raw text
                                if "-" in chg_str or "−" in chg_str: # Handles different minus signs
                                    chg = -float(chg_str.replace("-", "").replace("−", "").strip())
                                else:
                                    chg = float(chg_str.replace("+", "").strip())
                                    
                            all_stocks_data.append({
                                "Symbol": symbol,
                                "LTP": ltp,
                                "Change_Percent": chg,
                                "Volume": "N/A" # Live volume is hard to scrape reliably here
                            })
                except Exception as inner_e:
                    continue # Skip stock if error
                    
                time.sleep(0.5) # Crucial: Don't hammer Google too fast

            if all_stocks_data:
                # Sort the data
                sorted_stocks = sorted(all_stocks_data, key=lambda x: x['Change_Percent'], reverse=True)
                top_gainers = sorted_stocks[:20]
                top_losers = sorted(sorted_stocks[-20:], key=lambda x: x['Change_Percent']) # Gets most negative

                cached_data = {
                    "status": "success",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "data": {
                        "top_gainers": top_gainers,
                        "top_losers": top_losers
                    }
                }
                print(f"✅ Data Synced via Google Finance at {cached_data['timestamp']}")

        except Exception as e:
            print(f"⚠️ Error fetching data: {e}")
            if cached_data["status"] == "loading":
                cached_data["status"] = "error"
                cached_data["timestamp"] = "Failed to fetch data"

        # Wait 3 minutes before next full scrape to avoid bans
        time.sleep(180) 

# Start the background fetching thread
threading.Thread(target=fetch_google_finance_data, daemon=True).start()

@app.get("/api/live-data")
def get_live_market_data():
    return cached_data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
