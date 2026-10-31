"""Collecte le calendrier économique US (importance 3) et les dates de résultats
des sociétés suivies, puis écrit un fichier JSON lu par la tâche de veille.

Lancé chaque matin par GitHub Actions (.github/workflows/collecte-calendrier.yml).
Aucune clé ni donnée personnelle : uniquement des pages publiques.

Usage : python3 outils/collecte_calendrier.py [fichier_sortie.json]
"""
import datetime as dt
import html
import json
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
UTC = dt.timezone.utc
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
JOURS_FENETRE = 10  # aujourd'hui + 10 jours

# Liste fixe des sociétés suivies (même liste que le prompt de la veille).
US = ("AAPL ABTC AI AMD AMZN APP ARLO ARM ASML ASST AVGO BABA BMNR BRUN BTBT BTDR BX CAN CANG "
      "CIFR CLSK COIN CORZ CRCL CRWD CRWV DELL DOCU EBAY ETOR FRMM GEMI GLW GLXY GME GOOGL HE "
      "HIMS HLIT HOOD HUT IBM INTC IREN KO MARA MAT MDB META MRNA MRVL MSFT MSTR MU NBIS NFLX "
      "NKE NOK NTNX NVDA OKLO ORCL PLAB PLTR PYPL QCOM RIOT RIVN RKLB RR SBET SBUX SKHY SMCI "
      "SNAP SNDK SNOW SPCX SVIA TSLA TSM VFS WDC XXI ZM").split()
MINEURS = "B CDE FNV HL NEM RGLD SVM EXK WPM".split()
EURONEXT = ("AC AI AL2SI ALFEN ALGAE ALKAL ATO CA CAP CDI DSY EDEN EL EN FDJU FR GLE KER MC NXI "
            "RI SOI STMPA TEP TRI TTE UBI VIRI WLN").split()
AUTRES = ["TSX:BB", "KRX:005930", "NSE:HYUNDAI", "HKEX:1810", "OTC:MTPLF", "FWB:HY9H"]

erreurs = []


def requete(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    h.update(headers or {})
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        data = data.encode()
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def paris(ts_utc):
    return ts_utc.astimezone(PARIS)


def texte(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment or "")).replace("\xa0", " ").strip()


def nombre(v):
    if v in (None, ""):
        return None
    return v


# ---------------------------------------------------------------- Calendrier économique

def investing(debut, fin):
    """fr.investing.com / investing.com : États-Unis, importance 3 (3 taureaux). Heures en UTC (timeZone=55)."""
    corps = (f"country%5B%5D=5&importance%5B%5D=3&dateFrom={debut}&dateTo={fin}"
             "&timeZone=55&timeFilter=timeOnly&currentTab=custom&limit_from=0")
    brut = requete("https://www.investing.com/economic-calendar/Service/getCalendarFilteredData", data=corps,
                   headers={"X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Referer": "https://www.investing.com/economic-calendar/"})
    contenu = json.loads(brut)["data"]
    evenements = []
    for ligne in re.findall(r'<tr id="eventRowId_\d+".*?</tr>', contenu, flags=re.S):
        quand = re.search(r'data-event-datetime="([^"]+)"', ligne)
        heure_txt = texte((re.search(r'class="first left time[^"]*"\s*>(.*?)</td>', ligne, re.S) or [None, ""])[1])
        titre = texte((re.search(r'class="left event"[^>]*>(.*?)</td>', ligne, re.S) or [None, ""])[1])
        taureaux = ligne.count("grayFullBullishIcon")
        prevision = texte((re.search(r'id="eventForecast_\d+">(.*?)</td>', ligne, re.S) or [None, ""])[1])
        precedent = texte((re.search(r'id="eventPrevious_\d+">(.*?)</td>', ligne, re.S) or [None, ""])[1])
        if not quand or taureaux != 3:
            continue
        t = dt.datetime.strptime(quand.group(1), "%Y/%m/%d %H:%M:%S").replace(tzinfo=UTC)
        p = paris(t)
        sans_heure = not re.match(r"\d\d:\d\d", heure_txt)  # « All Day », « Tentative »…
        evenements.append({
            "date_paris": p.strftime("%Y-%m-%d"),
            "heure_paris": None if sans_heure else p.strftime("%H:%M"),
            "heure_new_york": None if sans_heure else t.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M"),
            "titre": titre,
            "importance": 3,
            "prevision": nombre(prevision),
            "precedent": nombre(precedent),
            "source": "investing.com",
        })
    return evenements


