import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="MLB Betr Model", layout="wide")

# -------------------
# 1. DATA SCRAPING FUNCTIONS
# -------------------

def get_rotowire_lineups():
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "lxml")

        games = soup.find_all("div", class_="lineup__card")
        all_lineups = []
        for game in games:
            teams = [x.text.strip() for x in game.find_all("div", class_="lineup__abbr")]
            status = game.find("span", class_="lineup__status").text.strip() if game.find("span", class_="lineup__status") else "Projected"

            for i, lineup in enumerate(game.find_all("ul", class_="lineup__list")):
                batters = [b.text.strip() for b in lineup.find_all("a", class_="lineup__player-link")]
                for order, batter in enumerate(batters, 1):
                    all_lineups.append({
                        "Team": teams[i] if i < len(teams) else f"Team{i+1}",
                        "Batter": batter,
                        "Order": order,
                        "Lineup Status": status
                    })
        if not all_lineups:
            return pd.DataFrame(), "No projected or confirmed lineups posted yet. Try again later."
        return pd.DataFrame(all_lineups), "Lineups loaded from Rotowire"
    except Exception as e:
        return pd.DataFrame(), f"Error loading lineups: {e}"

def get_daily_weather():
    # Dummy example, replace with real API or data as needed
    return pd.DataFrame({
        'Ballpark': ['Yankee Stadium', 'Truist Park', 'Dodger Stadium'],
        'Temperature (F)': [78, 85, 75],
        'Wind': ['8 mph Out', '5 mph In', '2 mph L to R'],
        'Conditions': ['Sunny', 'Cloudy', 'Clear']
    })

def get_daily_matchups():
    # Dummy example, replace with real API or data as needed
    return pd.DataFrame({
        'Home': ['Yankees', 'Braves', 'Dodgers'],
        'Away': ['Red Sox', 'Phillies', 'Padres'],
        'Home SP': ['Gerrit Cole', 'Max Fried', 'Tyler Glasnow'],
        'Away SP': ['Chris Sale', 'Zack Wheeler', 'Yu Darvish']
    })

def get_historic_data():
    # Dummy example, replace with real data or API
    return pd.DataFrame({
        'Batter': ['Aaron Judge', 'Ronald Acuna Jr.', 'Shohei Ohtani'],
        'HR %': [0.07, 0.05, 0.06],
        'TB %': [0.45, 0.38, 0.41],
        'Hits %': [0.28, 0.30, 0.27]
    })

# -------------------
# 2. MODEL LOGIC
# -------------------

def run_mlb_betr_model(lineups, weather, matchups, historic_data):
    # Merge lineups with historic data
    merged = pd.merge(lineups, historic_data, left_on="Batter", right_on="Batter", how="left")

    # Example model logic: Win% is avg of 3 stats, plus a small boost for confirmed lineups
    merged["Win %"] = (merged['HR %'].fillna(0) + merged['TB %'].fillna(0) + merged['Hits %'].fillna(0)) / 3
    merged["Win %"] += merged["Lineup Status"].apply(lambda x: 0.10 if "Confirmed" in x else 0.03)

    # Sort and classify
    merged = merged.sort_values('Win %', ascending=False).reset_index(drop=True)
    merged['Type'] = ["Best Play"]*15 + ["Longshot"]*10 + ["Other"]*(len(merged)-25) if len(merged) > 25 else (
        ["Best Play"]*min(15,len(merged)) + ["Longshot"]*max(0, len(merged)-15)
    )
    return merged

# -------------------
# 3. STREAMLIT UI
# -------------------

st.title("MLB Betr: Daily Model Output")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("Pulling latest lineups from Rotowire..."):
    lineups_df, msg = get_rotowire_lineups()
    st.info(msg)
    if lineups_df.empty:
        st.warning("No projected or confirmed lineups posted yet. Try again later today.")
        st.stop()

with st.spinner("Loading weather, matchups, and historical data..."):
    weather = get_daily_weather()
    matchups = get_daily_matchups()
    historic_data = get_historic_data()
    output_df = run_mlb_betr_model(lineups_df, weather, matchups, historic_data)

st.subheader("Today's Weather by Ballpark")
st.dataframe(weather)

st.subheader("Today's Pitching Matchups")
st.dataframe(matchups)

st.header("Today's Starting Lineups")
for team in lineups_df["Team"].unique():
    st.markdown(f"**{team} Lineup**")
    st.dataframe(lineups_df[lineups_df["Team"] == team][["Order", "Batter", "Lineup Status"]].set_index("Order"))

st.header("Top 15 Best Plays (by Win %)")
best_plays = output_df[output_df['Type'] == 'Best Play'].head(15).copy()
st.dataframe(best_plays[["Batter", "Team", "Order", "Lineup Status", "Win %"]])

st.header("Top 10 Longshot/Variance Plays (by Win %)")
longshots = output_df[output_df['Type'] == 'Longshot'].head(10).copy()
st.dataframe(longshots[["Batter", "Team", "Order", "Lineup Status", "Win %"]])

# Optional: Download button for CSV
st.download_button(
    label="Download All Results as CSV",
    data=output_df.to_csv(index=False),
    file_name='mlb_betr_model_output.csv',
    mime='text/csv'
)

# Expand to show all players
with st.expander("Show all players evaluated"):
    st.dataframe(output_df)

st.info("Customize data sources and model logic by editing this script.")

