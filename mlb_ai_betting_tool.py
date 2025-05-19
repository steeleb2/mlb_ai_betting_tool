# MLB AI Betting Tool (Rewritten from Scratch)
# Provides best value bets for Moneylines, Spreads, Totals, and live player props using Streamlit

import streamlit as st
import pandas as pd
import numpy as np
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------
# CONFIGURATION
# -------------------------------
ODDS_API_KEY = "ad02233ec4f4184f055d0428b0cd2b82"  # Replace with your actual key
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
UNDERDOG_API_URL = "https://api.underdogfantasy.com/beta/over_under_lines"

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("MLB AI Bets").sheet1

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

def fetch_underdog_props():
    r = requests.get(UNDERDOG_API_URL)
    if r.status_code != 200:
        st.error("Failed to fetch player props from Underdog")
        return []
    data = r.json()
    props = []
    for entry in data.get("over_under_lines", []):
        player = entry.get("over_under", {}).get("user", {}).get("username", "Unknown")
        stat = entry.get("over_under", {}).get("stat_type", "")
        line = entry.get("line", None)
        if player and stat and line is not None:
            props.append({"player": player, "stat": stat, "line": line})
    return props

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.title("MLB AI Value Betting Tool")
st.write("Daily best bets: Moneylines, Spreads, Totals, and player props")

odds_data = fetch_odds()
export_rows = []

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
                export_rows.append([team, "Moneyline", odds, round(edge * 100, 1)])

        # Spreads
        st.markdown("**Spread Picks**")
        for team, (spread, odds) in spreads.items():
            model_prob = model_estimate()
            edge = model_prob - implied_probability(odds)
            if edge > 0.05:
                st.write(f"- {team} {spread:+} @ {odds} | Edge: +{round(edge * 100, 1)}%")
                export_rows.append([team, f"Spread {spread:+}", odds, round(edge * 100, 1)])

        # Totals
        st.markdown("**Totals (Over/Under)**")
        for side, (point, odds) in totals.items():
            model_prob = model_estimate()
            edge = model_prob - implied_probability(odds)
            if edge > 0.05:
                st.write(f"- {side} {point} @ {odds} | Edge: +{round(edge * 100, 1)}%")
                export_rows.append([side, f"Total {point}", odds, round(edge * 100, 1)])

# -------------------------------
# UNDERDOG FANTASY PLAYER PROPS
# -------------------------------
st.markdown("---")
st.write("### Player Props (Live from Underdog Fantasy)")
underdog_props = fetch_underdog_props()

if underdog_props:
    for prop in underdog_props[:20]:
        model_prob = model_estimate()
        imp_prob = 0.5  # Assuming even implied prob
        edge = model_prob - imp_prob
        st.write(f"- {prop['player']} {prop['stat']} o{prop['line']} | Est. Edge: {round(edge * 100, 1)}%")
else:
    st.info("No props found from Underdog.")

# -------------------------------
# EXPORT TO GOOGLE SHEETS
# -------------------------------
if export_rows:
    sheet.clear()
    sheet.append_row(["Player/Team", "Bet Type", "Odds", "Edge %"])
    for row in export_rows:
        sheet.append_row(row)
    st.success("Best bets exported to Google Sheets!")

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

