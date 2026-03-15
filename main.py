from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, uvicorn, threading, time, os, httpx
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AI CONFIG ---
GROQ_API_KEY = "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"

try:
    groq_client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client())
except Exception as e:
    print(f"❌ Groq Error: {e}")
    groq_client = None

cached_data = {
    "live_data": {"status": "loading", "top_gainers": [], "top_losers": []},
    "sectoral": {"status": "loading", "data": []},
    "sentiment": {"score": 50, "label": "Neutral 🟡", "color": "#f59e0b"},
    "last_updated": "Wait..."
}

class ChatRequest(BaseModel):
    message: str

def calculate_sentiment(g_count, l_count):
    total = g_count + l_count
    if total == 0: return {"score": 50, "label": "Neutral 🟡", "color": "#f59e0b"}
    score = (g_count / total) * 100
    if score > 70: return {"score": score, "label": "Extreme Bullish 🔥", "color": "#10b981"}
    if score > 55: return {"score": score, "label": "Bullish 🟢", "color": "#22c55e"}
    if score < 35: return {"score": score, "label": "Extreme Bearish 💀", "color": "#ef4444"}
    if score < 45: return {"score": score, "label": "Bearish 🔴", "color": "#f87171"}
    return {"score": score, "label": "Neutral 🟡", "color": "#f59e0b"}

# --- 180+ F&O STOCKS MASTER LIST ---
FO_STOCKS = (
    "AARTIIND,ABB,ABBOTINDIA,ABCAPITAL,ABFRL,ACC,ADANIENT,ADANIPORTS,ALKEM,AMBUJACEM,APOLLOHOSP,APOLLOTYRE,"
    "ASHOKLEY,ASIANPAINT,ASTRAL,ATUL,AUBANK,AUROPHARMA,AXISBANK,BAJAJ-AUTO,BAJAJFINSV,BAJFINANCE,BALKRISIND,"
    "BALRAMCHIN,BANDHANBNK,BANKBARODA,BATAINDIA,BEL,BERGEPAINT,BHARATFORG,BHARTIARTL,BHEL,BIOCON,BOSCHLTD,BPCL,"
    "BRITANNIA,BSOFT,CANBK,CANFINHOME,CHAMBLFERT,CHOLAFIN,CIPLA,COALINDIA,COFORGE,COLPAL,CONCOR,COROMANDEL,"
    "CROMPTON,CUB,CUMMINSIND,DABUR,DALBHARAT,DEEPAKNTR,DIVISLAB,DIXON,DLF,DRREDDY,EICHERMOT,ESCORTS,EXIDEIND,"
    "FEDERALBNK,GAIL,GLENMARK,GMRINFRA,GNFC,GODREJCP,GODREJPROP,GRANULES,GRASIM,GUJGASLTD,HAL,HAVELLS,HCLTECH,"
    "HDFCAMC,HDFCBANK,HDFCLIFE,HEROMOTOCO,HINDALCO,HINDCOPPER,HINDPETRO,HINDUNILVR,ICICIBANK,ICICIGI,ICICIPRULI,"
    "IDEA,IDFCFIRSTB,IEX,IGL,INDHOTEL,INDIACEM,INDIAMART,INDIGO,INDUSINDBK,INDUSTOWER,INFY,IOC,IPCALAB,IRCTC,ITC,"
    "JINDALSTEL,JKCEMENT,JSWSTEEL,JUBLFOOD,KOTAKBANK,LALPATHLAB,LAURUSLABS,LICHSGFIN,LT,LTIM,LTTS,LUPIN,M&M,"
    "M&MFIN,MANAPPURAM,MARICO,MARUTI,MCX,METROPOLIS,MFSL,MGL,MOTHERSON,MPHASIS,MRF,MUTHOOTFIN,NATIONALUM,NAUKRI,"
    "NAVINFLUOR,NESTLEIND,NMDC,NTPC,OBEROIRLTY,OFSS,ONGC,PAGEIND,PEL,PERSISTENT,PETRONET,PFC,PIDILITIND,PIIND,PNB,"
    "POLYCAB,POWERGRID,PVRINOX,RAMCOCEM,RBLBANK,RECLTD,RELIANCE,SAIL,SBICARD,SBILIFE,SBIN,SHREECEM,SIEMENS,SRF,"
    "SUNPHARMA,SUNTV,SYNGENE,TATACHEM,TATACOMM,TATACONSUM,TATAMOTORS,TATAPOWER,TATASTEEL,TCS,TECHM,TITAN,"
    "TORNTPHARM,TRENT,TVSMOTOR,UBL,ULTRACEMCO,UPLLTD,VEDL,VOLTAS,WIPRO,ZEEL,ZYDUSLIFE"
)

