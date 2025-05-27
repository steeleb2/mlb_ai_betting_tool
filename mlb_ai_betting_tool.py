import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# --- 1. Functions to Get Data ---

def get_daily_lineups():
    # Replace with real logic or API
    return pd.DataFrame({
        'Player': ['Aaron Judge', 'Ronald Acuna Jr.', 'Shohei Ohtani'],
        'Team': ['Yankees', 'Braves', 'Dodgers'],
        'Batting Order': [2, 1, 3],
        'Position': ['RF', 'CF', 'DH']
    })

def get_daily_weather():
    # Replace with real logic or API
    return pd.DataFrame({
        'Ballpark': ['Yankee Stadium', 'Truist Park', 'Dodger Stadium'],
        'Temperature (F)': [78, 85, 75],
        'Wind': ['8 mph Out', '5 mph In', '2 mph L to R'],
        'Conditions': ['Sunny', 'Cloudy', 'Clear']
    })

def get_daily_matchups():
    # Replace with real logic or API
    return pd.DataFrame({
        'Home': ['Yankees', 'Braves', 'Dodgers'],
        'Away': ['Red Sox', 'Phillies', 'Padres'],
        'Home SP': ['Gerrit Cole', 'Max Fried', 'Tyler Glasnow'],
        'Away SP': ['Chris Sale', 'Zack Wheeler', 'Yu Darvish']
    })

def get_historic_data():
    # Replace with real logic or file/database
    return pd.DataFrame({
        'Player': ['Aaron Judge', 'Ronald Acuna Jr.', 'Shohei Ohtani'],
        'HR %': [0.07, 0.05, 0.06],
        'TB %': [0.45, 0.38, 0.41],
        'Hits %': [0.28, 0.30, 0.27]
    })

# --- 2. Your Model Logic Here ---

def run_mlb_betr_model(lineups, weather, matchups, historic_data):
    # Merge lineups with historic data
    merged = pd.merge(lineups, historic_data, on='Player', how='left')

    # Example "Win %" calculation (customize with your formula as needed)
    merged['Win %'] = (merged['HR %'] + merged['TB %'] + merged['Hits %']) / 3 + 0.5  # Demo logic

    # Sort and assign type labels for output
    merged = merged.sort_values('Win %', ascending=False).reset_index(drop=True)
    merged['Type'] = ""
    merged.loc[merged.index < 15, 'Type'] = "Best Play"
    merged.loc[(merged.index >= 15) & (merged.index < 25), 'Type'] = "Longshot"
    merged.loc[merged.index >= 25, 'Type'] = "Other"

    # Pad with fake players for demo if not enough rows
    while len(merged) < 25:
        merged.loc[len(merged)] = [
            f"Player {len(merged)+1}", "TeamX", (len(merged)%9)+1, "OF",
            0.03, 0.27, 0.19, 0.51-(len(merged)*0.01), "Longshot"
        ]

    # Keep only relevant columns
    merged = merged[['Player', 'Team', 'Batting Order', 'Position', 'Win %', 'Type']]

    return merged

# --- 3. Streamlit App UI ---

st.title("MLB Betr: Daily Model Output")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("Loading data..."):
    lineups = get_daily_lineups()
    weather = get_daily_weather()
    matchups = get_daily_matchups()
    historic_data = get_historic_data()
    output_df = run_mlb_betr_model(lineups, weather, matchups, historic_data)

st.subheader("Today's Weather by Ballpark")
st.dataframe(weather)

st.subheader("Today's Pitching Matchups")
st.dataframe(matchups)

st.header("Top 15 Best Plays (by Win %)")
best_plays = output_df[output_df['Type'] == 'Best Play'].head(15)
st.dataframe(best_plays)

st.header("Top 10 Longshot/Variance Plays (by Win %)")
longshots = output_df[output_df['Type'] == 'Longshot'].head(10)
st.dataframe(longshots)

# Download all results as CSV
st.download_button(
    label="Download All Results as CSV",
    data=output_df.to_csv(index=False),
    file_name='mlb_betr_model_output.csv',
    mime='text/csv'
)

with st.expander("Show all players evaluated"):
    st.dataframe(output_df)

st.info("Customize data sources and model logic by editing this script.")

