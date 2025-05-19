import os
import requests
import pandas as pd
import streamlit as st

API_KEY = "ad02233ec4f4184f055d0428b0cd2b82"
API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

@st.cache_data(ttl=86400)
def fetch_player_props(api_key):
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "playerProps",  # confirm with your plan; some tiers use "playerprops"
        "oddsFormat": "american",
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        st.error(f"Failed to fetch player props: {resp.status_code}")
        st.write(resp.text)  # full response for debugging in logs
        return pd.DataFrame()
    except Exception as err:
        st.error(f"Unexpected error: {err}")
        return pd.DataFrame()

    data = resp.json()
    records = []
    for event in data:
        teams = f"{event['home_team']} @ {event['away_team']}"
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"].lower() != "playerprops":
                    continue
                for outcome in market["outcomes"]:
                    a_odds = outcome["price"]
                    # convert American odds to decimal
                    if a_odds > 0:
                        dec = a_odds / 100 + 1
                    else:
                        dec = 100 / abs(a_odds) + 1
                    records.append({
                        "event": teams,
                        "bookmaker": bookmaker["key"],
                        "prop": outcome["name"],
                        "american_odds": a_odds,
                        "decimal_odds": round(dec, 2),
                        "implied_prob": round(1/dec, 3),
                    })
    return pd.DataFrame(records)

st.set_page_config(page_title="MLB Player Props Value", layout="wide")
st.title("⚾ Best-Value MLB Player Props")

df = fetch_player_props(API_KEY)
if df.empty:
    st.warning("No data to display—check your API plan or log output.")
    st.stop()

# sort by payout and take top 25
df = df.sort_values("decimal_odds", ascending=False).reset_index(drop=True)
top25 = df.head(25)

st.subheader("Top 25 Props by Decimal Odds")
st.dataframe(top25, height=600)

st.subheader("Top 25 Props Chart")
st.bar_chart(top25.set_index("prop")["decimal_odds"])
