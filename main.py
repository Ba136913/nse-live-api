from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import requests
import os
import time
import threading

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NSE F&O Stock List (Yahoo Finance Format)
NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "SBIN.NS",
    "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "BAJFINANCE.NS", "TITAN.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
    "BAJAJFINSV.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "JSWSTEEL.NS", "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS", "BPCL.NS", "BRITANNIA.NS",
    "CIPLA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HEROMOTOCO.NS",
    "HINDALCO.NS", "HINDZINC.NS", "INDUSINDBK.NS", "JINDALSTEL.NS", "M&M.NS", "SBILIFE.NS",
    "SHRIRAMFIN.NS", "TECHM.NS", "TATACONSUM.NS", "TATAPOWER.NS", "TORNTPHARM.NS", "TVSMOTOR.NS",
    "ADANIGREEN.NS", "APOLLOHOSP.NS", "BANDHANBNK.NS", "BEL.NS", "CANBK.NS", "DABUR.NS", "DLF.NS",
    "GODREJCP.NS", "HAVELLS.NS", "HCLTECH.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS", "INDIGO.NS",
    "IRCTC.NS", "JIOFIN.NS", "LALPATHLAB.NS", "MUTHOOTFIN.NS", "NAUKRI.NS", "NMDC.NS", "NYKAA.NS",
    "OFSS.NS", "PAYTM.NS", "PERSISTENT.NS", "PNB.NS", "POLYCAB.NS", "PVRINOX.NS", "RAMCOCEM.NS",
    "RBLBANK.NS", "SBICARD.NS", "SIEMENS.NS", "SRF.NS", "UNIONBANK.NS", "VBL.NS", "VEDL.NS",
    "ZOMATO.NS", "ABB.NS", "ALKEM.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASTRAL.NS", "AUROPHARMA.NS",
    "BAJAJ-AUTO.NS", "BALKRISIND.NS", "BATAINDIA.NS", "BERGEPAINT.NS", "BHEL.NS", "BIOCON.NS",
    "CROMPTON.NS", "CUMMINSIND.NS", "DIXON.NS", "ESCORTS.NS", "FEDERALBNK.NS", "GAIL.NS",
    "GLENMARK.NS", "GODREJPROP.NS", "HAL.NS", "IDBI.NS", "IGL.NS", "INDHOTEL.NS", "IRFC.NS",
    "LICHSGFIN.NS", "LUPIN.NS", "M&MFIN.NS", "MARICO.NS", "MOTHERSON.NS", "NATIONALUM.NS",
    "NAVINFLUOR.NS", "OBEROIRLTY.NS", "PETRONET.NS", "PFC.NS", "PIIND.NS", "PNBHOUSING.NS",
    "RECLTD.NS", "SAIL.NS", "STARHEALTH.NS", "SUPREMEIND.NS", "TATACHEM.NS", "THERMAX.NS",
    "UPL.NS", "VOLTAS.NS", "YESBANK.NS", "ZYDUSWELL.NS"
]

# Global data store
market_data = {
    "status": "loading",
    "timestamp": "",
    "data": {
        "top_gainers": [],
        "top_losers": []
    }
}

data_lock = threading.Lock()

