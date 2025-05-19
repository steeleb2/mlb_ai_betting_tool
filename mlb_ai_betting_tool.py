# MLB AI Betting Tool (Streamlit App)
# Includes live odds integration for Moneyline, Spreads, Over/Unders, and scraped Player Props
# Run with: `streamlit run mlb_ai_betting_tool.py`

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import requests
from bs4 import BeautifulSoup
import json

# -------------------------------
# CONFIGURATION
# -------------------------------
ODDS_API_KEY = "ad02233ec4f4184f055d0428b0cd2b82"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

# -------------------------------
# FETCH LIVE ODDS
# -------------------------------
def fetch_live_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    response = requests.get(ODDS_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch odds: {response.status_code}")
        return []

# -------------------------------
# SCRAPE PLAYER PROPS (PRIZEPICKS STYLE)
# -------------------------------
def scrape_player_props():
    url = "https://www.prizepicks.com/projections"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error("Failed to scrape player props")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    script_tags = soup.find_all("script")

    for script in script_tags:
        if 'window.__PRELOADED_STATE__' in script.text:
            try:
                start = script.text.find('{')
                end = script.text.rfind('}') + 1
                json_str = script.text[start:end]
                data = json.loads(json_str)
                props = data.get("props", [])
                return props
            except Exception as e:
                st.error(f"Error parsing player props: {e}")
                return []
    return []

# -------------------------------
# VALUE BET LOGIC
# -------------------------------
def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)

# Placeholder AI prediction functions
np.random.seed(42)
def model_prediction():
    return np.random.uniform(0.45, 0.65)

def prop_prediction():
    return np.random.uniform(0.48, 0.68)

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.title("MLB AI Betting Value Tool")
st.write("### Powered by AI — Updated Daily")

live_data = fetch_live_odds()
prop_data = scrape_player_props()

if not live_data:
    st.warning("No live data found. Showing placeholder games.")
    live_data = []

# Collect best value bets
value_bets = []

for game in live_data:
    teams = game.get("teams", [])
    home_team = game.get("home_team", "")
    commence_time = game.get("commence_time", "")
    bookmakers = game.get("bookmakers", [])

    if not teams or not bookmakers:
        continue

    st.subheader(f"{teams[0]} vs {teams[1]}")
    st.text(f"Time: {commence_time} (Home: {home_team})")

    h2h_odds = {}
    spreads = {}
    totals = {}

    for bm in bookmakers:
        for market in bm["markets"]:
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    h2h_odds[outcome["name"]] = outcome["price"]
            elif market["key"] == "spreads":
                for outcome in market["outcomes"]:
                    spreads[outcome["name"]] = (outcome["point"], outcome["price"])
            elif market["key"] == "totals":
                for outcome in market["outcomes"]:
                    totals[outcome["name"]] = (outcome["point"], outcome["price"])

    # Moneyline
    st.markdown("**Moneyline Value Picks**")
    for team in teams:
        if team in h2h_odds:
            odds = h2h_odds[team]
            imp_prob = implied_prob(odds)
            model_prob = model_prediction()
            value = model_prob - imp_prob
            if value > 0.05:
                value_bets.append((f"{team} ML", odds, value))
                st.write(f"- {team} ML ({odds}) | Edge: +{round(value * 100, 1)}%")

    # Spreads
    st.markdown("**Spread Value Picks**")
    for team in teams:
        if team in spreads:
            spread_point, odds = spreads[team]
            imp_prob = implied_prob(odds)
            model_prob = model_prediction()
            value = model_prob - imp_prob
            if value > 0.05:
                value_bets.append((f"{team} {spread_point:+}", odds, value))
                st.write(f"- {team} {spread_point:+} ({odds}) | Edge: +{round(value * 100, 1)}%")

    # Totals
    st.markdown("**Over/Under Total**")
    for side, (point, odds) in totals.items():
        imp_prob = implied_prob(odds)
        model_prob = model_prediction()
        value = model_prob - imp_prob
        if value > 0.05:
            st.write(f"- {side} {point} ({odds}) | Edge: +{round(value * 100, 1)}%")

# Player Props
st.markdown("---")
st.write("### Scraped Player Prop Value Picks (Demo)")
if not prop_data:
    st.info("No player prop data available.")
else:
    for prop in prop_data[:25]:  # Show first 25 props for demo
        name = prop.get("name")
        stat = prop.get("statType")
        line = prop.get("line")
        odds = 100  # Placeholder until real implied odds known
        imp_prob = implied_prob(odds)
        model_prob = prop_prediction()
        edge = model_prob - imp_prob
        if edge > 0.05:
            value_bets.append((f"{name} {stat} o{line}", odds, edge))
            st.write(f"- {name} {stat} o{line} (Est. Edge: +{round(edge * 100, 1)}%)")

# -------------------------------
# TRACKING
# -------------------------------
st.write("---")
st.write("### Previous Results Tracker (Demo)")
track_data = pd.DataFrame({
    "Date": ["2025-05-18", "2025-05-17"],
    "Pick": ["Yankees ML", "Dodgers ML"],
    "Odds": [-130, -150],
    "Result": ["Win", "Loss"],
    "Profit": [+0.77, -1.0]
})
st.dataframe(track_data)

roi = track_data["Profit"].sum() / len(track_data)
roi_by_type = track_data.groupby("Result")["Profit"].mean().reset_index()
st.metric("Avg ROI per Pick", f"{roi:.2f} units")
st.write("#### ROI by Result")
st.dataframe(roi_by_type)

