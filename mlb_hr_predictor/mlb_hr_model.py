import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os

# Load historical HR data (export from Baseball Savant for best results)
if not os.path.exists('mlb_hr_predictor/data/historical.csv'):
    # Download sample (real data): https://baseballsavant.mlb.com/statcast_search
    raise FileNotFoundError("Please download and place historical.csv (Statcast batted ball data) in data folder.")

df = pd.read_csv('mlb_hr_predictor/data/historical.csv')

# Basic feature engineering (expand as needed)
df['is_hr'] = (df['events'] == 'home_run').astype(int)
df['batter_power'] = df['launch_speed'].fillna(85)
df['batter_la'] = df['launch_angle'].fillna(12)
df['park'] = df['home_team'].fillna('Yankee Stadium')
park_factors = pd.read_csv('mlb_hr_predictor/data/park_factors.csv')

df = df.merge(park_factors, how='left', left_on='park', right_on='park').fillna(1.0)

features = ['batter_power', 'batter_la', 'hr_factor']
X = df[features]
y = df['is_hr']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
model.fit(X_train, y_train)
joblib.dump(model, "mlb_hr_predictor/mlb_hr_rf.joblib")
print(f"Train: {model.score(X_train, y_train):.4f}, Test: {model.score(X_test, y_test):.4f}")

def predict_today():
    model = joblib.load("mlb_hr_predictor/mlb_hr_rf.joblib")
    # Minimal features for demo
    df_lineup = pd.read_csv("mlb_hr_predictor/data/todays_lineups.csv")
    parks = pd.read_csv("mlb_hr_predictor/data/todays_games.csv")
    odds = pd.read_csv("mlb_hr_predictor/data/hr_odds.csv")
    pf = pd.read_csv('mlb_hr_predictor/data/park_factors.csv')
    # Merge in park/park_factor by team (simplified)
    df_lineup = df_lineup.merge(parks[['home','park']], left_on='team', right_on='home', how='left')
    df_lineup = df_lineup.merge(pf, how='left', on='park').fillna(1.0)
    # For demo, just use mean values or add your own stat sources for better predictions
    df_lineup['batter_power'] = 90
    df_lineup['batter_la'] = 15
    X_pred = df_lineup[['batter_power','batter_la','hr_factor']]
    df_lineup['pred_hr_prob'] = model.predict_proba(X_pred)[:,1]
    # Merge odds
    df_lineup = df_lineup.merge(odds, on=['player','team'], how='left')
    df_lineup['vegas_prob'] = 1 / df_lineup['hr_odds']
    df_lineup['edge'] = df_lineup['pred_hr_prob'] - df_lineup['vegas_prob']
    df_lineup.sort_values('edge', ascending=False, inplace=True)
    df_lineup.to_csv('mlb_hr_predictor/data/todays_predictions.csv', index=False)
    print(df_lineup[['player','team','pred_hr_prob','vegas_prob','edge']].head(10))

if __name__ == "__main__":
    predict_today()
