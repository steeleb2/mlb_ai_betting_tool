import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime

def get_lineups():
    # RotoWire's MLB daily lineups (public)
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    tables = soup.find_all("div", class_="lineup is-mlb")
    lineups = []
    for table in tables:
        try:
            team = table.find("div", class_="lineup__abbr").text.strip()
            players = table.find_all("a", class_="lineup__player-link")
            for p in players:
                name = p.text.strip()
                pos = p.parent.find("span", class_="lineup__pos").text.strip()
                lineups.append({'team': team, 'player': name, 'pos': pos})
        except Exception:
            continue
    df = pd.DataFrame(lineups)
    df.to_csv("mlb_hr_predictor/data/todays_lineups.csv", index=False)

def get_park_weather():
    # Fetch today's games and weather from MLB API
    games_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={datetime.date.today()}"
    games = requests.get(games_url).json()['dates'][0]['games']
    rows = []
    for g in games:
        park = g['venue']['name']
        home = g['teams']['home']['team']['name']
        away = g['teams']['away']['team']['name']
        game_time = g['gameDate']
        rows.append({'park': park, 'home': home, 'away': away, 'game_time': game_time})
    pd.DataFrame(rows).to_csv("mlb_hr_predictor/data/todays_games.csv", index=False)

def get_hr_odds():
    # Example: Scrape FanDuel HR odds (public, structure may change)
    url = "https://sportsbook.fanduel.com/navigation/mlb"
    # This is often dynamic (JS) -- you might need to use oddsportal or csv upload here.
    # For demo: Just create a dummy odds file.
    pd.DataFrame({
        'player': ['Aaron Judge', 'Giancarlo Stanton', 'Shohei Ohtani'],
        'team': ['Yankees', 'Yankees', 'Dodgers'],
        'hr_odds': [3.2, 4.0, 2.8],  # decimal odds
    }).to_csv("mlb_hr_predictor/data/hr_odds.csv", index=False)

if __name__ == "__main__":
    get_lineups()
    get_park_weather()
    get_hr_odds()
    print("Today's data updated.")
