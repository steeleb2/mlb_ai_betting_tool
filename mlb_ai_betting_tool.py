import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import time

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# ------------- 1. Lineup Logic: Official + Projected Fallback -----------------

def get_official_lineups():
    """
    Replace this with MLB StatsAPI, SportsDataIO, or your paid data feed.
    For now, returns empty (so will always use projections until you wire up an official lineup API).
    """
    return pd.DataFrame()  # Simulated empty

def get_projected_lineups_rotowire():
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, "lxml")
    games = soup.find_all("div", class_="lineup is-mlb")
    lineup_rows = []
    for game in games:
        try:
            teams = game.find_all("div", class_="lineup__abbr")
            away = teams[0].text.strip()
            home = teams[1].text.strip()
            game_time = game.find("div", class_="lineup__time").text.strip()
            away_players = [x.text.strip() for x in game.select('.lineup__list--away .lineup__player')]
            home_players = [x.text.strip() for x in game.select('.lineup__list--home .lineup__player')]
            for i, player in enumerate(away_players):
                lineup_rows.append({
                    "Player": player,
                    "Team": away,
                    "Batting Order": i + 1,
                    "Position": "",  # (Optional: scrape position as well)
                    "Opponent": home,
                    "Game Time": game_time,
                    "Source": "Projected (Rotowire)"
                })
            for i, player in enumerate(home_players):
                lineup_rows.append({
                    "Player": player,
                    "Team": home,
                    "Batting Order": i + 1,
                    "Position": "",
                    "Opponent": away,
                    "Game Time": game_time,
                    "Source": "Projected (Rotowire)"
                })
        except Exception:
            continue
    return pd.DataFrame(lineup_rows)

def get_daily_lineups():
    df_official = get_official_lineups()
    if not df_official.empty:
        st.success("Loaded OFFICIAL posted lineups.")
        return df_official
    st.warning("No official lineups yet. Using projected lineups from Rotowire.")
    df_projected = get_projected_lineups_rotowire()
    return df_projected

# ------------- 2. Weather Logic -----------------

def get_daily_weather():
    # Demo uses Open-Meteo, real implementation should map ballparks to lat/lon
    # For now, fake some sample data for the teams shown
    return pd.DataFrame({
        'Ballpark': ['Yankee Stadium', 'Truist Park', 'Dodger Stadium'],
        'Temperature (F)': [78, 85, 75],
        'Wind': ['8 mph Out', '5 mph In', '2 mph L to R'],
        'Conditions': ['Sunny', 'Cloudy', 'Clear']
    })

# ------------- 3. Matchups Logic -----------------

def get_daily_matchups():
    # Replace this with your real matchup API/scrape
    return pd.DataFrame({
        'Home': ['Yankees', 'Braves', 'Dodgers'],
        'Away': ['Red Sox', 'Phillies', 'Padres'],
        'Home SP': ['Gerrit Cole', 'Max Fried', 'Tyler Glasnow'],
        'Away SP': ['Chris Sale', 'Zack Wheeler', 'Yu Darvish']
    })

# ------------- 4. Historical Player Data (API) -----------------

def get_player_stats_bref(player_name):
    """
    Example: Scrape player stats from Baseball Reference. 
    Ideally swap with paid API for production.
    """
    # For demo, just return some sample data
    player_stats = {
        "Aaron Judge": {"HR %": 0.068, "TB %": 0.45, "Hits %": 0.28, "K %": 0.27},
        "Ronald Acuna Jr.": {"HR %": 0.047, "TB %": 0.38, "Hits %": 0.31, "K %": 0.21},
        "Shohei Ohtani": {"HR %": 0.057, "TB %": 0.41, "Hits %": 0.27, "K %": 0.28},
    }
    return player_stats.get(player_name, {"HR %": 0.03, "TB %": 0.27, "Hits %": 0.19, "K %": 0.26})

def get_historic_data(lineups):
    stats = []
    for _, row in lineups.iterrows():
        s = get_player_stats_bref(row['Player'])
        stats.append({**{"Player": row['Player']}, **s})
    return pd.DataFrame(stats)

# ------------- 5. MODEL LOGIC -----------------

def run_mlb_betr_model(lineups, weather, matchups, historic_data):
    # Merge lineups with historic data
    merged = pd.merge(lineups, historic_data, on='Player', how='left')
    # Custom Win % formula: Example based on your previous formula
    merged['Win %'] = (merged['HR %'].fillna(0) + merged['TB %'].fillna(0) + merged['Hits %'].fillna(0)) / 3 + 0.5
    merged = merged.sort_values('Win %', ascending=False).reset_index(drop=True)
    # Mark Top 15/Longshots
    merged['Type'] = ['Best Play'] * min(15, len(merged)) + ['Longshot'] * (min(25, len(merged)) - 15) + ['Other'] * (len(merged) - 25)
    return merged

# ------------- 6. STREAMLIT APP LOGIC -----------------

st.title("MLB Betr: Daily Model Output")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("Loading daily lineups..."):
    lineups_df = get_daily_lineups()

if lineups_df.empty:
    st.error("No lineups available.")
    st.stop()

# Optionally show source
if "Source" in lineups_df.columns:
    st.info(f"Lineup Source: {lineups_df['Source'].iloc[0]}")

with st.spinner("Loading weather data..."):
    weather_df = get_daily_weather()
st.subheader("Today's Weather by Ballpark")
st.dataframe(weather_df)

with st.spinner("Loading pitching matchups..."):
    matchup_df = get_daily_matchups()
st.subheader("Today's Pitching Matchups")
st.dataframe(matchup_df)

with st.spinner("Loading player historic data..."):
    historic_df = get_historic_data(lineups_df)

with st.spinner("Running model..."):
    output_df = run_mlb_betr_model(lineups_df, weather_df, matchup_df, historic_df)

# ------------- 7. DISPLAY OUTPUT -----------------

st.header("Top 15 Best Plays (by Win %)")
best_plays = output_df[output_df['Type'] == 'Best Play'].head(15).copy()
st.dataframe(best_plays)

st.header("Top 10 Longshot/Variance Plays (by Win %)")
longshots = output_df[output_df['Type'] == 'Longshot'].head(10).copy()
st.dataframe(longshots)

# Download button
st.download_button(
    label="Download All Results as CSV",
    data=output_df.to_csv(index=False),
    file_name='mlb_betr_model_output.csv',
    mime='text/csv'
)

with st.expander("Show all players evaluated"):
    st.dataframe(output_df)

# Show posted lineups for each game
st.header("Lineups for Each Game")
games = lineups_df.groupby(['Opponent', 'Team', 'Game Time'])
for (opp, team, time_), group in games:
    st.subheader(f"{team} vs {opp} @ {time_}")
    st.table(group[['Batting Order', 'Player', 'Position']])

st.info("Lineups auto-refresh between official (when posted) and Rotowire projected. To add real-time odds, connect a paid API.")

