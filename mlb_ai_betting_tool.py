import os
import requests
import pandas as pd
import streamlit as st

# ── CONFIG ──────────────────────────────────────────────────────────────────────
API_KEY        = "ad02233ec4f4184f055d0428b0cd2b82"
SPORT_KEY      = "baseball_mlb"
REGIONS        = "us"
ODDS_FORMAT    = "american"
EVENTS_URL     = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/events"
EVENT_ODDS_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/events/{{}}/odds"

# all supported MLB player‐props market keys
MLB_PROPS_MARKETS = [
    "batter_home_runs", "batter_first_home_run", "batter_hits",
    "batter_total_bases", "batter_rbis", "batter_runs_scored",
    "batter_hits_runs_rbis", "batter_singles", "batter_doubles",
    "batter_triples", "batter_walks", "batter_strikeouts",
    "batter_stolen_bases", "pitcher_strikeouts", "pitcher_record_a_win",
    "pitcher_hits_allowed", "pitcher_walks", "pitcher_earned_runs",
    "pitcher_outs",
]
MARKETS_PARAM = ",".join(MLB_PROPS_MARKETS)

# ── DATA FETCHING ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_player_props(api_key: str) -> pd.DataFrame:
    # 1) get today's MLB events
    try:
        ev = requests.get(EVENTS_URL, params={"apiKey": api_key}, timeout=10)
        ev.raise_for_status()
        events = ev.json()
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()

    records = []
    # 2) for each event, get only the prop‐markets
    for event in events:
        eid   = event["id"]
        teams = f"{event['away_team']} @ {event['home_team']}"
        try:
            eo = requests.get(
                EVENT_ODDS_URL.format(eid),
                params={
                    "apiKey":     api_key,
                    "regions":    REGIONS,
                    "markets":    MARKETS_PARAM,
                    "oddsFormat": ODDS_FORMAT,
                },
                timeout=10,
            )
            eo.raise_for_status()
        except Exception:
            continue

        data = eo.json()
        for bm in data.get("bookmakers", []):
            for mkt in bm.get("markets", []):
                if mkt["key"] not in MLB_PROPS_MARKETS:
                    continue
                for outcome in mkt.get("outcomes", []):
                    name = outcome["name"]  # e.g. "Juan Soto Over 1.5"
                    # parse out the player name and the rest of the prop description
                    if " Over " in name:
                        player, rest = name.split(" Over ", 1)
                        desc = f"Over {rest}"
                    elif " Under " in name:
                        player, rest = name.split(" Under ", 1)
                        desc = f"Under {rest}"
                    else:
                        # fallback to the 'participant' field if it exists
                        player = outcome.get("participant", "Unknown Player")
                        desc   = name

                    ao = outcome["price"]
                    # convert American → decimal
                    dec = (ao / 100 + 1) if ao > 0 else (100 / abs(ao) + 1)
                    ip  = (1 / dec) if dec else None

                    records.append({
                        "event":         teams,
                        "player":        player,
                        "prop_desc":     desc,
                        "american_odds": ao,
                        "decimal_odds":  round(dec, 2),
                        "implied_prob":  round(ip, 3) if ip else None,
                    })

    return pd.DataFrame.from_records(records) if records else pd.DataFrame()

# ── STREAMLIT UI ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="MLB Player-Props Value", layout="wide")
st.title("⚾ Best-Value MLB Player Props (Top 25 by Implied Probability)")

with st.spinner("Fetching MLB player props…"):
    df = fetch_player_props(API_KEY)

if df.empty:
    st.warning("No player props available. Check your API plan & logs.")
    st.stop()

# 3) sort by implied probability descending = highest chance
df = df.sort_values("implied_prob", ascending=False).reset_index(drop=True)
top25 = df.head(25)

st.subheader("Top 25 Props by Implied Probability")
st.dataframe(
    top25[["player", "prop_desc", "american_odds", "decimal_odds", "implied_prob"]],
    height=600
)

st.subheader("Implied Probability Chart (Top 25)")
st.bar_chart(top25.set_index("player")["implied_prob"])
