import re
import uuid
import requests
import pandas as pd
import streamlit as st

# ── CONFIG ──────────────────────────────────────────────────────────────────────
API_URL = "https://api.prizepicks.com/projections"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://app.prizepicks.com/",
    # A random device-ID so Cloudflare sees it as a “real” session
    "X-Device-ID": str(uuid.uuid4()),
}

# PrizePicks’ internal league IDs: NBA=7, NHL=8, so MLB is 6 :contentReference[oaicite:0]{index=0}
PARAMS = {
    "league_id":      6,
    "per_page":       500,
    "single_stat":    "true",
    "projection_type_id": 1,
    "game_mode":      "pickem",
}


@st.cache_data(ttl=3600)
def fetch_prizepicks_mlb_props() -> pd.DataFrame:
    """Fetch raw MLB props from PrizePicks API and return a DataFrame."""
    resp = requests.get(API_URL, params=PARAMS, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    records = []
    for e in data:
        attrs = e.get("attributes", {})
        desc  = attrs.get("description", "").strip()
        # parse "Player Over/Under X.Y"
        m = re.match(r"^(.*?)\s+(Over|Under)\s+(.+)$", desc)
        if m:
            player    = m.group(1)
            prop_desc = f"{m.group(2)} {m.group(3)}"
        else:
            player    = attrs.get("name", desc)
            prop_desc = desc

        # odds: PrizePicks sometimes gives decimal directly, or you can use American
        dec = attrs.get("oddsDecimal")
        ao  = attrs.get("oddsAmerican")
        if dec is None and ao is not None:
            dec = (ao / 100 + 1) if ao > 0 else (100 / abs(ao) + 1)
        if dec is None:
            continue

        implied = round(1 / dec, 3)
        records.append({
            "player":        player,
            "prop":          prop_desc,
            "american_odds": ao,
            "decimal_odds":  round(dec, 2),
            "implied_prob":  implied,
        })

    return pd.DataFrame.from_records(records)


# ── STREAMLIT UI ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="MLB PrizePicks Props", layout="wide")
st.title("⚾ Best-Value MLB Player Props (PrizePicks)")

with st.spinner("Loading PrizePicks MLB props…"):
    df = fetch_prizepicks_mlb_props()

if df.empty:
    st.error(
        "No MLB props found. PrizePicks may have changed their API or your league_id is off."
    )
    st.stop()

# sort by *lowest* implied prob (i.e. largest edge) or flip ascending if you prefer highest payout
df = df.sort_values("implied_prob", ascending=True).reset_index(drop=True)
top25 = df.head(25)

st.subheader("Top 25 Props by Implied Probability")
st.dataframe(
    top25[["player", "prop", "american_odds", "decimal_odds", "implied_prob"]],
    height=600,
)

st.subheader("Implied Probability Chart (Lower is Better Value)")
st.bar_chart(top25.set_index("player")["implied_prob"])