INDICES = "^NSEI,^NSEBANK,^CNXIT,^CNXAUTO,^CNXPHARMA,^CNXMETAL"
YF_HEADERS = {'User-Agent': 'Mozilla/5.0'}

def fetch_market_data():
    global cached_data
    
    # .NS lagana zaroori hai Yahoo Finance ke liye
    symbols_list = [s + ".NS" for s in FO_STOCKS.split(",")]
    batch_size = 40 # 40 stocks ek baar mein bhejenge taaki API crash na ho
    
    while True:
        try:
            all_clean_stocks = []
            
            # 1. BATCH PROCESSING FOR 180+ STOCKS
            for i in range(0, len(symbols_list), batch_size):
                batch = symbols_list[i:i+batch_size]
                symbols_str = ",".join(batch)
                
                s_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_str}"
                response = requests.get(s_url, headers=YF_HEADERS, timeout=10)
                
                if response.status_code == 200:
                    s_data = response.json().get('quoteResponse', {}).get('result', [])
                    for s in s_data:
                        all_clean_stocks.append({
                            "Symbol": s.get('symbol', '').replace('.NS', ''),
                            "LTP": round(s.get('regularMarketPrice', 0), 2),
                            "Change": round(s.get('regularMarketChangePercent', 0), 2),
                            "Volume": s.get('regularMarketVolume', 0)
                        })
                
                # Small delay between batches to respect Rate Limits
                time.sleep(0.5) 
                
            if all_clean_stocks:
                # 2. SORTING LOGIC (Top 20 Gainers & Losers)
                sorted_stocks = sorted(all_clean_stocks, key=lambda x: x['Change'], reverse=True)
                top_gainers = sorted_stocks[:20] 
                
                # Reverse sort for losers so most negative comes first
                top_losers = sorted(sorted_stocks[-20:], key=lambda x: x['Change']) 
                
                # 3. SENTIMENT METER (Out of 180+ stocks)
                g_count = len([x for x in all_clean_stocks if x['Change'] > 0])
                l_count = len(all_clean_stocks) - g_count
                cached_data["sentiment"] = calculate_sentiment(g_count, l_count)
                
                cached_data["live_data"] = {
                    "status": "success", 
                    "top_gainers": top_gainers, 
                    "top_losers": top_losers
                }

            # 4. FETCH INDICES
            i_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={INDICES}"
            i_resp = requests.get(i_url, headers=YF_HEADERS, timeout=10)
            if i_resp.status_code == 200:
                i_data = i_resp.json().get('quoteResponse', {}).get('result', [])
                idx_map = {"^NSEI": "NIFTY 50", "^NSEBANK": "BANK NIFTY", "^CNXIT": "NIFTY IT", "^CNXAUTO": "NIFTY AUTO", "^CNXPHARMA": "NIFTY PHARMA", "^CNXMETAL": "NIFTY METAL"}
                clean_indices = [{"name": idx_map.get(i.get('symbol'), i.get('symbol')), "ltp": round(i.get('regularMarketPrice', 0), 2), "chng": round(i.get('regularMarketChangePercent', 0), 2)} for i in i_data]
                cached_data["sectoral"] = {"status": "success", "data": clean_indices}

            cached_data["last_updated"] = time.strftime("%H:%M:%S")
            print(f"✅ Master Sync Done (180+ Stocks): {cached_data['last_updated']} | Gainers: {g_count}, Losers: {l_count}")

        except Exception as e:
            print(f"⚠️ Master Fetch Error: {e}")
            cached_data["sentiment"]["label"] = "Syncing... 🔄"
            
        time.sleep(120) # 2 min wait before next full scan

threading.Thread(target=fetch_market_data, daemon=True).start()

# --- API ENDPOINTS ---
@app.get("/api/all-data")
def get_all(): return cached_data

@app.post("/api/chat")
def chat_ai(req: ChatRequest):
    if not groq_client: return {"reply": "Bhai, AI key check kar!"}
    try:
        mood = cached_data['sentiment']['label']
        top_g = cached_data['live_data']['top_gainers'][0]['Symbol'] if cached_data['live_data']['top_gainers'] else "N/A"
        
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": f"You are Gemini Bhai, a savage Quant F&O Trader. Market Mood: {mood}. Top Stock right now: {top_g}. Speak Hinglish. Be energetic and data-driven!"},
                {"role": "user", "content": req.message}
            ],
            max_tokens=300
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"reply": f"AI Error: {str(e)}"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
