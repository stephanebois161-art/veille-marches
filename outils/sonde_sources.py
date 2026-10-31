"""Sonde temporaire : teste quelles sources de calendrier sont joignables depuis GitHub Actions."""
import json, urllib.request, datetime as dt

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

def get(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:
        return "ERR", str(e).encode()

def show(name, status, body, n=600):
    print(f"\n===== {name} : {status} ({len(body)} octets)")
    print(body[:n].decode("utf-8", "replace"))

d1 = "2026-11-02"
# 1. ForexFactory (miroir JSON)
for w in ["thisweek", "nextweek"]:
    s, b = get(f"https://nfs.faireconomy.media/ff_calendar_{w}.json")
    show(f"FF {w}", s, b)
    try:
        ev = [e for e in json.loads(b) if e.get("country") == "USD" and e.get("impact") == "High"]
        print("USD High :", len(ev)); [print(" ", e["date"], e["title"], e.get("forecast"), e.get("previous")) for e in ev[:15]]
    except Exception as e: print("parse", e)

# 2. TradingView calendrier éco
s, b = get("https://economic-calendar.tradingview.com/events?from=2026-11-02T00:00:00.000Z&to=2026-11-07T00:00:00.000Z&countries=US",
           headers={"Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
show("TradingView eco", s, b, 300)
try:
    res = json.loads(b)["result"]
    print("total", len(res)); [print(" ", e["date"], e.get("importance"), e["title"], e.get("forecast"), e.get("previous")) for e in res if e.get("importance") == 1][:30]
except Exception as e: print("parse", e)

# 3. investing.com (service AJAX)
s, b = get("https://www.investing.com/economic-calendar/Service/getCalendarFilteredData",
           data=b"country%5B%5D=5&importance%5B%5D=3&dateFrom=2026-11-02&dateTo=2026-11-06&timeZone=58&timeFilter=timeOnly&currentTab=custom&limit_from=0",
           headers={"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/x-www-form-urlencoded", "Referer": "https://www.investing.com/economic-calendar/"})
show("investing.com AJAX", s, b, 400)

# 4. Nasdaq earnings
s, b = get(f"https://api.nasdaq.com/api/calendar/earnings?date={d1}", headers={"Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"})
show("Nasdaq earnings", s, b, 500)
s, b = get(f"https://api.nasdaq.com/api/calendar/economicevents?date={d1}", headers={"Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"})
show("Nasdaq eco", s, b, 500)

# 5. TradingView scanner (dates de résultats, toutes places)
q = {"symbols": {"tickers": ["NASDAQ:AAPL", "NASDAQ:AMD", "NYSE:PLTR", "EURONEXT:MC", "EURONEXT:TTE", "KRX:005930", "HKEX:1810", "TSX:BB", "NYSE:NEM"]},
     "columns": ["name", "earnings_release_next_date", "earnings_release_next_time", "earnings_per_share_forecast_next_fq", "revenue_forecast_next_fq", "earnings_release_date", "earnings_release_next_calendar_date"]}
s, b = get("https://scanner.tradingview.com/global/scan", data=json.dumps(q).encode(), headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com"})
show("TV scanner", s, b, 3000)
try:
    for r in json.loads(b)["data"]:
        v = r["d"]; nd = v[1]
        print(" ", r["s"], v[0], dt.datetime.utcfromtimestamp(nd).isoformat() if nd else None, v[2:])
except Exception as e: print("parse", e)

# 6. Yahoo
s, b = get("https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=calendarEvents")
show("Yahoo quoteSummary", s, b, 300)
s, b = get("https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL,MC.PA&fields=earningsTimestamp,earningsTimestampStart,earningsTimestampEnd,isEarningsDateEstimate")
show("Yahoo quote", s, b, 300)

# 7. Sources officielles
for name, u in [("Fed FOMC", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
                ("BLS calendrier ics", "https://www.bls.gov/schedule/news_release/bls.ics"),
                ("BEA", "https://www.bea.gov/news/schedule"),
                ("Alpha Vantage demo", "https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey=demo"),
                ("Earnings Whispers", "https://www.earningswhispers.com/api/caldata/20261102"),
                ("Zacks", "https://www.zacks.com/includes/classes/z2_class_calendarfunctions_data.php?calltype=eventscal&date=1793577600&type=1")]:
    s, b = get(u); show(name, s, b, 250)
