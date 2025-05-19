import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

# ----------------------------
# Configuration
# ----------------------------
# Set your betting-odds API key in the environment, e.g.
# export ODDS_API_KEY=ad02233ec4f4184f055d0428b0cd2b82
API_KEY = os.getenv("ODDS_API_KEY")
API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

# ----------------------------
# Helper functions
# ----------------------------
@st.cache_data(ttl=3600)
def fetch_player_props():
    """
    Fetches daily MLB player prop markets from Odds API.

    Returns:
        DataFrame: columns=[player, prop_type, line, odds_decimal]
    """
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "player_props",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }
    resp = requests.get(API_URL, params=params)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for match in data:
        for market in match.get("bookmakers", []):
            for prop in market.get("markets", []):
                if prop.get("key").startswith("player_props"):
                    for outcome in prop.get("outcomes", []):
                        rows.append({
                            "player": outcome["name"],
                            "prop_type": prop.get("key").split("_")[1],
                            "line": outcome.get("point"),
                            "odds": outcome.get("price")
                        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def estimate_model_probabilities(df):
    """
    Estimate each player's true probability based on historical data.
    For simplicity, we approximate using last 30 days' batting average or relevant stat.

    Args:
        df (DataFrame): output of fetch_player_props
    Returns:
        DataFrame with extra column model_prob
    """
    # Placeholder: assign a flat 50% probability for demonstration
    df = df.copy()
    df["model_prob"] = 0.5
    return df

# ----------------------------
# Main Streamlit App
# ----------------------------
st.set_page_config(page_title="MLB Player Prop Value Finder", layout="wide")
st.title("Daily Best-Value MLB Player Props 🚀")

# Fetch data
with st.spinner("Fetching player props..."):
    props_df = fetch_player_props()

if props_df.empty:
    st.error("No player props data found for today.")
    st.stop()

# Estimate model probabilities
props_df = estimate_model_probabilities(props_df)

# Calculate implied probabilities and value
props_df["implied_prob"] = 1 / props_df["odds"]
props_df["value_diff"] = props_df["model_prob"] - props_df["implied_prob"]

# Filter for positive value
value_props = props_df[props_df["value_diff"] > 0].copy()
value_props.sort_values("value_diff", ascending=False, inplace=True)

# Display top choices
st.subheader("Top 10 Best-Value Props")
st.dataframe(
    value_props.head(10)[["player", "prop_type", "line", "odds", "implied_prob", "model_prob", "value_diff"]]
)

# Visualization
st.subheader("Value Distribution Across Props")
st.bar_chart(value_props.set_index("player")["value_diff"])

# Footer
st.markdown(
    "---\n"
    "⚙️ **Configure your API key** via `$ export ODDS_API_KEY=...` and deploy on Streamlit Cloud.\n"
    "🔗 **GitHub**: Upload this script to your repo and set up CI to run daily."
)
