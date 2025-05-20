import os
import requests
import pandas as pd
import streamlit as st

# ── CONFIG ──────────────────────────────────────────────────────────────────────
API_KEY           = "ad02233ec4f4184f055d0428b0cd2b82"
SPORT_KEY         = "baseball_mlb"
REGIONS           = "us"
ODDS_FORMAT       = "american"
EVENTS_URL        = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/events"
EVENT_ODDS_URL    = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/events/{{}}/odds"

# all supported MLB player-props market keys :contentReference[oaicite:0]{index=0}
MLB_PROPS_MARKETS = [
    "batter_home_runs",
    "batter_first_home_run",
    "batter_hits",
    "batter_total_bases",
    "batter_rbis",
    "batter_runs_scored",
    "batter_hits_runs_rbis",
    "batter_singles",
    "batter_doubles",
    "batter_triples",
    "batter_walks",
    "batter_strikeouts",
    "batter_stolen_bases",
    "pitcher_strikeouts",
    "pitcher_record_a_win",
    "pitcher_hits_allowed",
    "pitcher_walks",
    "pitcher_earned_runs",
    "pitcher_outs",
]
MARKETS_PARAM = ",".join(MLB_PROPS_MARKETS)

# ── DATA FETCHING ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_player_props(api_key: str) -> pd.DataFrame:
    # 1) get list of today's events
    try:
        ev = requests.get(EVENTS_URL, params={"apiKey": api_key}, timeout=10)
        ev.raise_for_status()
        events = ev.json()
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()

    records = []
    # 2) for each event, pull ONLY the player-props markets via the event-odds endpoint
    for event in events:
        eid   = event["id"]
        teams = f"{event['away_team']} @ {event['home_team']}"
        try:
            eo = requests.get(
                EVENT_ODDS_URL.format(eid),
                params={
                    "apiKey": api_key,
                    "regions": REGIONS,
                    "markets": MARKETS_PARAM,
                    "oddsFormat": ODDS_FORMAT,
                },
                timeout=10
            )
            eo.raise_for_status()
        except requests.exceptions.HTTPError:
            # no props for this game or invalid market → skip :contentReference[oaicite:1]{index=1}
            continue
        except Exception:
            continue

        data = eo.json()
        for bm in data.get("bookmakers", []):
            for mkt in bm.get("markets", []):
                if mkt["key"] not in MLB_PROPS_MARKETS:
                    continue
                for outcome in mkt.get("outcomes", []):
                    ao = outcome["price"]
                    # American → decimal → implied prob
                    dec = (ao / 100 + 1) if ao > 0 else (100 / abs(ao) + 1)
                    ip  = 1 / dec if dec else None
                    records.append({
                        "event": teams,
                        "bookmaker": bm["key"],
                        "market":   mkt["key"],
                        "prop":     outcome["name"],
                        "american_odds": ao,
                        "decimal_odds":  round(dec, 2),
                        "implied_prob":  round(ip, 3) if ip else None,
                    })

    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records)

# ── STREAMLIT UI ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="MLB Player-Props Value", layout="wide")
st.title("⚾ Best-Value MLB Player Props (Top 25)")

with st.spinner("Fetching MLB player props…"):
    df = fetch_player_props(API_KEY)

if df.empty:
    st.warning("No player props available. Check your API plan & logs.")
    st.stop()

# 3) sort by highest decimal odds and take top 25
df = df.sort_values("decimal_odds", ascending=False).reset_index(drop=True)
top25 = df.head(25)

st.subheader("Top 25 Props by Decimal Odds")
st.dataframe(top25, height=600)

st.subheader("Top 25 Props Chart")
st.bar_chart(top25.set_index("prop")["decimal_odds"])
