from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import threading
import time
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hardcoded list of ~180 NSE F&O stock symbols (popular ones; expanded to ~180)
symbols = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS", "MARUTI.NS",
    "BAJFINANCE.NS", "BAJAJFINSV.NS", "AXISBANK.NS", "BHARTIARTL.NS", "HEROMOTOCO.NS",
    "ONGC.NS", "NTPC.NS", "GRASIM.NS", "ULTRACEMCO.NS", "INDUSINDBK.NS",
    "SUNPHARMA.NS", "BAJAJ-AUTO.NS", "POWERGRID.NS", "ADANIPORTS.NS", "DRREDDY.NS",
    "CIPLA.NS", "TATAMOTORS.NS", "WIPRO.NS", "M&M.NS", "JSWSTEEL.NS",
    "IOC.NS", "GAIL.NS", "ASIANPAINT.NS", "COLPAL.NS", "NESTLEIND.NS",
    "BAJAJHLDNG.NS", "HAVELLS.NS", "AMBUJACEM.NS", "COALINDIA.NS", "SHREECEM.NS",
    "SIEMENS.NS", "DIVISLAB.NS", "BERGEPAINT.NS", "PIDILITIND.NS", "MARICO.NS",
    "TATACONSUM.NS", "MCX.NS", "IGL.NS", "POLYCAB.NS", "VOLTAS.NS",
    "MRF.NS", "PFIZER.NS", "GODREJIND.NS", "UNITEDSPIRITS.NS", "BOSCHLTD.NS",
    "SRF.NS", "MINDTREE.NS", "IPCALAB.NS", "AKZOINDIA.NS", "CRISIL.NS",
    "LUPIN.NS", "WHIRLPOOL.NS", "EMAMILTD.NS", "ASHOKLEY.NS", "GILLETTE.NS",
    "AMARAJABAT.NS", "SYMPHONY.NS", "RAJESHEXPO.NS", "BAJAJELEC.NS", "SUNDRMFAST.NS",
    "BANARISUG.NS", "AVANTIFEED.NS", "ROYALORCHIDHOTELS.NS", "BALLARPUR.NS", "NAHARSPINGMILL.NS",
    "JISLJALEQS.NS", "KALPATPOWR.NS", "JBFIND.NS", "VSAN.NS", "COTTONFORMAT.NS",
    "PASSAVINTL.NS", "LADHUAUTO.NS", "SHILPAILS.NS", "FOSECOIND.NS", "GTLAN.NS",
    "BALLARPUR.NS", "ANDHRACEMENTS.NS", "SHIVALIK.NS", "VENKYS.NS", "SHANKARA.NS",
    "GUJAPOLLO.NS", "GOODYEAR.NS", "BRIDGEWORK.NS", "MADRASFERT.NS", "AGRO%20TECHFOODSLTD.NS",
    "FOODSIN.NS", "NAHARINDUS.NS", "KABRAEXTRUSION.NS", "ORIENTELEC.NS", "NIHARINFRA.NS",
    "DRKSHREERAM.NS", "PILITA.NS", "GET.D.NS", "SERVALL.NS", "RAMANEWS.NS",
    "DHRUV.NS", "VARDHANCEMENT.NS", "AJMERACEMENT.NS", "SAURASHCEM.NS", "BARAKAH.FILL.NS",
    "YCPL.NS", "HIRA%20CEMENT.NS", "GROVY.NS", "ORISSATEC.NS", "ANIKINDS.NS",
    "VINYLINDIA.NS", "POLYLINK.NS", "KERLA.NS", "MVN.NS", "FILATEX.NS",
    "DAMODARISPAT.NS", "SINTEX.NS", "PATINTLOG.NS", "NIFTYBEES.NS", "JPASSOCIAT.NS",
    "SUVEN.NS", "BLEED.BL.NS", "MANAPPURAM.NS", "CANFINHOME.NS", "PEL.NS",
    "PFC.NS", "RECLTD.NS", "NATIONALUM.NS", "NHPC.NS", "HCC.NS",
    "NMDC.NS", "SAIL.NS", "RPOWER.NS", "GAEL.NS", "MMTC.NS",
    "TATASTEEL.NS", "JINDALSTEL.NS", "ZEEL.NS", "TV18BRDCST.NS", "DISHTV.NS",
    "ZEELEARN.NS", "ENIL.NS", "ADANIENT.NS", "ADANIPOWER.NS", "ADANIGREEN.NS",
    "THERMAX.NS", "CGPOWER.NS", "CARBORUNIV.NS", "ABBOTINDIA.NS", "GLENMARK.NS",
    "TORNTPHARM.NS", "ALKEM.NS", "AUROPHARMA.NS", "BIOCON.NS", "CADILAHC.NS",
    "STAR.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "MAXINDIA.NS", "NAM-INDIA.NS",
    "BHARTI-INFRATEL.NS", "IDEA.NS", "RCOM.NS", "VODAFONEINDIA.NS", "TECHINICALTELLER.NS",
    "GSTL.NS", "KESORAMIND.NS", "JYOTHYLAB.NS", "GODFREYPHILLIPS.NS", "VSTIND.NS",
    "TCIFINANCE.NS", "AVANTI.NS", "SUNDARAM.NS", "RAMCOSUPERLEATHERS.NS", "CENTURYPLY.NS",
    "GREENPLY.NS", "LEEL.NS", "SHANKRA.NS", "NIVAKA.NS", "BLACKBOX.NS",
    "FRETAIL.NS", "SHRDIL.NS", "BILOWER.NS", "KYRO.NS", "SCHAFFHAUSEN.NS",
    "EPICENTRE.NS", "NSIL.NS", "PSL.NS", "INDOWIND.NS", "SMEANDTRUST.NS",
    "ACME.NS", "BIRLACABLE.NS", "FINOLEXIND.NS", "KEI.NS", "BUTTERFLY.NS",
    "JAIPRA.NS", "TTKPRESTIG.NS", "IFB.NS", "JOHNSON.NS", "KRBL.NS",
    "ALKALI.NS", "ASTEC.NS", "BALMERLAW.NS", "BALPHARMA.NS", "CANTABIL.NS",
    "COREPROJECTS.NS", "COSMOFRST.NS", "DCAL.NS", "DIGIDAY.NS", "EASTSILK.NS",
    "ECOM.NS", "FCS.NS", "GLITTEK.NS", "GNB.NS", "HCL-INSYS.NS",
    "HEXATRADEX.NS", "HUHTAMAKI.NS", "IBULISL.NS", "INDOCO.NS", "JKPAPER.NS"
]

