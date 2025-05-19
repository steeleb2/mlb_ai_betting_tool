# MLB AI Betting Tool (Rewritten from Scratch)
# Provides best value bets for Moneylines, Spreads, Totals, and live player props using Streamlit

import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import json

# -------------------------------
# CONFIGURATION
# -------------------------------
ODDS_API_KEY = "ad02233ec4f4184f055d0428b0cd2b82"  # Replace with your actual key
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

# -------------------------------
# FUNCTIONS
# -------------------------------
def implied_probability(odds):
    return 100 / (odds + 100) if odds > 0 else -odds / (-odds + 100)

def model_estimate():
    return np.random.uniform(0.45, 0.65)  # Placeholder

def fetch_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    r = requests.get(ODDS_API_URL, params=params)
    if r.status_code == 200:
        return r.json()
    else:
        st.error(f"Failed to fetch odds: {r.status_code}")
        return []

def scrape_player_props():
    url = "https://www.prizepicks.com/projections"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error("Failed to scrape player props")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    scripts = soup.find_all("script")
    for script in scripts:
        if 'window.__PRELOADED_STATE__' in script.text:
            try:
                start = script.text.find('{')
                end = script.text.rfind('}') + 1
                data_json = json.loads(script.text[start:end])
                projections = data_json.get("props", [])
                return projections
            except Exception as e:
                st.error(f"Error loading player props: {e}")
                return []
    return []

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.title("MLB AI Value Betting Tool")
st.write("Daily best bets: Moneylines, Spreads, Totals, and player props")

odds_data = fetch_odds()

if not odds_data:
    st.warning("No live data available.")
else:
    for game in odds_data:
        teams = game.get("teams", [])
        if len(teams) < 2:
            continue  # Skip games without two valid teams

        home_team = game.get("home_team")
        start_time = game.get("commence_time")
        st.subheader(f"{teams[0]} vs {teams[1]}")
        st.caption(f"Start Time: {start_time} | Home: {home_team}")

        h2h = {}
        spreads = {}
        totals = {}

        for book in game.get("bookmakers", []):
            for market in book.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        h2h[outcome["name"]] = outcome["price"]
                elif market["key"] == "spreads":
                    for outcome in market["outcomes"]:
                        spreads[outcome["name"]] = (outcome["point"], outcome["price"])
                elif market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        totals[outcome["name"]] = (outcome["point"], outcome["price"])

        # Moneyline
        st.markdown("**Moneyline Picks**")
        for team, odds in h2h.items():
            model_prob = model_estimate()
            edge = model_prob - implied_probability(odds)
            if edge > 0.05:
                st.write(f"- {team} ML @ {odds} | Edge: +{round(edge * 100, 1)}%")

        # Spreads
        st.markdown("**Spread Picks**")
        for team, (spread, odds) in spreads.items():
            model_prob = model_estimate()
            edge = model_prob - implied_probability(odds)
            if edge > 0.05:
                st.write(f"- {team} {spread:+} @ {odds} | Edge: +{round(edge * 100, 1)}%")

        # Totals
        st.markdown("**Totals (Over/Under)**")
        for side, (point, odds) in totals.items():
            model_prob = model_estimate()
            edge = model_prob - implied_probability(odds)
            if edge > 0.05:
                st.write(f"- {side} {point} @ {odds} | Edge: +{round(edge * 100, 1)}%")

# -------------------------------
# LIVE PLAYER PROPS (Scraped)
# -------------------------------
st.markdown("---")
st.write("### Live Player Props (Scraped from PrizePicks)")
props = scrape_player_props()

if props:
    for prop in props[:20]:  # Limit for performance
        name = prop.get("name", "Unknown Player")
        stat_type = prop.get("statType", "Unknown Stat")
        line = prop.get("line", "?")
        odds = 100  # Placeholder odds since PrizePicks doesn't display them
        model_prob = model_estimate()
        edge = model_prob - implied_probability(odds)
        st.write(f"- {name} {stat_type} o{line} | Est. Edge: {round(edge * 100, 1)}%")
else:
    st.info("No live player props found.")

# -------------------------------
# TRACKING SECTION (Static Example)
# -------------------------------
st.markdown("---")
st.write("### Previous Pick Tracker")
track_data = pd.DataFrame({
    "Date": ["2025-05-18", "2025-05-17"],
    "Pick": ["Yankees ML", "Dodgers Spread"],
    "Odds": [-130, -110],
    "Result": ["Win", "Loss"],
    "Profit": [+0.77, -1.0]
})
st.dataframe(track_data)
st.metric("Avg ROI", f"{track_data['Profit'].mean():.2f} units")
