import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# --- 1. Pull today's MLB schedule with lineups/probables ---

today = datetime.now().strftime('%Y-%m-%d')
mlb_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&expand=schedule.lineups,schedule.probablePitchers"

resp = requests.get(mlb_url)
data = resp.json()

games = data.get('dates', [])[0].get('games', []) if data.get('dates') else []

def extract_lineup(lineup_data):
    if not lineup_data:
        return []
    try:
        batting_order = sorted(
            [p for p in lineup_data['bats']],
            key=lambda x: x['battingOrder']
        )
        return [
            {
                "Spot": p['battingOrder'],
                "Player": p['fullName'],
                "Position": p['position']['abbreviation']
            }
            for p in batting_order
        ]
    except Exception as e:
        return []

# --- 2. Parse and display games, starters, lineups ---

games_table = []
full_lineups = []

for game in games:
    game_info = {
        "Game": f"{game['teams']['away']['team']['name']} @ {game['teams']['home']['team']['name']}",
        "Start Time (ET)": pd.to_datetime(game['gameDate']).tz_convert('US/Eastern').strftime('%I:%M %p'),
        "Home Starter": game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD'),
        "Away Starter": game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
    }
    games_table.append(game_info)

    # Away lineup
    away_lineup = game.get('lineups', {}).get('away', {})
    if away_lineup and 'bats' in away_lineup:
        full_lineups.append({
            "Team": game['teams']['away']['team']['name'],
            "Type": "Away",
            "Lineup": extract_lineup(away_lineup)
        })
    # Home lineup
    home_lineup = game.get('lineups', {}).get('home', {})
    if home_lineup and 'bats' in home_lineup:
        full_lineups.append({
            "Team": game['teams']['home']['team']['name'],
            "Type": "Home",
            "Lineup": extract_lineup(home_lineup)
        })

games_df = pd.DataFrame(games_table)

# --- 3. Streamlit Display ---

st.title("MLB Betr Model - Live MLB Data")
st.caption(f"Auto-pulled from MLB Stats API. Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.header("Today's Games & Probable Starters")
st.dataframe(games_df)

# Show starting lineups if available
if full_lineups:
    st.header("Posted Starting Lineups (Live Updates)")
    for lineup in full_lineups:
        st.subheader(f"{lineup['Team']} ({lineup['Type']})")
        st.table(pd.DataFrame(lineup['Lineup']))
else:
    st.info("No official lineups posted yet for today's games. Lineups typically become available 3–5 hours before first pitch.")

# --- 4. (OPTIONAL) Insert your Model Logic Here ---

st.header("Your Custom Model Output")
st.warning("Add your model logic here! Merge lineups, stats, weather, history, and output your top 15/10 plays below.")

# --- 5. (OPTIONAL) Download Button for Raw Data ---

if st.button("Download Raw Games Data"):
    st.download_button(
        label="Download as CSV",
        data=games_df.to_csv(index=False),
        file_name='mlb_games_today.csv',
        mime='text/csv'
    )

st.caption("Powered by MLB Stats API. For custom output/modeling, add logic below this line in the script.")

