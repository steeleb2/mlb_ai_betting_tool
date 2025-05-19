import os
import requests
import pandas as pd
import streamlit as st

API_KEY = "ad02233ec4f4184f055d0428b0cd2b82"  # ← your Odds API key here
API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

@st.cache_data(ttl=86400)  # cache for 24 hours
def fetch_player_props(api_key):
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "playerProps",
        "oddsFormat": "american",
    }
    resp = requests.get(API_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    
    records = []
    for event in data:
        teams = f"{event['home_team']} @ {event['away_team']}"
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] != "playerProps":
                    continue
                for outcome in market["outcomes"]:
                    odds_american = outcome["price"]
                    # convert American odds to decimal
                    if odds_american > 0:
                        dec_odds = odds_american / 100 + 1
                    else:
                        dec_odds = 100 / abs(odds_american) + 1
                    implied_prob = 1 / dec_odds
                    records.append({
                        "event": teams,
                        "bookmaker": bookmaker["key"],
                        "player_prop": outcome["name"],
                        "american_odds": odds_american,
                        "decimal_odds": round(dec_odds, 2),
                        "implied_prob": round(implied_prob, 3),
                    })
    return pd.DataFrame.from_records(records)

st.set_page_config(page_title="MLB Player Props Value", layout="wide")
st.title("⚾ Best-Value MLB Player Props")

df = fetch_player_props(API_KEY)

if df.empty:
    st.warning("No player props data available.")
    st.stop()

# sort by highest decimal odds (biggest payout)
df_sorted = df.sort_values("decimal_odds", ascending=False).reset_index(drop=True)

st.subheader("Top 20 Props by Decimal Odds")
st.dataframe(df_sorted.head(20), height=500)

st.subheader("Odds Comparison")
chart_df = df_sorted.head(10).set_index("player_prop")[["decimal_odds"]]
st.bar_chart(chart_df)

