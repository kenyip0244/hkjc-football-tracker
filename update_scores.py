#!/usr/bin/env python3
"""
HKJC & Global Football Match Auto-Updater
Continuously fetches real completed matches, filters half-time & full-time scores,
and maintains a rolling 56-day database saved to data/matches.json.
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Target directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "matches.json")
SUMMARY_FILE = os.path.join(DATA_DIR, "summary.json")

HK_TZ = timezone(timedelta(hours=8))
API_KEY = os.environ.get("RAPIDAPI_KEY") or os.environ.get("APISPORTS_KEY") or ""

# Chinese League Name Translations
LEAGUE_NAME_MAP = {
    "Premier League": "英格蘭超級聯賽",
    "Championship": "英格蘭冠軍聯賽",
    "FA Cup": "英格蘭足總盃",
    "League Cup": "英格蘭聯賽盃",
    "La Liga": "西班牙甲組聯賽",
    "Copa del Rey": "西班牙盃",
    "Serie A": "意大利甲組聯賽",
    "Coppa Italia": "意大利盃",
    "Bundesliga": "德國甲組聯賽",
    "2. Bundesliga": "德國乙組聯賽",
    "DFB Pokal": "德國盃",
    "Ligue 1": "法國甲組聯賽",
    "Ligue 2": "法國乙組聯賽",
    "Coupe de France": "法國盃",
    "UEFA Champions League": "歐洲聯賽冠軍盃",
    "UEFA Europa League": "歐霸盃",
    "UEFA Europa Conference League": "歐洲協會聯賽",
    "UEFA Nations League": "歐洲國家聯賽",
    "Allsvenskan": "瑞典超級聯賽",
    "Saudi Pro League": "沙特超級聯賽",
    "Stars League": "卡塔爾星級聯賽",
    "Major League Soccer": "美國職業聯賽",
    "J1 League": "日本職業聯賽",
    "J2 League": "日本乙組聯賽",
    "K League 1": "南韓職業聯賽",
    "Primera Division": "烏拉圭甲組聯賽",
    "Jupiler Pro League": "比利時甲組聯賽",
    "Eredivisie": "荷蘭甲組聯賽",
    "Primeira Liga": "葡萄牙超級聯賽",
    "Copa Libertadores": "南美自由盃",
    "Copa Sudamericana": "南美球會盃",
    "Serie A Brazil": "巴西甲組聯賽",
    "Copa America": "美洲國家盃",
    "Euro Championship": "歐洲國家盃"
}

def load_existing_data():
    """Load previously cached matches from data/matches.json to maintain 56-day history."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"Note: Could not parse existing data file ({e}), starting fresh.")
    return []

