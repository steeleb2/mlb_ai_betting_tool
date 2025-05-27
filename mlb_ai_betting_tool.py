import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# 1. MLB API Helper Functions

def get_today_games():
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?date={today}&sportId=1"
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
                'status': game['status']['detailedState']
            })
    return games

def get_game_lineup(gamePk):
    url = f"https://statsapi.mlb.com/api/v1/game/{gamePk}/boxscore"
    resp = requests.get(url)
    data = resp.json()
    players = []
    teams = ['home', 'away']
    for t in teams:
        team_data = data['teams'][t]
        lineup = team_data.get('battingOrder', [])
        if not lineup:  # fallback: get from players marked as starter
            for pid, pdata in team_data['players'].items():
                if pdata.get('gameStatus', {}).get('isInStartingLineup', False):
                    players.append({
                        'id': pdata['person']['id'],
                        'Player': pdata['person']['fullName'],
                        'Team': team_data['team']['name'],
                        'Position': pdata['position']['abbreviation'],
                        'Batting Order': None
                    })
            continue
        for idx, pid in enumerate(lineup):
            p = team_data['players'][f'ID{pid}']
            players.append({
                'id': p['person']['id'],
                'Player': p['person']['fullName'],
                'Team': team_data['team']['name'],
                'Position': p['position']['abbreviation'],
                'Batting Order': idx + 1
            })
    return players

def get_player_season_stats(player_id, season=None):
    if season is None:
        season = datetime.now().year
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&season={season}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        stats = data.get('stats', [])
        if stats and 'splits' in stats[0] and stats[0]['splits']:
            return stats[0]['splits'][0]['stat']
    except Exception as e:
        print(f"Error fetching stats for {player_id}: {e}")
    return {}

def get_weather_for_ballpark(venue_name):
    # This is a stub. You can add a real weather API for each ballpark location.
    return {"Temperature (F)": 75, "Wind": "5 mph Out", "Conditions": "Partly Cloudy"}

# 2. Assemble All Lineups and Stats

@st.cache_data(ttl=60*10)
def get_full_lineups_and_stats():
    games = get_today_games()
    all_players = []
    weather = []
    for g in games:
        try:
            lineup = get_game_lineup(g['gamePk'])
            # Weather (stub or call your API here)
            weather.append({
                "Ballpark": g['venue'],
                **get_weather_for_ballpark(g['venue'])
            })
            # Player stats
            for player in lineup:
                stats = get_player_season_stats(player['id'])
                # Use 1 for AB if missing to avoid ZeroDivisionError
                ab = int(stats.get('atBats', 1)) or 1
                all_players.append({
                    **player,
                    "HR": int(stats.get('homeRuns', 0)),
                    "Hits": int(stats.get('hits', 0)),
                    "TB": int(stats.get('totalBases', 0)),
                    "KO": int(stats.get('strikeOuts', 0)),
                    "AB": ab,
                })
                time.sleep(0.1)  # Rate limit (avoid hammering MLB API)
        except Exception as e:
            st.warning(f"Failed to load lineup or stats for {g['home']} vs {g['away']}: {e}")
    return pd.DataFrame(all_players), pd.DataFrame(weather), games

# 3. Model Calculations

def model_win_percent(row, prop):
    ab = row['AB'] if row['AB'] else 1
    if prop == "HR":
        return row['HR'] / ab
    if prop == "Hits":
        return row['Hits'] / ab
    if prop == "TB":
        return row['TB'] / ab
    if prop == "KO":
        return row['KO'] / ab
    return 0

def rank_and_output(df, prop):
    df = df.copy()
    df[f"{prop} Win %"] = df.apply(lambda row: model_win_percent(row, prop), axis=1)
    df = df.sort_values(f"{prop} Win %", ascending=False).reset_index(drop=True)
    df['Type'] = 'Longshot'
    df.loc[:14, 'Type'] = 'Best Play'
    return df

# 4. Streamlit UI

st.title("MLB Betr: Daily Model Output (LIVE API)")

st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("Loading games, lineups, and stats (may take 30s)..."):
    lineup_df, weather_df, games = get_full_lineups_and_stats()

if len(lineup_df) == 0:
    st.error("No posted lineups yet for today.")
    st.stop()

st.subheader("Today's Weather by Ballpark")
st.dataframe(weather_df)

st.subheader("Today's Games & Posted Lineups")
for g in games:
    team_players = lineup_df[lineup_df['Team'].isin([g['home'], g['away']])]
    if len(team_players) == 0:
        continue
    st.markdown(f"**{g['away']} @ {g['home']} ({g['venue']})**")
    st.dataframe(team_players[['Player', 'Team', 'Position', 'Batting Order']])

# Output for Player Props

props = {
    "HR": "Home Run % (per AB)",
    "Hits": "Hit % (per AB)",
    "TB": "Total Base % (per AB)",
    "KO": "Strikeout % (per AB)",
}

for prop, desc in props.items():
    st.header(f"{prop}: Top 15 Best Plays and Top 10 Longshots")
    outdf = rank_and_output(lineup_df, prop)
    st.subheader("Top 15 Best Plays")
    st.dataframe(outdf[outdf['Type'] == 'Best Play'].head(15)[
        ['Player', 'Team', 'Position', 'Batting Order', 'AB', prop, f"{prop} Win %"]
    ])
    st.subheader("Top 10 Longshot/Variance Plays")
    st.dataframe(outdf[outdf['Type'] == 'Longshot'].head(10)[
        ['Player', 'Team', 'Position', 'Batting Order', 'AB', prop, f"{prop} Win %"]
    ])
    st.download_button(
        label=f"Download {prop} Results as CSV",
        data=outdf.to_csv(index=False),
        file_name=f"mlb_betr_{prop.lower()}_output.csv",
        mime='text/csv'
    )

# Expand to show all player stats
with st.expander("Show all lineup players/stats"):
    st.dataframe(lineup_df)

st.info("All data pulled live from MLB StatsAPI. Weather data can be improved with a weather API by ballpark location.")

# -----
# To extend for Moneyline/Spread/O-U, pull game odds via an odds API, and add similar rankings/output for those.