def tradingview_eco(debut, fin):
    """Calendrier économique TradingView : États-Unis, importance haute (= 1)."""
    url = ("https://economic-calendar.tradingview.com/events?"
           f"from={debut}T00:00:00.000Z&to={fin}T23:59:59.000Z&countries=US")
    res = json.loads(requete(url, headers={"Origin": "https://www.tradingview.com",
                                           "Referer": "https://www.tradingview.com/"}))["result"]
    evenements = []
    for e in res:
        if e.get("importance") != 1:
            continue
        t = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        p = paris(t)
        evenements.append({
            "date_paris": p.strftime("%Y-%m-%d"),
            "heure_paris": p.strftime("%H:%M"),
            "titre": e.get("title"),
            "prevision": e.get("forecast"),
            "precedent": e.get("previous"),
            "source": "tradingview",
        })
    return evenements


def recoupe(principal, secours):
    """Indique pour chaque événement investing s'il est aussi chez TradingView au même moment."""
    cles = {(e["date_paris"], e["heure_paris"]) for e in secours}
    for e in principal:
        e["recoupe_tradingview"] = (e["date_paris"], e["heure_paris"]) in cles
    return principal


# ---------------------------------------------------------------- Résultats d'entreprises

MOMENT_TV = {-1: "avant l'ouverture", 1: "après la clôture", 0: None}


def tv_scan(marche, requete_scan):
    colonnes = ["name", "description", "exchange", "earnings_release_next_date",
                "earnings_release_next_time", "earnings_per_share_forecast_next_fq",
                "revenue_forecast_next_fq"]
    requete_scan = dict(requete_scan, columns=colonnes, range=[0, 500])
    res = json.loads(requete(f"https://scanner.tradingview.com/{marche}/scan", data=requete_scan,
                             headers={"Origin": "https://www.tradingview.com"}))
    return [(r["s"], dict(zip(colonnes, r["d"]))) for r in res.get("data", [])]


