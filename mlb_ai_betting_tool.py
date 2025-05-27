import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# --- Helper: Rotowire confirmed lineups ---
def get_rotowire_lineups():
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        tables = soup.find_all("div", class_="lineup")
        lineup_rows = []
        for game in tables:
            teams = game.find_all("div", class_="lineup__abbr")
            team_names = [t.text.strip() for t in teams]
            lineups = game.find_all("ul", class_="lineup__list")
            for idx, lineup in enumerate(lineups):
                players = lineup.find_all("li")
                for spot, p in enumerate(players, start=1):
                    name = p.text.strip().split('\n')[0]
                    pos = p.find("span", class_="lineup__pos").text.strip() if p.find("span", class_="lineup__pos") else ""
                    lineup_rows.append({
                        'Team': team_names[idx] if idx < len(team_names) else '',
                        'Player': name,
                        'Batting Order': spot,
                        'Position': pos,
                        'Source': 'Rotowire (Confirmed)'
                    })
        return pd.DataFrame(lineup_rows)
    except Exception:
        return pd.DataFrame()

# --- Helper: Baseball Press projected lineups ---
def get_baseballpress_projected_lineups():
    url = "https://www.baseballpress.com/api/lineups.json"
    try:
        res = requests.get(url)
        data = res.json()
    except Exception:
        return pd.DataFrame()
    lineup_rows = []
    for game in data.get('data', []):
        for side in ['home', 'away']:
            t = game.get(side, {})
            team = t.get('abbr', '')
            lineup = t.get('players', [])
            for spot, p in enumerate(lineup, start=1):
                batter = p.get('player_name', '')
                pos = p.get('position', '')
                lineup_rows.append({
                    'Team': team,
                    'Player': batter,
                    'Batting Order': spot,
                    'Position': pos,
                    'Source': 'Baseball Press (Projected)'
                })
    return pd.DataFrame(lineup_rows)

# --- Helper: Get yesterday's lineups ---
def get_yesterdays_lineups():
    yest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://www.baseballpress.com/api/lineups.json?date={yest}"
    try:
        res = requests.get(url)
        data = res.json()
    except Exception:
        return pd.DataFrame()
    lineup_rows = []
    for game in data.get('data', []):
        for side in ['home', 'away']:
            t = game.get(side, {})
            team = t.get('abbr', '')
            lineup = t.get('players', [])
            for spot, p in enumerate(lineup, start=1):
                batter = p.get('player_name', '')
                pos = p.get('position', '')
                lineup_rows.append({
                    'Team': team,
                    'Player': batter,
                    'Batting Order': spot,
                    'Position': pos,
                    'Source': "Yesterday's Lineup"
                })
    return pd.DataFrame(lineup_rows)

# --- Fallback: pick the best available lineup source ---
def get_daily_lineups():
    st.info("Checking Rotowire for confirmed lineups...")
    df_rw = get_rotowire_lineups()
    if not df_rw.empty:
        st.success("Confirmed lineups loaded from Rotowire.")
        return df_rw

    st.warning("No confirmed lineups. Pulling projected lineups from Baseball Press...")
    df_bp = get_baseballpress_projected_lineups()
    if not df_bp.empty:
        st.success("Projected lineups loaded from Baseball Press.")
        return df_bp

    st.warning("No projected lineups. Pulling yesterday's lineups as fallback...")
    df_yd = get_yesterdays_lineups()
    if not df_yd.empty:
        st.success("Loaded yesterday's lineups as fallback.")
        return df_yd

    st.error("No confirmed, projected, or yesterday's lineups available.")
    return pd.DataFrame()

# --- Mock: get weather, matchups, historic data as before ---
def get_daily_weather():
    # Placeholder: Replace with real API
    return pd.DataFrame({
        'Ballpark': ['Yankee Stadium', 'Truist Park', 'Dodger Stadium'],
        'Temperature (F)': [78, 85, 75],
        'Wind': ['8 mph Out', '5 mph In', '2 mph L to R'],
        'Conditions': ['Sunny', 'Cloudy', 'Clear']
    })

def get_daily_matchups():
    # Placeholder: Replace with real API
    return pd.DataFrame({
        'Home': ['Yankees', 'Braves', 'Dodgers'],
        'Away': ['Red Sox', 'Phillies', 'Padres'],
        'Home SP': ['Gerrit Cole', 'Max Fried', 'Tyler Glasnow'],
        'Away SP': ['Chris Sale', 'Zack Wheeler', 'Yu Darvish']
    })

def get_historic_data():
    # Placeholder: Replace with your real stats load/API!
    return pd.DataFrame({
        'Player': ['Aaron Judge', 'Ronald Acuna Jr.', 'Shohei Ohtani'],
        'HR %': [0.07, 0.05, 0.06],
        'TB %': [0.45, 0.38, 0.41],
        'Hits %': [0.28, 0.30, 0.27]
    })

# --- Model Logic Example ---
def run_mlb_betr_model(lineups, weather, matchups, historic_data):
    merged = pd.merge(lineups, historic_data, on='Player', how='left')
    merged['Win %'] = (merged['HR %'].fillna(0) + merged['TB %'].fillna(0) + merged['Hits %'].fillna(0)) / 3 + 0.5
    merged = merged.sort_values('Win %', ascending=False).reset_index(drop=True)
    merged['Type'] = ['Best Play']*min(15, len(merged)) + ['Longshot']*min(10, max(len(merged)-15, 0)) + ['Other']*max(0, len(merged)-25)
    merged = merged[['Player', 'Team', 'Batting Order', 'Position', 'Win %', 'Type', 'Source']]
    return merged

# --- Streamlit UI ---
st.title("MLB Betr: Daily Model Output")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("Loading data..."):
    lineups = get_daily_lineups()
    if lineups.empty:
        st.error("No lineups available from any source.")
        st.stop()
    weather = get_daily_weather()
    matchups = get_daily_matchups()
    historic_data = get_historic_data()
    output_df = run_mlb_betr_model(lineups, weather, matchups, historic_data)

st.subheader("Today's Weather by Ballpark")
st.dataframe(weather)

st.subheader("Today's Pitching Matchups")
st.dataframe(matchups)

st.header("Starting Lineups (Source in column)")
st.dataframe(lineups)

st.header("Top 15 Best Plays (by Win %)")
best_plays = output_df[output_df['Type'] == 'Best Play'].head(15).copy()
st.dataframe(best_plays)

st.header("Top 10 Longshot/Variance Plays (by Win %)")
longshots = output_df[output_df['Type'] == 'Longshot'].head(10).copy()
st.dataframe(longshots)

# Download button for CSV
st.download_button(
    label="Download All Results as CSV",
    data=output_df.to_csv(index=False),
    file_name='mlb_betr_model_output.csv',
    mime='text/csv'
)

with st.expander("Show all players evaluated"):
    st.dataframe(output_df)

st.info("Lineups source displayed in 'Source' column. You can further customize API sources and model logic in this script.")

