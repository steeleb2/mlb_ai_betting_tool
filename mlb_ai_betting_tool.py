import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

st.set_page_config(page_title="MLB Betr Model - Auto Fetch", layout="wide")
st.title("⚾ MLB Betr Model — Automated Daily Output")

# -------- MLB VENUE LAT/LON MAPPING (partial list, extend as needed) --------
VENUE_COORDS = {
    "Fenway Park": (42.3467, -71.0972),
    "Yankee Stadium": (40.8296, -73.9262),
    "Camden Yards": (39.2839, -76.6217),
    "Tropicana Field": (27.7683, -82.6534),
    "Kauffman Stadium": (39.0517, -94.4803),
    "Dodger Stadium": (34.0739, -118.239),
    "Oracle Park": (37.7786, -122.389),
    "Wrigley Field": (41.9484, -87.6553),
    "Citizens Bank Park": (39.9057, -75.1665),
    # Add all venues as needed!
}

# -------- GET TODAY'S MLB GAMES --------
def get_today_games():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    resp = requests.get(url)
    data = resp.json()
    games = []
    for date in data.get('dates', []):
        for game in date.get('games', []):
            games.append({
                'gamePk': game['gamePk'],
                'home': game['teams']['home']['team']['name'],
                'away': game['teams']['away']['team']['name'],
                'venue': game['venue']['name'],
                'gameTime': game['gameDate'],
            })
    return pd.DataFrame(games)

# -------- GET WEATHER FOR VENUE --------
def get_weather(venue):
    coords = VENUE_COORDS.get(venue)
    if not coords:
        return "N/A"
    lat, lon = coords
    # Open-Meteo Free API
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation,weathercode&current_weather=true&temperature_unit=fahrenheit"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        return "N/A"
    data = resp.json()
    temp = data.get('current_weather', {}).get('temperature')
    code = data.get('current_weather', {}).get('weathercode', 0)
    description = weather_code_to_desc(code)
    return f"{temp}°F, {description}"

def weather_code_to_desc(code):
    # Simplified Open-Meteo code mapping
    mapping = {
        0: "Clear",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Cloudy",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Freezing drizzle (dense)",
        61: "Slight rain",
        63: "Rain",
        65: "Heavy rain",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, "Unknown")

# -------- GET STARTING LINEUPS FOR A GAME --------
def get_lineup(gamePk):
    url = f"https://statsapi.mlb.com/api/v1/game/{gamePk}/boxscore"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    lineups = []
    for team_type in ['home', 'away']:
        team = data['teams'][team_type]
        team_name = team['team']['name']
        for player_id, player in team['players'].items():
            # Only include batters in the lineup
            order = player.get('battingOrder', None)
            if order is not None and order > 0:
                lineups.append({
                    "Team": team_name,
                    "Player": player['person']['fullName'],
                    "BattingOrder": order,
                    "Position": player.get('position', {}).get('abbreviation', 'N/A'),
                })
    return pd.DataFrame(lineups)

# -------- MAIN APP LOGIC --------
games_df = get_today_games()
if games_df.empty:
    st.error("No MLB games found for today.")
else:
    st.subheader("Today's Games")
    st.dataframe(games_df)

    all_lineups = []
    st.write("---")
    st.subheader("Fetching Lineups and Weather... (May take a moment)")
    for idx, row in games_df.iterrows():
        with st.expander(f"{row['away']} @ {row['home']} — {row['venue']}"):
            weather = get_weather(row['venue'])
            st.write(f"Weather: {weather}")
            lineup_df = get_lineup(row['gamePk'])
            if lineup_df is not None and not lineup_df.empty:
                st.dataframe(lineup_df)
                lineup_df['Venue'] = row['venue']
                lineup_df['Weather'] = weather
                all_lineups.append(lineup_df)
            else:
                st.write("Lineup not yet available.")

    # Show ALL LINEUPS for all games (summary view)
    if all_lineups:
        full_df = pd.concat(all_lineups, ignore_index=True)
        st.subheader("All Lineups (Today's Games, with Weather)")
        st.dataframe(full_df)
    else:
        st.warning("No starting lineups available yet for any games.")

# ----------- (YOUR MODEL LOGIC/PLAYER PROP/SCORING CODE GOES HERE) -----------
st.write("---")
st.markdown("""
#### 🚀 **Next Steps:**
- Add your player prop/odds API scraping (FanDuel, DraftKings, Underdog, etc)
- Integrate your win percentage or scoring formulas here!
- Output 15 Best Plays and 10 Longshots (auto generate table)
- Optional: Export to Excel/Google Sheets or send to email/Discord

**Want the next section written in code? Just ask for your specific model logic and output format.**
""")
