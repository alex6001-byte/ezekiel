#!/usr/bin/env python3
"""
Composite crisis-signal index.

Pulls three free, official-ish data sources, compares each to its own
recent history, and combines them into a single 1-5 "alert level" plus
the raw numbers behind it. Writes everything to data/dashboard.json.

Sources:
  1. SEC EDGAR daily index  -> count of Form 4 (insider transaction) filings per day
  2. Wikipedia pageviews API -> readership of a basket of "panic" articles
  3. Yahoo Finance (yfinance) -> VIX close price

None of these require an API key. All of them can rate-limit or change
shape without warning, so every fetch function fails soft: on error it
returns None for that channel and the dashboard just shows that channel
as "unavailable" instead of crashing the whole run.
"""

import json
import os
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DASHBOARD_PATH = DATA_DIR / "dashboard.json"
HISTORY_DAYS_KEPT = 180          # how much history we keep in the json
BASELINE_WINDOW = 30             # trading/business days used to compute "normal"
SEC_USER_AGENT = "crisis-index research contact@example.com"  # SEC asks for a real contact here


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 1. SEC EDGAR - Form 4 (insider transaction) filing counts
# ---------------------------------------------------------------------------

def _business_days_back(n):
    """Last n weekday dates, most recent first, excluding today (data lags)."""
    days = []
    d = date.today() - timedelta(days=1)
    while len(days) < n:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d -= timedelta(days=1)
    return days


def _sec_form4_count_for_day(d):
    """Count Form 4 filings listed in SEC's daily index for date d."""
    url = f"https://www.sec.gov/Archives/edgar/daily-index/{d.year}/QTR{(d.month - 1) // 3 + 1}/form.{d.strftime('%Y%m%d')}.idx"
    resp = requests.get(url, headers={"User-Agent": SEC_USER_AGENT}, timeout=20)
    if resp.status_code != 200:
        return None
    count = 0
    for line in resp.text.splitlines():
        # Fixed-width index: form type is the first column.
        if line.startswith("4 ") or line.startswith("4\t"):
            count += 1
    return count


def fetch_sec_signal():
    try:
        days = _business_days_back(BASELINE_WINDOW + 1)
        counts = []
        for d in days:
            c = _sec_form4_count_for_day(d)
            if c is not None:
                counts.append((d, c))
            time.sleep(0.3)  # be polite to SEC's servers
        if len(counts) < 5:
            log("SEC: not enough data points, skipping")
            return None
        counts.sort(key=lambda x: x[0])
        latest_date, latest_value = counts[-1]
        baseline_values = [c for _, c in counts[:-1]]
        mean = statistics.mean(baseline_values)
        stdev = statistics.pstdev(baseline_values) or 1.0
        z = (latest_value - mean) / stdev
        return {
            "label": "SEC Form 4 filings (insider transactions)",
            "date": latest_date.isoformat(),
            "value": latest_value,
            "baseline_mean": round(mean, 1),
            "z_score": round(z, 2),
        }
    except Exception as e:
        log(f"SEC fetch failed: {e}")
        return None

# ---------------------------------------------------------------------------
# 2. Wikipedia pageviews - basket of "panic" article readership
# ---------------------------------------------------------------------------

PANIC_WIKI_ARTICLES = ["Bunker", "Gold_as_an_investment", "Potassium_iodide", "Evacuation"]
WIKI_PAGEVIEWS_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
WIKI_HEADERS = {"User-Agent": "ezekiel-signal-station/1.0 (personal project)"}


def _wiki_pageviews(article, start, end):
    url = f"{WIKI_PAGEVIEWS_BASE}/en.wikipedia.org/all-access/user/{article}/daily/{start}/{end}"
    resp = requests.get(url, headers=WIKI_HEADERS, timeout=20)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return {item["timestamp"][:8]: item["views"] for item in items}


