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
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def fetch_market_data():
    global cached_data
    symbols_list = [s + ".NS" for s in FO_STOCKS.split(",")]
    batch_size = 40 
    
    while True:
        try:
            all_clean_stocks = []
            
            for i in range(0, len(symbols_list), batch_size):
                batch = symbols_list[i:i+batch_size]
                symbols_str = ",".join(batch)
                
                url = f"https://query2.finance.yahoo.com/v8/finance/spark?symbols={symbols_str}&range=1d"
                response = requests.get(url, headers=HEADERS, timeout=10)
                
                if response.status_code == 200:
                    results = response.json().get('spark', {}).get('result', [])
                    for res in results:
                        try:
                            sym = res.get('symbol', '').replace('.NS', '')
                            meta = res.get('response', [{}])[0].get('meta', {})
                            ltp = meta.get('regularMarketPrice', 0)
                            prev = meta.get('chartPreviousClose', 0)
                            
                            if ltp and prev and prev > 0:
                                chg = ((ltp - prev) / prev) * 100
                                all_clean_stocks.append({
                                    "Symbol": sym,
                                    "LTP": round(ltp, 2),
                                    "Change": round(chg, 2)
                                })
                        except:
                            continue
                time.sleep(1) 
            
            if all_clean_stocks:
                sorted_stocks = sorted(all_clean_stocks, key=lambda x: x['Change'], reverse=True)
                top_gainers = sorted_stocks[:20] 
                top_losers = sorted(sorted_stocks[-20:], key=lambda x: x['Change']) 
                
                g_count = len([x for x in all_clean_stocks if x['Change'] > 0])
                l_count = len(all_clean_stocks) - g_count
                cached_data["sentiment"] = calculate_sentiment(g_count, l_count)
                
                cached_data["live_data"] = {
                    "status": "success", 
                    "top_gainers": top_gainers, 
                    "top_losers": top_losers
                }

            i_url = f"https://query2.finance.yahoo.com/v8/finance/spark?symbols={INDICES}&range=1d"
            i_resp = requests.get(i_url, headers=HEADERS, timeout=10)
            if i_resp.status_code == 200:
                i_results = i_resp.json().get('spark', {}).get('result', [])
                idx_map = {"^NSEI": "NIFTY 50", "^NSEBANK": "BANK NIFTY", "^CNXIT": "NIFTY IT", "^CNXAUTO": "NIFTY AUTO", "^CNXPHARMA": "NIFTY PHARMA", "^CNXMETAL": "NIFTY METAL"}
                clean_indices = []
                for res in i_results:
                    try:
                        sym = res.get('symbol', '')
                        meta = res.get('response', [{}])[0].get('meta', {})
                        ltp = meta.get('regularMarketPrice', 0)
                        prev = meta.get('chartPreviousClose', 0)
                        
                        if ltp and prev and prev > 0:
                            chg = ((ltp - prev) / prev) * 100
                            clean_indices.append({
                                "name": idx_map.get(sym, sym),
                                "ltp": round(ltp, 2),
                                "chng": round(chg, 2)
                            })
                    except:
                        continue
                if clean_indices:
                    cached_data["sectoral"] = {"status": "success", "data": clean_indices}

            cached_data["last_updated"] = time.strftime("%H:%M:%S")

        except Exception as e:
            if cached_data["last_updated"] == "Wait...":
                cached_data["sentiment"]["label"] = "Syncing... 🔄"
            
        time.sleep(120)

threading.Thread(target=fetch_market_data, daemon=True).start()

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
                {"role": "system", "content": f"You are Gemini Bhai, a savage Quant F&O Trader. Market Mood: {mood}. Top Stock: {top_g}. Speak Hinglish. Be energetic!"},
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
