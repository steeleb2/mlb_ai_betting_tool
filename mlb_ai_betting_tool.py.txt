# MLB AI Betting Tool (Streamlit App)
# This version includes value detection for Moneyline, Spreads, Over/Unders, and Player Props
# Run with: `streamlit run mlb_ai_betting_tool.py`

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import requests

# -------------------------------
# CONFIGURATION
# -------------------------------
ODDS_API_KEY = "YOUR_ODDS_API_KEY"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

# For demo, we use hardcoded data. Replace with live APIs for production
example_games = [
    {
        "teams": ["Yankees", "Red Sox"],
        "home_team": "Yankees",
        "game_time": "2025-05-19T19:05:00Z",
        "moneyline": {"Yankees": -130, "Red Sox": +120},
        "total": 9.0,
        "total_line": 9.0,
        "spread": {"Yankees": -1.5, "Red Sox": +1.5},
        "player_props": [
            {"player": "Aaron Judge", "type": "HR", "line": 0.5, "odds": +250},
            {"player": "Rafael Devers", "type": "HITS", "line": 1.5, "odds": -105}
        ]
    },
    {
        "teams": ["Dodgers", "Giants"],
        "home_team": "Dodgers",
        "game_time": "2025-05-19T21:10:00Z",
        "moneyline": {"Dodgers": -150, "Giants": +135},
        "total": 8.5,
        "total_line": 8.5,
        "spread": {"Dodgers": -1.5, "Giants": +1.5},
        "player_props": [
            {"player": "Mookie Betts", "type": "RUNS", "line": 0.5, "odds": +110},
            {"player": "Logan Webb", "type": "Ks", "line": 6.5, "odds": -110}
        ]
    }
]

# -------------------------------
# VALUE BET LOGIC
# -------------------------------
def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)

# Placeholder AI prediction function
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

for game in example_games:
    st.subheader(f"{game['teams'][0]} vs {game['teams'][1]}")
    st.text(f"Time: {game['game_time']} (Home: {game['home_team']})")

    best_bets = []

    # Moneyline bets
    st.markdown("**Moneyline Value Picks**")
    for team in game["teams"]:
        odds = game["moneyline"][team]
        imp_prob = implied_prob(odds)
        model_prob = model_prediction()
        value = model_prob - imp_prob
        if value > 0.05:
            best_bets.append(("ML", team, odds, round(value * 100, 1)))
            st.write(f"- {team} ML ({odds}) | Edge: +{round(value * 100, 1)}%")

    # Spread
    st.markdown("**Spread Value Picks**")
    for team in game["teams"]:
        odds = -110  # Simulated spread odds
        imp_prob = implied_prob(odds)
        model_prob = model_prediction()
        value = model_prob - imp_prob
        if value > 0.05:
            st.write(f"- {team} {game['spread'][team]} ({odds}) | Edge: +{round(value * 100, 1)}%")

    # Over/Under
    st.markdown("**Over/Under Total**")
    for side in ["Over", "Under"]:
        odds = -110
        imp_prob = implied_prob(odds)
        model_prob = model_prediction()
        value = model_prob - imp_prob
        if value > 0.05:
            st.write(f"- {side} {game['total_line']} ({odds}) | Edge: +{round(value * 100, 1)}%")

    # Player Props
    st.markdown("**Player Prop Value Picks**")
    for prop in game["player_props"]:
        imp_prob = implied_prob(prop["odds"])
        proj = prop_prediction()
        value = proj - imp_prob
        if value > 0.05:
            st.write(f"- {prop['player']} {prop['type']} o{prop['line']} ({prop['odds']}) | Edge: +{round(value * 100, 1)}%")

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
st.metric("Avg ROI per Pick", f"{roi:.2f} units")