def fetch_from_api(date_str):
    """Fetch completed match fixtures for a specific date from API-Football."""
    if not API_KEY:
        return []

    endpoints = [
        {
            "url": f"https://v3.football.api-sports.io/fixtures?date={date_str}",
            "headers": {
                "x-apisports-key": API_KEY,
                "User-Agent": "HKJC-Football-Tracker/2.0"
            }
        },
        {
            "url": f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={date_str}",
            "headers": {
                "x-rapidapi-key": API_KEY,
                "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
                "User-Agent": "HKJC-Football-Tracker/2.0"
            }
        }
    ]

    for ep in endpoints:
        try:
            req = urllib.request.Request(ep["url"], headers=ep["headers"])
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                fixtures = res_data.get("response", [])
                if fixtures:
                    print(f"[{date_str}] Successfully fetched {len(fixtures)} matches from online API.")
                    results = []
                    for item in fixtures:
                        status = item.get("fixture", {}).get("status", {}).get("short", "")
                        if status not in ["FT", "AET", "PEN"]:
                            continue

                        league_name = item.get("league", {}).get("name", "足球賽事")
                        league_cn = LEAGUE_NAME_MAP.get(league_name, league_name)

                        home_team = item.get("teams", {}).get("home", {}).get("name", "主隊")
                        away_team = item.get("teams", {}).get("away", {}).get("name", "客隊")

                        score_obj = item.get("score", {})
                        ht = score_obj.get("halftime", {})
                        ft = score_obj.get("fulltime", {})

                        ht_h, ht_a = ht.get("home"), ht.get("away")
                        ft_h, ft_a = ft.get("home"), ft.get("away")

                        if None in (ht_h, ht_a, ft_h, ft_a):
                            continue

                        utc_str = item.get("fixture", {}).get("date", "")
                        try:
                            utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
                            hk_dt = utc_dt.astimezone(HK_TZ)
                            d_text = hk_dt.strftime("%d/%m/%Y")
                            d_iso = hk_dt.strftime("%Y-%m-%d")
                            hkt_str = hk_dt.strftime("%Y-%m-%d %H:%M") + " (UTC+8)"
                        except Exception:
                            d_text = date_str
                            d_iso = date_str
                            hkt_str = date_str

                        venue_name = item.get("fixture", {}).get("venue", {}).get("name") or "官方指定體育場"
                        venue_city = item.get("fixture", {}).get("venue", {}).get("city") or ""
                        f_id = str(item.get("fixture", {}).get("id", f"{home_team}_{away_team}_{d_iso}"))

                        results.append({
                            "code": f"FB{f_id[-4:]}",
                            "id": f_id,
                            "dateText": d_text,
                            "dateISO": d_iso,
                            "hktTime": hkt_str,
                            "league": league_cn,
                            "home": home_team,
                            "away": away_team,
                            "ftScore": f"{ft_h}:{ft_a}",
                            "htScore": f"{ht_h}:{ht_a}",
                            "venue": venue_name,
                            "city": venue_city
                        })
                    return results
        except Exception as e:
            print(f"API query for {date_str} failed ({e}), trying next endpoint...")
            continue

    return []

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    existing_data = load_existing_data()
    now_hk = datetime.now(HK_TZ)

    print(f"=== HKJC Football Match Auto-Updater Started at {now_hk.strftime('%Y-%m-%d %H:%M:%S HKT')} ===")

    # Look back past 4 days to catch all finished fixtures
    dates_to_scan = [(now_hk - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(4)]
    
    fetched_matches = []
    if API_KEY:
        for d in dates_to_scan:
            fetched_matches.extend(fetch_from_api(d))
    else:
        print("Note: No RAPIDAPI_KEY or APISPORTS_KEY found in environment.")
        print("Existing cached 56-day database will be preserved.")

    # Deduplicate and merge
    match_map = {}
    for m in existing_data:
        key = m.get("id") or m.get("code") or f"{m.get('home')}_{m.get('away')}_{m.get('dateISO')}"
        match_map[key] = m

    for m in fetched_matches:
        key = m.get("id") or m.get("code") or f"{m.get('home')}_{m.get('away')}_{m.get('dateISO')}"
        match_map[key] = m

    # Filter rolling 56 days
    cutoff_iso = (now_hk - timedelta(days=56)).strftime("%Y-%m-%d")
    all_matches = [m for m in match_map.values() if m.get("dateISO", "") >= cutoff_iso]
    all_matches.sort(key=lambda x: x.get("dateISO", ""), reverse=True)

    # Save to data/matches.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_matches, f, ensure_ascii=False, indent=2)

    # Calculate summary
    matched_ht = [m for m in all_matches if m.get("htScore", "").replace(" ", "") in ["1:0", "2:0", "0:1", "0:2"]]
    summary = {
        "lastUpdated": now_hk.strftime("%Y-%m-%d %H:%M:%S HKT"),
        "totalRecords": len(all_matches),
        "targetHTMatchesCount": len(matched_ht),
        "status": "success"
    }

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Auto-update complete!")
    print(f"Total Matches: {len(all_matches)} | Target HT Matches (1:0, 2:0, 0:1, 0:2): {len(matched_ht)}")
    print(f"Saved to {DATA_FILE}")

if __name__ == "__main__":
    main()
