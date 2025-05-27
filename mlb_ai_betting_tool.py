import streamlit as st
import requests
import pandas as pd
import datetime

st.set_page_config(page_title="MLB AI Prop Bet Finder", layout="wide")
st.title("MLB AI Prop Bet Finder")

# ------------- API KEYS --------------
# Get your (free tier) API keys from these sites and insert below:
ODDS_API_KEY = "YOUR_ODDS_API_KEY"      # https://the-odds-api.com/
SPORTSDATAIO_KEY = "YOUR_SPORTSDATAIO_KEY"  # https://sportsdata.io/
# For demonstration, code will run with demo/free endpoints as available

# ------------- FUNCTIONS --------------

@st.cache_data(ttl=1800)
def get_mlb_lineups():
    """Get today's MLB lineups from MLB Stats API (official, free)"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={today}"
    schedule = requests.get(url).json()
    game_ids = [g['gamePk'] for d in schedule.get('dates', []) for g in d.get('games', [])]
    lineups = []
    for game_id in game_ids:
        url2 = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
        resp = requests.get(url2).json()
        for team_type in ['home', 'away']:
            team = resp['teams'][team_type]['team']['name']
            try:
                players = [
                    p['person']['fullName']
                    for p in resp['teams'][team_type]['players'].values()
                    if 'battingOrder' in p and p['battingOrder'] <= 900
                ]
            except Exception:
                players = []
            lineups.append({'Team': team, 'Lineup': players, 'GameID': game_id})
    return pd.DataFrame(lineups)

@st.cache_data(ttl=600)
def get_oddsapi_props():
    """Pulls MLB odds (Moneyline, O/U, Spreads) from The Odds API"""
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=spreads,totals,h2h"
    resp = requests.get(url)
    if resp.status_code != 200:
        st.warning("Odds API quota reached or invalid key.")
        return pd.DataFrame()
    data = resp.json()
    all_bets = []
    for game in data:
        matchup = f"{game['home_team']} vs {game['away_team']}"
        commence = game.get('commence_time', '')
        for bookmaker in game.get('bookmakers', []):
            for market in bookmaker['markets']:
                if market['key'] in ['spreads', 'totals', 'h2h']:
                    for outcome in market['outcomes']:
                        all_bets.append({
                            'Matchup': matchup,
                            'Start': commence,
                            'Type': market['key'],
                            'Team': outcome.get('name', ''),
                            'Line': outcome.get('point', ''),
                            'Odds': outcome.get('price', ''),
                            'Book': bookmaker.get('title', '')
                        })
    return pd.DataFrame(all_bets)

def get_sportsdataio_props():
    """(Optional) For player props—requires API key, limited on free tier."""
    # Example endpoint: https://api.sportsdata.io/v4/mlb/odds/json/PlayerPropsByDate/{date}
    # Fill this in if you have a key.
    return pd.DataFrame()

def get_demo_player_props():
    """Demo player props table. Replace with real API/scraper as needed."""
    # Simulate data
    return pd.DataFrame({
        'Player': ['Aaron Judge', 'Ronald Acuna Jr.', 'Shohei Ohtani'],
        'Team': ['Yankees', 'Braves', 'Dodgers'],
        'Prop': ['Home Run', 'Hits', 'Total Bases'],
        'Line': [0.5, 1.5, 2.5],
        'Odds': [+225, -120, +105],
        'Opponent': ['Red Sox', 'Mets', 'Giants']
    })

# Your custom formula/model to determine best bets (replace with your logic)
def calculate_best_bets(props_df, lineups_df):
    """Example: Only recommend props where player is confirmed in lineup."""
    best_bets = []
    for _, row in props_df.iterrows():
        team_lineup = lineups_df[lineups_df['Team'].str.contains(row['Team'], case=False, na=False)]
        if not team_lineup.empty and any(row['Player'] in lineup for lineup in team_lineup['Lineup']):
            # Placeholder: Add your real win% model here
            best_bets.append({
                'Player': row['Player'],
                'Team': row['Team'],
                'Prop': row['Prop'],
                'Line': row['Line'],
                'Odds': row['Odds'],
                'Opponent': row['Opponent'],
                'Win % (Model)': 65 + (row['Odds'] % 10),  # <-- Dummy win%
            })
    return pd.DataFrame(best_bets)

# ------------- APP MAIN --------------

st.header("Today's Confirmed MLB Lineups")
lineups_df = get_mlb_lineups()
if lineups_df.empty:
    st.warning("No confirmed lineups yet. Try again later.")
else:
    st.dataframe(lineups_df)

st.header("Today's MLB Moneyline, Spread, and O/U Bets (from OddsAPI)")
odds_df = get_oddsapi_props()
if odds_df.empty:
    st.warning("OddsAPI data not available or no games today.")
else:
    st.dataframe(odds_df)

st.header("Today's Top Player Props (Demo/Replace with API/Scraper)")
player_props_df = get_demo_player_props()
st.dataframe(player_props_df)

# Cross-reference and run model
st.header("AI-Recommended Best MLB Prop Bets")
best_bets_df = calculate_best_bets(player_props_df, lineups_df)
if best_bets_df.empty:
    st.warning("No best bets found yet. Wait for confirmed lineups and player props.")
else:
    st.dataframe(best_bets_df)

st.info("Upgrade the model by adding your prop data source and formula for win percentage.")

# ------------- USER INPUTS / FILTERS (OPTIONAL) -------------
st.sidebar.header("Filters")
filter_team = st.sidebar.text_input("Team (optional)")
if filter_team:
    filtered = best_bets_df[best_bets_df['Team'].str.contains(filter_team, case=False, na=False)]
    st.subheader(f"Filtered Best Bets for {filter_team}")
    st.dataframe(filtered)