def tradingview_resultats():
    lignes = []
    lignes += [("US", s, d) for s, d in tv_scan("america", {"filter": [
        {"left": "name", "operation": "in_range", "right": US},
        {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX", "CBOE"]}]})]
    lignes += [("Mineurs or/argent", s, d) for s, d in tv_scan("america", {"filter": [
        {"left": "name", "operation": "in_range", "right": MINEURS},
        {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}]})]
    lignes += [("Euronext", s, d) for s, d in tv_scan("global", {"filter": [
        {"left": "name", "operation": "in_range", "right": EURONEXT},
        {"left": "exchange", "operation": "equal", "right": "EURONEXT"}]})]
    lignes += [("Autres places", s, d) for s, d in tv_scan("global", {"symbols": {"tickers": AUTRES}})]

    trouves = {}
    for groupe, symbole, d in lignes:
        trouves[(groupe, d["name"])] = True
        ts = d.get("earnings_release_next_date")
        if not ts:
            continue
        t = dt.datetime.fromtimestamp(ts, UTC)
        code = d.get("earnings_release_next_time")
        moment = MOMENT_TV.get(code)
        heure_connue = code in (-1, 1)
        yield {
            "groupe": groupe,
            "symbole": symbole,
            "ticker": d["name"],
            "societe": d.get("description"),
            # Sans moment connu, TradingView place la date à midi UTC : seule la date compte.
            "date_paris": (paris(t) if heure_connue else t).strftime("%Y-%m-%d"),
            "heure_paris": paris(t).strftime("%H:%M") if heure_connue else None,
            "moment": moment,
            "bpa_prevu": round(d["earnings_per_share_forecast_next_fq"], 4)
            if d.get("earnings_per_share_forecast_next_fq") is not None else None,
            "ca_prevu": d.get("revenue_forecast_next_fq"),
            "source": "tradingview",
        }
    attendus = ([("US", t) for t in US] + [("Mineurs or/argent", t) for t in MINEURS]
                + [("Euronext", t) for t in EURONEXT] + [("Autres places", s.split(":")[1]) for s in AUTRES])
    manquants = [t for g, t in attendus if (g, t) not in trouves]
    if manquants:
        erreurs.append("TradingView ne connaît pas : " + ", ".join(manquants))


MOMENT_NASDAQ = {"time-pre-market": "avant l'ouverture", "time-after-hours": "après la clôture"}


def nasdaq_resultats(jours):
    """Calendrier des résultats Nasdaq (sociétés cotées aux États-Unis), jour par jour."""
    vus = {}
    for jour in jours:
        brut = requete(f"https://api.nasdaq.com/api/calendar/earnings?date={jour}",
                       headers={"Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"})
        lignes = ((json.loads(brut).get("data") or {}).get("rows")) or []
        for r in lignes:
            vus[r["symbol"]] = {"date": jour, "moment": MOMENT_NASDAQ.get(r.get("time")),
                                "bpa_prevu": r.get("epsForecast") or None}
    return vus


# ---------------------------------------------------------------- Assemblage

def prochain_jour_de_bourse(aujourdhui):
    """Lundi-jeudi : le lendemain ; vendredi, samedi, dimanche : le lundi suivant (jours fériés non gérés)."""
    j = aujourdhui + dt.timedelta(days=1)
    while j.weekday() >= 5:
        j += dt.timedelta(days=1)
    return j


def main():
    sortie = sys.argv[1] if len(sys.argv) > 1 else "calendrier.json"
    maintenant = dt.datetime.now(UTC)
    aujourdhui = paris(maintenant).date()
    debut, fin = aujourdhui.isoformat(), (aujourdhui + dt.timedelta(days=JOURS_FENETRE)).isoformat()
    jours_ouvres = [(aujourdhui + dt.timedelta(days=i)).isoformat() for i in range(JOURS_FENETRE + 1)
                    if (aujourdhui + dt.timedelta(days=i)).weekday() < 5]

    eco, eco_tv = [], []
    try:
        eco = investing(debut, fin)
    except Exception as e:
        erreurs.append(f"investing.com inaccessible : {e}")
    try:
        eco_tv = tradingview_eco(debut, fin)
    except Exception as e:
        erreurs.append(f"Calendrier TradingView inaccessible : {e}")
    if eco:
        eco = recoupe(eco, eco_tv)

    resultats = []
    try:
        resultats = list(tradingview_resultats())
    except Exception as e:
        erreurs.append(f"Scanner TradingView inaccessible : {e}")
    nasdaq = {}
    try:
        nasdaq = nasdaq_resultats(jours_ouvres)
    except Exception as e:
        erreurs.append(f"Calendrier Nasdaq inaccessible : {e}")
    for r in resultats:
        if r["groupe"] in ("US", "Mineurs or/argent") and r["ticker"] in nasdaq:
            n = nasdaq[r["ticker"]]
            r["nasdaq"] = n
            r["dates_concordantes"] = n["date"] == r["date_paris"] or (
                r["moment"] == "après la clôture" and n["date"] < r["date_paris"])
            if not r["moment"] and n["moment"]:
                r["moment"] = n["moment"]
                r["source"] = "tradingview + nasdaq"
    resultats = [r for r in resultats if debut <= r["date_paris"] <= fin]
    resultats.sort(key=lambda r: (r["date_paris"], r["heure_paris"] or "99", r["ticker"]))
    eco.sort(key=lambda e: (e["date_paris"], e["heure_paris"] or "99"))

    donnees = {
        "genere_le_utc": maintenant.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "genere_le_paris": paris(maintenant).strftime("%Y-%m-%d %H:%M"),
        "prochain_jour_de_bourse": prochain_jour_de_bourse(aujourdhui).isoformat(),
        "fenetre": {"debut": debut, "fin": fin},
        "lisez_moi": ("Heures en heure de Paris. economie = investing.com, États-Unis, importance 3 "
                      "uniquement (calendrier_tradingview = contrôle). resultats = sociétés suivies "
                      "uniquement ; heure_paris vide = heure non annoncée, moment indique avant "
                      "l'ouverture / après la clôture quand il est connu."),
        "economie": eco,
        "calendrier_tradingview": eco_tv,
        "resultats": resultats,
        "erreurs": erreurs,
    }
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    print(f"{len(eco)} annonces importance 3, {len(eco_tv)} TradingView, {len(resultats)} résultats ; "
          f"erreurs : {erreurs or 'aucune'}")
    # Échec seulement si tout manque : sinon on publie ce qu'on a, erreurs comprises.
    return 0 if (eco or eco_tv) and resultats else 1


if __name__ == "__main__":
    sys.exit(main())
