import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import datetime
import json

# ----------- API KEYS -------------
ODDS_API_KEY = "2f4b2a85425623b90862432824f901aa"

st.set_page_config(page_title="MLB AI Prop Bet Finder", layout="wide")
st.title("MLB AI Prop Bet Finder")

# ----------- DATA SOURCES -------------

@st.cache_data(ttl=1800)
def get_mlb_lineups():
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

@st.cache_data(ttl=600)
def scrape_prizepicks_mlb_props_html():
    """
    Scrapes MLB player props from PrizePicks' public web page by extracting embedded JSON from HTML.
    """
    url = "https://www.prizepicks.com/lines/mlb"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        st.error(f"Failed to fetch PrizePicks: {e}")
        return pd.DataFrame()
    if resp.status_code != 200:
        st.warning(f"Could not reach PrizePicks (status code {resp.status_code}).")
        return pd.DataFrame()
    soup = BeautifulSoup(resp.text, "lxml")
    scripts = soup.find_all("script")
    data_script = None
    for script in scripts:
        if "window.__NUXT__=" in script.text:
            data_script = script.text
            break
    if not data_script:
        st.warning("PrizePicks page structure changed—no JSON found.")
        return pd.DataFrame()
    try:
        json_data = data_script.split("window.__NUXT__=")[-1]
        if json_data.endswith(";"):
            json_data = json_data[:-1]
        data = json.loads(json_data)
    except Exception as e:
        st.warning(f"Failed to parse PrizePicks embedded JSON: {e}")
        return pd.DataFrame()
    player_props = []
    try:
        projections = data['state']['projections']
        included = {item['id']: item for item in data['state']['included']}
        for proj in projections:
            try:
                player_id = proj['relationships']['new_player']['data']['id']
                player = included.get(player_id, {})
                player_name = player.get('attributes', {}).get('name', 'Unknown')
                team = player.get('attributes', {}).get('team', {}).get('name', '')
                stat_type = proj['attributes']['stat_type']
                line_score = proj['attributes']['line_score']
                opp_team = proj['attributes'].get('description', '')
                if stat_type in ['HITS', 'HOMERUNS', 'TOTAL_BASES', 'STRIKEOUTS']:
                    player_props.append({
                        'Player': player_name,
                        'Team': team,
                        'Prop': stat_type,
                        'Line': line_score,
                        'Opponent': opp_team,
                        'Source': 'PrizePicks'
                    })
            except Exception:
                continue
    except Exception as e:
        st.warning(f"PrizePicks data structure changed—cannot extract projections: {e}")
        return pd.DataFrame()
    return pd.DataFrame(player_props)

def calculate_best_bets(props_df, lineups_df):
    """Recommend props where player is confirmed in lineup (expand this logic for your model)."""
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
                'Opponent': row['Opponent'],
                'Source': row['Source'],
                'Win % (Model)': 65  # <-- Dummy win%, swap for real model
            })
    return pd.DataFrame(best_bets)

# ------------- APP MAIN -------------

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

st.header("PrizePicks MLB Player Props (Hits, HRs, TBs, KOs)")
prizepicks_df = scrape_prizepicks_mlb_props_html()
if prizepicks_df.empty:
    st.warning("No PrizePicks MLB player props found.")
else:
    st.dataframe(prizepicks_df)

st.header("AI-Recommended Best MLB Prop Bets (PrizePicks + Lineups)")
best_bets_df = calculate_best_bets(prizepicks_df, lineups_df)
if best_bets_df.empty:
    st.warning("No best bets found yet. Wait for confirmed lineups and player props.")
else:
    st.dataframe(best_bets_df)

st.info("Upgrade the model by adding your prop data source and formula for win percentage.")

# ------------ USER FILTERS (OPTIONAL) -----------
st.sidebar.header("Filters")
filter_team = st.sidebar.text_input("Team (optional)")
if filter_team:
    filtered = best_bets_df[best_bets_df['Team'].str.contains(filter_team, case=False, na=False)]
    st.subheader(f"Filtered Best Bets for {filter_team}")
    st.dataframe(filtered)
