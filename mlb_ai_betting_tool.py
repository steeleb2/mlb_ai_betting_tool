import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# --- 1. LINEUP SCRAPERS ---

def get_rotowire_lineups():
    """Scrape confirmed lineups from Rotowire."""
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    games = soup.find_all("div", class_="lineup is-mlb")
    lineups = []
    for game in games:
        teams = game.find_all("div", class_="lineup__abbr")
        if not teams or len(teams) < 2:
            continue
        team1 = teams[0].text.strip()
        team2 = teams[1].text.strip()
        # Rotowire lists both teams, get each team's hitters:
        hitters = game.find_all("ul", class_="lineup__list")
        if len(hitters) < 2:
            continue
        for team_idx, lineup_ul in enumerate(hitters):
            for spot, li in enumerate(lineup_ul.find_all("li"), start=1):
                name_tag = li.find("a", class_="lineup__player-link")
                if not name_tag:
                    continue
                player = name_tag.text.strip()
                position_tag = li.find("span", class_="lineup__player-position")
                pos = position_tag.text.strip() if position_tag else ""
                team = [team1, team2][team_idx]
                lineups.append({
                    'Team': team,
                    'Player': player,
                    'Batting Order': spot,
                    'Position': pos,
                    'Source': "Confirmed"
                })
    return pd.DataFrame(lineups)

def get_baseballpress_projected_lineups():
    """Pull projected lineups from Baseball Press public API."""
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
            status = t.get('status', 'Projected')
            lineup = t.get('players', [])
            for spot, p in enumerate(lineup, start=1):
                batter = p.get('player_name', '')
                pos = p.get('position', '')
                lineup_rows.append({
                    'Team': team,
                    'Player': batter,
                    'Batting Order': spot,
                    'Position': pos,
                    'Source': f"BaseballPress ({status})"
                })
    return pd.DataFrame(lineup_rows)

def get_daily_lineups():
    """Try Rotowire first, fallback to Baseball Press."""
    st.info("Checking Rotowire for confirmed lineups...")
    df_rw = get_rotowire_lineups()
    if not df_rw.empty:
        st.success("Confirmed lineups loaded from Rotowire.")
        return df_rw
    st.warning("No confirmed lineups yet. Pulling projected lineups from Baseball Press.")
    df_bp = get_baseballpress_projected_lineups()
    if not df_bp.empty:
        st.success("Projected lineups loaded from Baseball Press.")
        return df_bp
    st.error("No confirmed or projected lineups available from Rotowire or Baseball Press.")
    return pd.DataFrame()

# --- 2. WEATHER SCRAPER ---

def get_daily_weather():
    # Demo: Replace with a real weather API for each park if needed!
    return pd.DataFrame({
        'Ballpark': ['Yankee Stadium', 'Truist Park', 'Dodger Stadium'],
        'Temperature (F)': [78, 85, 75],
        'Wind': ['8 mph Out', '5 mph In', '2 mph L to R'],
        'Conditions': ['Sunny', 'Cloudy', 'Clear']
    })

# --- 3. MATCHUPS DEMO ---

def get_daily_matchups():
    # Demo: Replace with real matchup API or scraping if needed
    return pd.DataFrame({
        'Home': ['Yankees', 'Braves', 'Dodgers'],
        'Away': ['Red Sox', 'Phillies', 'Padres'],
        'Home SP': ['Gerrit Cole', 'Max Fried', 'Tyler Glasnow'],
        'Away SP': ['Chris Sale', 'Zack Wheeler', 'Yu Darvish']
    })

# --- 4. HISTORIC DATA ---

def get_historic_data():
    # Replace with your historic stats file/API!
    return pd.DataFrame({
        'Player': ['Aaron Judge', 'Ronald Acuna Jr.', 'Shohei Ohtani'],
        'HR %': [0.07, 0.05, 0.06],
        'TB %': [0.45, 0.38, 0.41],
        'Hits %': [0.28, 0.30, 0.27]
    })

# --- 5. MLB Betr MODEL LOGIC ---

def run_mlb_betr_model(lineups, historic_data):
    # Merge lineups with historic player data on player name
    merged = pd.merge(lineups, historic_data, on='Player', how='left')
    # Fill missing stats with mean or 0 for demo; ideally use latest data
    for col in ['HR %', 'TB %', 'Hits %']:
        merged[col] = merged[col].fillna(merged[col].mean())
    # Calculate Win %: YOUR model logic
    merged['Win %'] = (merged['HR %'] + merged['TB %'] + merged['Hits %']) / 3 + 0.5
    merged = merged.sort_values('Win %', ascending=False).reset_index(drop=True)
    # Label top 15 Best Play, next 10 Longshot, rest Other
    n = len(merged)
    merged['Type'] = ['Best Play']*min(15, n) + ['Longshot']*min(10, max(n-15,0)) + ['Other']*max(n-25,0)
    return merged

# --- 6. STREAMLIT UI ---

st.title("MLB Betr Model: Daily Automated Output")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("Gathering all data..."):
    lineups = get_daily_lineups()
    if lineups.empty:
        st.stop()
    weather = get_daily_weather()
    matchups = get_daily_matchups()
    historic_data = get_historic_data()
    output_df = run_mlb_betr_model(lineups, historic_data)

st.subheader("Today's Lineups (by source)")
st.dataframe(lineups)

st.subheader("Weather (Demo Data)")
st.dataframe(weather)

st.subheader("Pitching Matchups (Demo Data)")
st.dataframe(matchups)

st.header("Top 15 Best Plays (Win %)")
st.dataframe(output_df[output_df['Type'] == 'Best Play'].head(15))

st.header("Top 10 Longshot/Variance Plays (Win %)")
st.dataframe(output_df[output_df['Type'] == 'Longshot'].head(10))

st.download_button(
    label="Download Full Results as CSV",
    data=output_df.to_csv(index=False),
    file_name='mlb_betr_model_output.csv',
    mime='text/csv'
)

with st.expander("All Model Players"):
    st.dataframe(output_df)

st.info("Historic player stats: swap in your full API/data source for true daily output. Lineups auto-pulled from Rotowire (confirmed) and Baseball Press (projected). Weather/matchups shown as demo.")

