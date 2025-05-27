import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# --- 1. Scraper Functions ---

def get_rotowire_lineups():
    """Scrape confirmed lineups from Rotowire. Return empty DataFrame if none."""
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    games = soup.find_all("div", class_="lineup is-mlb")
    lineup_rows = []
    for game in games:
        teams = [x.text.strip() for x in game.find_all('span', class_='lineup__abbr')]
        for lineup_side in game.find_all('div', class_='lineup__list'):
            status = game.find('div', class_='lineup__status').text.strip()
            for spot in lineup_side.find_all('li', class_='lineup__player'):
                batter = spot.find('a').text.strip()
                order = spot.find('span', class_='lineup__order').text.strip()
                lineup_rows.append({
                    'Team': teams[0] if len(lineup_rows) < 9 else teams[1],  # crude, works for 9-man lineups
                    'Batter': batter,
                    'Order': int(order),
                    'Lineup Status': status
                })
    df = pd.DataFrame(lineup_rows)
    return df

def get_fangraphs_projected_lineups():
    """
    Scrapes projected lineups from Fangraphs for today. 
    Fangraphs has all teams listed in a single table.
    """
    url = "https://www.fangraphs.com/projections.aspx?pos=all"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    # Fangraphs does not have a simple lineup list. Use the depth chart/projections table as fallback.
    table = soup.find('table', {'id': 'ProjectionBoard1_dgProjection'})
    headers = [th.text.strip() for th in table.find_all('th')]
    data = []
    for row in table.find_all('tr')[1:]:
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) == len(headers):
            data.append(dict(zip(headers, cols)))
    df = pd.DataFrame(data)
    if not df.empty:
        # Get top 9 players for each team by PA projection
        df['PA'] = pd.to_numeric(df['PA'], errors='coerce')
        df['Order'] = df.groupby('Team')['PA'].rank(method='first', ascending=False)
        df = df[df['Order'] <= 9]
        df['Order'] = df['Order'].astype(int)
        df['Lineup Status'] = "Projected (Fangraphs)"
        df.rename(columns={'Name': 'Batter'}, inplace=True)
        df = df[['Team', 'Batter', 'Order', 'Lineup Status']]
    return df

def get_daily_lineups():
    """Try Rotowire, fallback to Fangraphs."""
    st.info("Trying to pull lineups from Rotowire...")
    rw = get_rotowire_lineups()
    if not rw.empty:
        st.success("Loaded official/confirmed lineups from Rotowire.")
        return rw
    st.warning("No official lineups yet. Pulling projected lineups from Fangraphs.")
    fg = get_fangraphs_projected_lineups()
    if not fg.empty:
        st.success("Loaded projected lineups from Fangraphs.")
        return fg
    st.error("No lineups available from Rotowire or Fangraphs!")
    return pd.DataFrame()

# -- Weather example, update with real API or scraping logic
def get_daily_weather():
    # Dummy: Replace with real weather API for each ballpark
    return pd.DataFrame({
        'Ballpark': ['Yankee Stadium', 'Truist Park', 'Dodger Stadium'],
        'Temperature (F)': [78, 85, 75],
        'Wind': ['8 mph Out', '5 mph In', '2 mph L to R'],
        'Conditions': ['Sunny', 'Cloudy', 'Clear']
    })

# -- Your historic/model/stat data
def get_historic_data():
    # Replace with API/CSV/historical database pull!
    return pd.DataFrame({
        'Batter': ['Aaron Judge', 'Ronald Acuna Jr.', 'Shohei Ohtani'],
        'HR %': [0.07, 0.05, 0.06],
        'TB %': [0.45, 0.38, 0.41],
        'Hits %': [0.28, 0.30, 0.27]
    })

# --- MODEL LOGIC (update to your custom logic) ---
def run_mlb_betr_model(lineups, weather, historic_data):
    merged = pd.merge(lineups, historic_data, on='Batter', how='left')
    # Basic demo: average HR%, TB%, Hits% (replace with your true model!)
    merged['Win %'] = (merged['HR %'].fillna(0) + merged['TB %'].fillna(0) + merged['Hits %'].fillna(0)) / 3 + 0.5
    merged = merged.sort_values('Win %', ascending=False).reset_index(drop=True)
    # Top 15 best plays
    merged['Type'] = 'Other'
    merged.loc[merged.index < 15, 'Type'] = 'Best Play'
    merged.loc[(merged.index >= 15) & (merged.index < 25), 'Type'] = 'Longshot'
    return merged

# --- STREAMLIT UI ---
st.title("MLB Betr: Daily Model Output with Projected Lineups")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("Loading data..."):
    lineups = get_daily_lineups()
    weather = get_daily_weather()
    historic_data = get_historic_data()
    output_df = run_mlb_betr_model(lineups, weather, historic_data)

if lineups.empty:
    st.error("No lineups could be loaded from any source.")
else:
    st.subheader("Today's Starting Lineups (Official/Projected)")
    st.dataframe(lineups)

    st.subheader("Today's Weather by Ballpark")
    st.dataframe(weather)

    st.header("Top 15 Best Plays (by Win %)")
    best_plays = output_df[output_df['Type'] == 'Best Play'].head(15).copy()
    st.dataframe(best_plays)

    st.header("Top 10 Longshot/Variance Plays (by Win %)")
    longshots = output_df[output_df['Type'] == 'Longshot'].head(10).copy()
    st.dataframe(longshots)

    st.download_button(
        label="Download All Results as CSV",
        data=output_df.to_csv(index=False),
        file_name='mlb_betr_model_output.csv',
        mime='text/csv'
    )

    with st.expander("Show all players evaluated"):
        st.dataframe(output_df)
