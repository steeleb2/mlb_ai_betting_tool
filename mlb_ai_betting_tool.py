import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# ---------- CONFIG: Set your file locations here ----------
HISTORIC_DATA_PATH = 'player_stats.csv'   # <-- Point this to your real player stats file!

# ---------- UTILS: API helpers ----------
def get_today_mlb_games():
    today = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&expand=schedule.lineups,schedule.probablePitchers"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        return data.get('dates', [])[0].get('games', []) if data.get('dates') else []
    except Exception as e:
        st.error(f"Could not fetch MLB games: {e}")
        return []

def get_weather_by_city(city):
    # Simple weather: Open-Meteo or wttr.in (no API key needed)
    url = f"https://wttr.in/{city}?format=%t|%w|%C"
    try:
        txt = requests.get(url, timeout=10).text.strip()
        parts = txt.split('|')
        temp, wind, cond = (parts + ["N/A"]*3)[:3]
        return temp, wind, cond
    except:
        return "N/A", "N/A", "N/A"

def get_lineup_players(lineup_data, team_name, opponent_name, venue, homeaway):
    # Parse lineup bats list from MLB API response
    players = []
    if lineup_data and 'bats' in lineup_data:
        for bat in sorted(lineup_data['bats'], key=lambda x: x['battingOrder']):
            players.append({
                "Player": bat.get('fullName'),
                "Batting Order": bat.get('battingOrder'),
                "Position": bat.get('position', {}).get('abbreviation', ''),
                "Team": team_name,
                "Opponent": opponent_name,
                "Venue": venue,
                "Home/Away": homeaway
            })
    return players

# ---------- LOAD HISTORIC STATS ----------
def load_historic_stats():
    try:
        df = pd.read_csv(HISTORIC_DATA_PATH)
        # Expected columns: Player, HR_rate, Hits_rate, TB_rate, KO_rate, ...etc
        return df
    except Exception as e:
        st.warning(f"Failed to load player stats: {e}")
        return pd.DataFrame()

# ---------- MODEL LOGIC (you must customize this) ----------
def calculate_win_percent(row, prop_type):
    # Example: for Home Run, you might use their HR_rate; for Hits, their Hits_rate, etc.
    # You *must* tune this for your data and prop!
    if prop_type == "HR":
        return row.get("HR_rate", 0)
    elif prop_type == "Hits":
        return row.get("Hits_rate", 0)
    elif prop_type == "TB":
        return row.get("TB_rate", 0)
    elif prop_type == "KO":
        return row.get("KO_rate", 0)
    else:
        return 0

def model_output(merged, prop_type):
    merged['Win %'] = merged.apply(lambda row: calculate_win_percent(row, prop_type), axis=1)
    merged = merged.sort_values('Win %', ascending=False).reset_index(drop=True)
    # Assign "Best Play" and "Longshot"
    merged['Type'] = ['Best Play']*min(15, len(merged)) + ['Longshot']*max(0, min(10, len(merged)-15)) + ['Other']*max(0, len(merged)-25)
    return merged

# ---------- MAIN APP ----------
st.title("MLB Betr: Full-Stack AI Betting Model (Live Data)")

with st.spinner("Loading MLB games, lineups, and weather..."):
    games = get_today_mlb_games()
    time.sleep(1)  # Give API a second to avoid rate limits
    lineup_players = []
    game_lines = []
    weather_table = []
    for g in games:
        home_team = g['teams']['home']['team']['name']
        away_team = g['teams']['away']['team']['name']
        venue = g.get('venue', {}).get('name', '')
        start_time = pd.to_datetime(g['gameDate']).tz_convert('US/Eastern').strftime('%I:%M %p')
        city = venue.split(' ')[0] if venue else "N/A"
        temp, wind, cond = get_weather_by_city(city)
        # Weather Table
        weather_table.append({
            "Game": f"{away_team} @ {home_team}",
            "Venue": venue,
            "Start": start_time,
            "Weather Temp": temp,
            "Wind": wind,
            "Conditions": cond
        })
        # Starters (Game lines)
        home_sp = g['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
        away_sp = g['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
        game_lines.append({
            "Game": f"{away_team} @ {home_team}",
            "Venue": venue,
            "Start": start_time,
            "Home Starter": home_sp,
            "Away Starter": away_sp,
            # Add odds, lines etc. if you integrate an odds API!
        })
        # Lineups
        for side in ['away', 'home']:
            lineup = g.get('lineups', {}).get(side, {})
            players = get_lineup_players(
                lineup, 
                g['teams'][side]['team']['name'], 
                g['teams']['home' if side=='away' else 'away']['team']['name'],
                venue,
                "Home" if side == "home" else "Away"
            )
            lineup_players.extend(players)

    lineups_df = pd.DataFrame(lineup_players)
    games_df = pd.DataFrame(game_lines)
    weather_df = pd.DataFrame(weather_table)

# Load your historic data
historic_stats = load_historic_stats()

st.header("Today's MLB Games & Weather")
st.dataframe(weather_df)

st.header("Probable Starters and Game Lines")
st.dataframe(games_df)

st.header("Starting Lineups")
if not lineups_df.empty:
    for t, g in lineups_df.groupby('Team'):
        st.subheader(t)
        st.table(g[['Batting Order', 'Player', 'Position', 'Home/Away', 'Opponent', 'Venue']])
else:
    st.info("No lineups posted yet. (They usually post 3-5 hours before gametime)")

# ---------- PROPS MODEL: HR, Hits, TB, KO ----------
prop_categories = {'HR': "Home Runs", 'Hits': "Hits", 'TB': "Total Bases", 'KO': "Strikeouts"}
for prop_key, prop_label in prop_categories.items():
    st.header(f"{prop_label} Props: Top Model Plays")
    if not lineups_df.empty and not historic_stats.empty:
        merged = pd.merge(lineups_df, historic_stats, on="Player", how="left").fillna(0)
        prop_df = model_output(merged, prop_key)
        st.subheader("Top 15 Best Plays")
        st.dataframe(prop_df[prop_df['Type'] == 'Best Play'].head(15)[
            ['Player', 'Team', 'Opponent', 'Venue', 'Home/Away', 'Batting Order', 'Position', 'Win %']
        ])
        st.subheader("Top 10 Longshots")
        st.dataframe(prop_df[prop_df['Type'] == 'Longshot'].head(10)[
            ['Player', 'Team', 'Opponent', 'Venue', 'Home/Away', 'Batting Order', 'Position', 'Win %']
        ])
        st.download_button(
            label=f"Download {prop_label} Model Output (CSV)",
            data=prop_df.to_csv(index=False),
            file_name=f'mlb_{prop_key.lower()}_model_output.csv',
            mime='text/csv'
        )
    else:
        st.info("Waiting for lineups and player stats.")

# ---------- GAME LINES MODEL (MONEYLINE, SPREAD, O/U) ----------
st.header("Game Lines Model Output")
# Here you’d integrate with an odds API (or upload a CSV of lines) and run your models!
# You can add logic here as you build out your game line prediction functions.

st.caption("Model logic is fully customizable! Connect your own stats sources and odds APIs for more power.")