def fetch_yahoo_data():
    """Fetch stock data from Yahoo Finance API"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    all_stocks = []
    batch_size = 50
    
    for i in range(0, len(NSE_STOCKS), batch_size):
        batch = NSE_STOCKS[i:i + batch_size]
        try:
            symbols = ",".join(batch)
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                continue
            
            data = response.json()
            quotes = data.get("quoteResponse", {}).get("result", [])
            
            for quote in quotes:
                symbol = quote.get("symbol", "")
                ltp = quote.get("regularMarketPrice")
                prev_close = quote.get("previousClose")
                
                if ltp and prev_close and prev_close > 0:
                    change = ltp - prev_close
                    pct_change = (change / prev_close) * 100
                    volume = quote.get("regularMarketVolume", 0)
                    
                    all_stocks.append({
                        "Symbol": symbol.replace(".NS", ""),
                        "LTP": round(ltp, 2),
                        "Change_Percent": round(pct_change, 2),
                        "Volume": volume
                    })
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching batch {i}: {e}")
            continue
    
    return all_stocks

def update_market_data():
    """Background worker to fetch and process market data"""
    global market_data
    
    time.sleep(5)
    
    while True:
        try:
            print("Fetching market data...")
            stocks = fetch_yahoo_data()
            
            if stocks and len(stocks) > 10:
                gainers = sorted(stocks, key=lambda x: x['Change_Percent'], reverse=True)[:20]
                losers = sorted(stocks, key=lambda x: x['Change_Percent'])[:20]
                
                with data_lock:
                    market_data = {
                        "status": "success",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "data": {
                            "top_gainers": gainers,
                            "top_losers": losers
                        }
                    }
                print(f"Data updated: {len(gainers)} gainers, {len(losers)} losers")
            else:
                print(f"Insufficient data received: {len(stocks)} stocks")
                
        except Exception as e:
            print(f"Error in background worker: {e}")
        
        time.sleep(120)

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=update_market_data, daemon=True)
    thread.start()

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NSE F&O Live Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        .header { text-align: center; margin-bottom: 30px; }
        h1 { font-size: 2rem; margin-bottom: 10px; color: #00d4ff; }
        .status-bar { display: flex; justify-content: center; gap: 20px; align-items: center; flex-wrap: wrap; }
        .timestamp { font-size: 14px; color: #8892b0; }
        .refresh-btn { background: #00d4ff; color: #1a1a2e; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: 600; }
        .refresh-btn:hover { background: #00a8cc; }
        .refresh-btn:disabled { background: #444; cursor: not-allowed; }
        .container { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; max-width: 1400px; margin: 0 auto; }
        .table-card { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); }
        .card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .gainers-title { color: #00ff88; }
        .losers-title { color: #ff4757; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
        th { color: #8892b0; font-size: 12px; text-transform: uppercase; font-weight: 600; }
        .symbol { font-weight: 600; color: #fff; }
        .ltp { font-family: 'Courier New', monospace; color: #00d4ff; }
        .positive { color: #00ff88; font-weight: 600; }
        .negative { color: #ff4757; font-weight: 600; }
        .volume { color: #8892b0; font-size: 13px; }
        .loader { text-align: center; padding: 60px 20px; }
        .spinner { width: 50px; height: 50px; border: 4px solid rgba(255,255,255,0.1); border-top-color: #00d4ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .error-box { background: rgba(255,71,87,0.1); border: 1px solid #ff4757; border-radius: 8px; padding: 20px; text-align: center; margin: 20px auto; max-width: 500px; }
        .error-box h3 { color: #ff4757; margin-bottom: 10px; }
        .loading-note { background: rgba(0,212,255,0.1); border: 1px solid #00d4ff; border-radius: 8px; padding: 15px; text-align: center; margin: 20px auto; max-width: 500px; color: #8892b0; }
        .live-indicator { display: inline-block; width: 10px; height: 10px; background: #00ff88; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @media (max-width: 768px) { .container { grid-template-columns: 1fr; } h1 { font-size: 1.5rem; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 NSE F&O Live Dashboard</h1>
        <div class="status-bar">
            <span class="timestamp" id="timestamp"><span class="live-indicator"></span>Initializing...</span>
            <button class="refresh-btn" id="refresh-btn" onclick="fetchData()">🔄 Refresh</button>
        </div>
    </div>
    <div id="error-container"></div>
    <div id="loader" class="loader">
        <div class="spinner"></div>
        <p>Loading market data...</p>
        <div class="loading-note">⏱️ First load may take 30-60 seconds. Data refreshes every 2 minutes.</div>
    </div>
    <div id="data-container" class="container" style="display: none;">
        <div class="table-card">
            <div class="card-header"><span class="gainers-title">🟢</span><h2 class="gainers-title">Top 20 Gainers</h2></div>
            <table>
                <thead><tr><th>Symbol</th><th>LTP (₹)</th><th>% Change</th><th>Volume</th></tr></thead>
                <tbody id="gainers-body"></tbody>
            </table>
        </div>
        <div class="table-card">
            <div class="card-header"><span class="losers-title">🔴</span><h2 class="losers-title">Top 20 Losers</h2></div>
            <table>
                <thead><tr><th>Symbol</th><th>LTP (₹)</th><th>% Change</th><th>Volume</th></tr></thead>
                <tbody id="losers-body"></tbody>
            </table>
        </div>
    </div>
    <script>
        let isLoading = false;
        let retryCount = 0;
        const MAX_RETRIES = 15;
        async function fetchData() {
            if (isLoading) return;
            isLoading = true;
            const btn = document.getElementById('refresh-btn');
            btn.disabled = true;
            btn.textContent = '⏳ Loading...';
            try {
                const response = await fetch('/api/live-data');
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error('Server returned non-JSON response');
                }
                const result = await response.json();
                if (result.status === 'success' && result.data && result.data.top_gainers && result.data.top_gainers.length > 0) {
                    document.getElementById('error-container').innerHTML = '';
                    document.getElementById('loader').style.display = 'none';
                    document.getElementById('data-container').style.display = 'grid';
                    document.getElementById('timestamp').innerHTML = '<span class="live-indicator"></span>Last Updated: ' + result.timestamp + ' IST';
                    renderTable('gainers-body', result.data.top_gainers, true);
                    renderTable('losers-body', result.data.top_losers, false);
                    retryCount = 0;
                } else {
                    throw new Error('Data not ready yet. Please wait...');
                }
            } catch (error) {
                retryCount++;
                console.error('Fetch error:', error);
                if (retryCount >= MAX_RETRIES) {
                    document.getElementById('loader').style.display = 'none';
                    document.getElementById('error-container').innerHTML = '<div class="error-box"><h3>⚠️ Connection Error</h3><p>' + error.message + '</p><p style="margin-top:10px;">Please refresh the page or try again later.</p></div>';
                } else {
                    document.getElementById('error-container').innerHTML = '<div class="loading-note">⏱️ Still loading... (Attempt ' + retryCount + '/' + MAX_RETRIES + ')<br>' + error.message + '</div>';
                }
            } finally {
                isLoading = false;
                btn.disabled = false;
                btn.textContent = '🔄 Refresh';
            }
        }
        function renderTable(tbodyId, data, isGainer) {
            const tbody = document.getElementById(tbodyId);
            tbody.innerHTML = '';
            data.forEach(stock => {
                const sign = isGainer ? '+' : '';
                const colorClass = isGainer ? 'positive' : 'negative';
                const volume = formatVolume(stock.Volume);
                const row = document.createElement('tr');
                row.innerHTML = '<td class="symbol">' + escapeHtml(stock.Symbol) + '</td><td class="ltp">₹' + stock.LTP.toFixed(2) + '</td><td class="' + colorClass + '">' + sign + stock.Change_Percent.toFixed(2) + '%</td><td class="volume">' + volume + '</td>';
                tbody.appendChild(row);
            });
        }
        function formatVolume(vol) {
            if (vol >= 10000000) return (vol / 10000000).toFixed(2) + ' Cr';
            if (vol >= 100000) return (vol / 100000).toFixed(2) + ' L';
            if (vol >= 1000) return (vol / 1000).toFixed(2) + ' K';
            return vol.toString();
        }
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        fetchData();
        setInterval(fetchData, 120000);
    </script>
</body>
</html>"""
    return html_content

@app.get("/api/live-data", response_class=JSONResponse)
async def get_live_data():
    with data_lock:
        return market_data

@app.get("/health", response_class=JSONResponse)
async def health_check():
    return {"status": "healthy", "data_available": market_data["status"] == "success"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