data_store = {"gainers": [], "losers": [], "last_updated": None}

def fetch_batch(symbol_batch):
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(symbol_batch)}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching batch: {e}")
        return None

def fetch_all_data():
    all_data = []
    batch_size = 20  # Reduced batch size to avoid rate limits
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        result = fetch_batch(batch)
        if result and 'quoteResponse' in result and 'result' in result['quoteResponse']:
            all_data.extend(result['quoteResponse']['result'])
        time.sleep(2)  # Increased sleep to 2 seconds to avoid 429 errors
    return all_data

def process_and_store_data():
    raw_data = fetch_all_data()
    stock_data = []
    for item in raw_data:
        if 'regularMarketPrice' in item and 'regularMarketPreviousClose' in item and item['regularMarketPreviousClose'] != 0:
            symbol = item['symbol']
            ltp = item['regularMarketPrice']
            pc = item['regularMarketPreviousClose']
            change = ((ltp - pc) / pc) * 100
            stock_data.append({"symbol": symbol.replace(".NS", ""), "ltp": round(ltp, 2), "change": round(change, 2)})
    
    stock_data.sort(key=lambda x: x['change'], reverse=True)
    gainers = stock_data[:20]
    losers = stock_data[-20:]  # Last 20, which are most negative
    data_store["gainers"] = gainers
    data_store["losers"] = losers
    data_store["last_updated"] = time.time()
    logging.info("Data updated")

def background_fetch():
    while True:
        process_and_store_data()
        time.sleep(120)  # 2 minutes

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=background_fetch, daemon=True)
    thread.start()

@app.get("/api/live-data")
async def get_live_data():
    if not data_store["gainers"] and not data_store["losers"]:
        raise HTTPException(status_code=503, detail="Data not yet available")
    return {
        "gainers": data_store["gainers"],
        "losers": data_store["losers"],
        "last_updated": data_store["last_updated"]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