def fetch_trends_signal():
    try:
        # Wikimedia pageviews data lags ~1-2 days behind real time, so end
        # the window a couple of days back to make sure data actually exists.
        end_day = date.today() - timedelta(days=2)
        start_day = end_day - timedelta(days=30)
        start_str = start_day.strftime("%Y%m%d")
        end_str = end_day.strftime("%Y%m%d")

        daily_totals = {}
        for article in PANIC_WIKI_ARTICLES:
            views = _wiki_pageviews(article, start_str, end_str)
            for day, count in views.items():
                daily_totals[day] = daily_totals.get(day, 0) + count

        if not daily_totals:
            log("Wiki panic: empty response")
            return None

        days_sorted = sorted(daily_totals.keys())
        series = [daily_totals[d] for d in days_sorted]
        latest_value = float(series[-1])
        baseline_values = series[:-1]
        if len(baseline_values) < 2:
            log("Wiki panic: not enough history for baseline")
            return None
        mean = statistics.mean(baseline_values)
        stdev = statistics.pstdev(baseline_values) or 1.0
        z = (latest_value - mean) / stdev
        d = days_sorted[-1]
        return {
            "label": "Wikipedia pageviews panic-article basket",
            "keywords": PANIC_WIKI_ARTICLES,
            "date": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
            "value": round(latest_value, 1),
            "baseline_mean": round(mean, 1),
            "z_score": round(z, 2),
        }
    except Exception as e:
        log(f"Wiki panic fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 3. VIX (market volatility index)
# ---------------------------------------------------------------------------

def fetch_vix_signal():
    try:
        import yfinance as yf

        hist = yf.Ticker("^VIX").history(period=f"{BASELINE_WINDOW + 10}d")
        if hist.empty:
            log("VIX: empty response")
            return None
        closes = hist["Close"].dropna()
        latest_value = float(closes.iloc[-1])
        baseline_values = closes.iloc[-(BASELINE_WINDOW + 1):-1].tolist()
        mean = statistics.mean(baseline_values)
        stdev = statistics.pstdev(baseline_values) or 1.0
        z = (latest_value - mean) / stdev
        return {
            "label": "VIX (CBOE volatility index)",
            "date": str(closes.index[-1].date()),
            "value": round(latest_value, 2),
            "baseline_mean": round(mean, 2),
            "z_score": round(z, 2),
        }
    except Exception as e:
        log(f"VIX fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 4. E-4B Nightwatch ("doomsday plane") fleet — how many are airborne at once
# ---------------------------------------------------------------------------

# ICAO 24-bit hex addresses for the 4 existing E-4B airframes (public
# aviation-enthusiast knowledge, e.g. ads-b.nl's military registry).
E4B_HEX_CODES = ["ADFEB3", "ADFEB4", "ADFEB5", "ADFEB6"]  # 73-1676 / 73-1677 / 74-0787 / 75-0125

ADSB_API_BASE = "https://api.adsb.lol/v2/hex"  # free, public, ADSBExchange-v2-compatible


def _is_airborne(aircraft):
    alt = aircraft.get("alt_baro")
    return alt is not None and alt != "ground"


def fetch_e4b_signal():
    try:
        airborne_count = 0
        seen_any = False
        for hex_code in E4B_HEX_CODES:
            resp = requests.get(f"{ADSB_API_BASE}/{hex_code}", timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            aircraft_list = data.get("ac") or []
            seen_any = True
            if any(_is_airborne(a) for a in aircraft_list):
                airborne_count += 1
            time.sleep(0.3)  # stay well under the API's rate limit

        if not seen_any:
            log("E-4B: no response from any hex lookup, skipping")
            return None

        # No free historical baseline exists for a 4-aircraft fleet, so this
        # is a hand-set rule rather than a real z-score: 0-1 airborne is
        # routine (there's near-daily training activity), 2+ simultaneously
        # airborne has historically coincided with real-world tension.
        z_equivalent = {0: 0.0, 1: 0.3}.get(airborne_count, 2.0 + (airborne_count - 2) * 1.5)

        return {
            "label": "E-4B Nightwatch fleet airborne",
            "date": datetime.now(timezone.utc).date().isoformat(),
            "value": airborne_count,
            "baseline_mean": "0-1 (typical)",
            "z_score": round(z_equivalent, 2),
        }
    except Exception as e:
        log(f"E-4B fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 5. Polymarket — crowd probability on crisis-adjacent questions
# ---------------------------------------------------------------------------

# Keywords used to find the most relevant *currently open* market for each
# theme. Exact market slugs change every year (new markets get created for
# "2027", "2028", etc.), so searching by keyword and taking the highest-volume
# live match is more durable than hardcoding a slug.
POLYMARKET_KEYWORDS = ["nuclear war", "us recession", "pandemic declared", "nato russia war"]
POLYMARKET_SEARCH_URL = "https://gamma-api.polymarket.com/public-search"
POLYMARKET_HEADERS = {"User-Agent": "signal-station/1.0 (research project)"}


def _best_market_for_keyword(keyword):
    """Return the highest-volume currently-open market matching this search term."""
    resp = requests.get(
        POLYMARKET_SEARCH_URL, params={"q": keyword}, headers=POLYMARKET_HEADERS, timeout=15
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    # The search response nests markets either directly or inside events;
    # check both shapes defensively since this endpoint's exact schema
    # wasn't verifiable from inside this sandbox (no outbound access to
    # polymarket.com here) - confirm this parsing against a real response
    # early and adjust if the shape differs.
    candidates = list(data.get("markets") or [])
    for event in data.get("events") or []:
        candidates.extend(event.get("markets") or [])

    open_candidates = [m for m in candidates if not m.get("closed", False)]
    if not open_candidates:
        return None
    open_candidates.sort(key=lambda m: float(m.get("volume", 0) or 0), reverse=True)
    return open_candidates[0]


def _yes_probability(market):
    try:
        outcomes = json.loads(market["outcomes"])
        prices = json.loads(market["outcomePrices"])
        yes_index = next(i for i, o in enumerate(outcomes) if o.strip().lower() == "yes")
        return float(prices[yes_index])
    except Exception:
        return None


def fetch_polymarket_signal():
    try:
        matches = []
        for keyword in POLYMARKET_KEYWORDS:
            market = _best_market_for_keyword(keyword)
            time.sleep(0.5)
            if market is None:
                continue
            prob = _yes_probability(market)
            if prob is None:
                continue
            matches.append({
                "keyword": keyword,
                "question": market.get("question", keyword),
                "probability": round(prob, 3),
            })

        if not matches:
            log("Polymarket: no matching open markets found, skipping")
            return None

        worst = max(matches, key=lambda m: m["probability"])

        # No free historical odds series without the CLOB/paid history APIs,
        # so - same pattern as the E-4B channel - this is a hand-set rule on
        # the raw probability rather than a z-score against real history.
        # These questions normally price in the low single digits; anything
        # climbing into double digits is itself the signal.
        p = worst["probability"]
        if p >= 0.30:
            z_equivalent = 5.0
        elif p >= 0.15:
            z_equivalent = 3.0
        elif p >= 0.08:
            z_equivalent = 1.5
        elif p >= 0.03:
            z_equivalent = 0.5
        else:
            z_equivalent = 0.0

        return {
            "label": "Polymarket crisis-question odds",
            "date": datetime.now(timezone.utc).date().isoformat(),
            "value": f"{worst['probability'] * 100:.1f}%",
            "baseline_mean": "low single digits (typical)",
            "z_score": z_equivalent,
            "matched_question": worst["question"],
            "all_matches": matches,
        }
    except Exception as e:
        log(f"Polymarket fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 6. Billionaire/oligarch yacht fleet — clustering in known "safe haven" waters
# ---------------------------------------------------------------------------

# Curated watchlist. MMSI verified against Wikipedia + VesselFinder/vesseltracker
# as of mid-2026. Sanctioned owners' yachts re-flag (and get new MMSIs) after
# sanctions events, so re-verify these every few months rather than trusting
# them indefinitely - see _dev/README.md for the per-yacht sourcing notes.
YACHT_WATCHLIST = [
    {"name": "Koru", "owner": "Jeff Bezos", "mmsi": "319225400"},
    {"name": "Musashi", "owner": "Larry Ellison", "mmsi": "319032600"},
    {"name": "Symphony", "owner": "Bernard Arnault", "mmsi": "319076700"},
    {"name": "Venus", "owner": "Laurene Powell Jobs", "mmsi": "319327000"},
    {"name": "Launchpad", "owner": "Mark Zuckerberg", "mmsi": "538072122"},
    {"name": "Ocean Victory", "owner": "Viktor Rashnikov", "mmsi": "319055400"},
    {"name": "Dilbar", "owner": "Alisher Usmanov", "mmsi": "319094900"},
    {"name": "Sailing Yacht A", "owner": "Andrey Melnichenko", "mmsi": "667002036"},
    {"name": "Nord", "owner": "Alexei Mordashov", "mmsi": "273610820"},
    {"name": "Eclipse", "owner": "Roman Abramovich", "mmsi": "518999664"},
    {"name": "Solaris", "owner": "Roman Abramovich", "mmsi": "518999189"},
]

# Rough bounding boxes for waters that have repeatedly shown up, in actual
# reporting (Bloomberg/Fortune/Reuters coverage cited in _dev/README.md), as
# where these fleets go when things get tense: sanctions-indifferent ports
# (UAE, Turkey, Hong Kong, Maldives) for the sanctioned owners, and the
# "billionaire bunker" Pacific (NZ/Fiji) for the Western tech owners. This is
# deliberately generous/approximate - a bounding box, not a precise port list.
SAFE_HAVEN_REGIONS = [
    {"name": "New Zealand / Fiji", "lat": (-46, -12), "lon": (163, -175)},
    {"name": "Maldives", "lat": (-1, 8), "lon": (72, 74)},
    {"name": "UAE / Persian Gulf", "lat": (24, 27), "lon": (51, 57)},
    {"name": "Turkish Aegean coast", "lat": (36, 41), "lon": (26, 30)},
    {"name": "Hong Kong", "lat": (22, 22.6), "lon": (113.8, 114.5)},
]

AISSTREAM_WS_URL = "wss://stream.aisstream.io/v0/stream"
AISSTREAM_LISTEN_SECONDS = 180  # how long to keep the socket open per run


def _in_safe_haven(lat, lon):
    for region in SAFE_HAVEN_REGIONS:
        lat_min, lat_max = region["lat"]
        lon_min, lon_max = region["lon"]
        if lon_min > lon_max:  # region straddles the antimeridian (NZ/Fiji box)
            lon_ok = lon >= lon_min or lon <= lon_max
        else:
            lon_ok = lon_min <= lon <= lon_max
        if lat_min <= lat <= lat_max and lon_ok:
            return region["name"]
    return None


async def _collect_yacht_positions():
    import asyncio
    import json as _json
    import websockets

    api_key = os.environ.get("AISSTREAM_API_KEY")
    if not api_key:
        log("Yachts: no AISSTREAM_API_KEY set, skipping")
        return {}

    positions = {}
    mmsi_list = [y["mmsi"] for y in YACHT_WATCHLIST]

    try:
        async with websockets.connect(AISSTREAM_WS_URL) as ws:
            await ws.send(_json.dumps({
                "APIKey": api_key,
                "BoundingBoxes": [[[-90, -180], [90, 180]]],
                "FiltersShipMMSI": mmsi_list,
            }))
            try:
                async with asyncio.timeout(AISSTREAM_LISTEN_SECONDS):
                    async for raw in ws:
                        msg = _json.loads(raw)
                        if msg.get("MessageType") != "PositionReport":
                            continue
                        report = msg.get("Message", {}).get("PositionReport", {})
                        mmsi = str(report.get("UserID", ""))
                        if mmsi in mmsi_list:
                            positions[mmsi] = (report.get("Latitude"), report.get("Longitude"))
            except TimeoutError:
                pass  # expected - we only listen for a fixed window
    except Exception as e:
        log(f"Yachts: websocket error: {e}")

    return positions


def fetch_yacht_signal():
    import asyncio

    try:
        positions = asyncio.run(_collect_yacht_positions())
        if not positions:
            log("Yachts: no positions received in listen window, skipping")
            return None

        in_haven = []
        for yacht in YACHT_WATCHLIST:
            pos = positions.get(yacht["mmsi"])
            if not pos or pos[0] is None:
                continue
            region = _in_safe_haven(pos[0], pos[1])
            if region:
                in_haven.append({"name": yacht["name"], "region": region})

        haven_count = len(in_haven)
        # Some of these yachts more or less live in these waters normally
        # (a couple of them are frequently in the Aegean or Gulf on any given
        # week), so 0-1 simultaneously is not news. Several at once, together,
        # is the actual signal - same rule-based approach as the E-4B and
        # Polymarket channels, for the same reason: no free historical
        # baseline exists to compute a real z-score against.
        if haven_count >= 4:
            z_equivalent = 4.0
        elif haven_count == 3:
            z_equivalent = 2.5
        elif haven_count == 2:
            z_equivalent = 1.0
        else:
            z_equivalent = 0.0

        return {
            "label": "Tracked yacht fleet in safe-haven waters",
            "date": datetime.now(timezone.utc).date().isoformat(),
            "value": f"{haven_count} of {len(positions)} tracked",
            "baseline_mean": "0-1 (typical)",
            "z_score": z_equivalent,
            "positions_received": len(positions),
            "in_haven": in_haven,
        }
    except Exception as e:
        log(f"Yacht fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Combine into a single alert level
# ---------------------------------------------------------------------------

def combine_signals(signals):
    """signals: dict of name -> signal dict-or-None. Returns (level, avg_z)."""
    z_scores = [s["z_score"] for s in signals.values() if s is not None]
    if not z_scores:
        return 1, 0.0
    avg_z = sum(z_scores) / len(z_scores)
    # Thresholds are deliberately conservative: real markets/news are noisy.
    if avg_z >= 3.0:
        level = 5
    elif avg_z >= 2.0:
        level = 4
    elif avg_z >= 1.25:
        level = 3
    elif avg_z >= 0.75:
        level = 2
    else:
        level = 1
    return level, round(avg_z, 2)


def load_existing_history():
    if DASHBOARD_PATH.exists():
        try:
            existing = json.loads(DASHBOARD_PATH.read_text())
            return existing.get("history", [])
        except Exception:
            return []
    return []


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    signals = {
        "sec_insider_filings": fetch_sec_signal(),
        "google_trends": fetch_trends_signal(),
        "vix": fetch_vix_signal(),
        "e4b_command_post": fetch_e4b_signal(),
        "polymarket_odds": fetch_polymarket_signal(),
        "yacht_fleet": fetch_yacht_signal(),
    }

    level, avg_z = combine_signals(signals)
    now = datetime.now(timezone.utc).isoformat()

    history = load_existing_history()
    history.append({"timestamp": now, "level": level, "avg_z_score": avg_z})
    history = history[-HISTORY_DAYS_KEPT:]

    dashboard = {
        "generated_at": now,
        "level": level,
        "avg_z_score": avg_z,
        "signals": signals,
        "history": history,
    }

    DASHBOARD_PATH.write_text(json.dumps(dashboard, indent=2))
    log(f"Wrote {DASHBOARD_PATH} — level {level} (avg z={avg_z})")


if __name__ == "__main__":
    main()
