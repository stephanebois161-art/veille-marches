"""Sonde temporaire n°2."""
import json, urllib.request, re

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
def get(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}; h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=25) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()[:300]
    except Exception as e: return "ERR", str(e).encode()

for tz in ["55", "58", "8"]:
    s, b = get("https://www.investing.com/economic-calendar/Service/getCalendarFilteredData",
        data=f"country%5B%5D=5&importance%5B%5D=3&dateFrom=2026-11-02&dateTo=2026-11-06&timeZone={tz}&timeFilter=timeOnly&currentTab=custom&limit_from=0".encode(),
        headers={"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/x-www-form-urlencoded", "Referer": "https://www.investing.com/economic-calendar/"})
    html = json.loads(b)["data"]
    print("\n== tz", tz, s, re.findall(r'data-event-datetime="([^"]+)"', html)[:3])
    if tz == "55":
        rows = html.split("<tr")
        for r in rows[:4]: print("ROW:", r[:2500].replace("\n", " "))
        print("NB lignes événement:", len(re.findall(r'eventRowId_', html)))

def scan(market, flt, cols):
    q = {"filter": flt, "columns": cols, "range": [0, 500]}
    s, b = get(f"https://scanner.tradingview.com/{market}/scan", data=json.dumps(q).encode(), headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com"})
    return s, b
cols = ["name", "description", "exchange", "type", "is_primary", "earnings_release_next_date", "earnings_release_next_time"]
us = "AAPL ABTC AI AMD AMZN APP ARLO ARM ASML ASST AVGO BABA BMNR BRUN BTBT BTDR BX CAN CANG CIFR CLSK COIN CORZ CRCL CRWD CRWV DELL DOCU EBAY ETOR FRMM GEMI GLW GLXY GME GOOGL HE HIMS HLIT HOOD HUT IBM INTC IREN KO MARA MAT MDB META MRNA MRVL MSFT MSTR MU NBIS NFLX NKE NOK NTNX NVDA OKLO ORCL PLAB PLTR PYPL QCOM RIOT RIVN RKLB RR SBET SBUX SKHY SMCI SNAP SNDK SNOW SPCX SVIA TSLA TSM VFS WDC XXI ZM B CDE FNV HL NEM RGLD SVM EXK WPM".split()
s, b = scan("america", [{"left": "name", "operation": "in_range", "right": us}, {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX", "CBOE"]}], cols)
print("\n== TV america", s)
d = json.loads(b); found = {}
for r in d.get("data", []): print(" ", r["s"], r["d"][1:]); found.setdefault(r["d"][0], []).append(r["s"])
print("MANQUANTS US:", [t for t in us if t not in found]); print("DOUBLONS:", {k: v for k, v in found.items() if len(v) > 1})
eu = "AC AI AL2SI ALFEN ALGAE ALKAL ATO CA CAP CDI DSY EDEN EL EN FDJU FR GLE KER MC NXI RI SOI STMPA TEP TRI TTE UBI VIRI WLN".split()
s, b = scan("global", [{"left": "name", "operation": "in_range", "right": eu}, {"left": "exchange", "operation": "equal", "right": "EURONEXT"}], cols)
print("\n== TV euronext", s)
d = json.loads(b); found = {}
for r in d.get("data", []): print(" ", r["s"], r["d"][1:]); found.setdefault(r["d"][0], []).append(r["s"])
print("MANQUANTS EU:", [t for t in eu if t not in found])
q = {"symbols": {"tickers": ["TSX:BB", "KRX:005930", "NSE:HYUNDAI", "HKEX:1810", "OTC:MTPLF", "FWB:HY9H"]}, "columns": cols}
s, b = get("https://scanner.tradingview.com/global/scan", data=json.dumps(q).encode(), headers={"Content-Type": "application/json"})
print("\n== TV autres", s, b.decode()[:1500])
