import json
import re
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

# ── CONFIG ──────────────────────────────────────────────────────────────────────
PRIZEPICKS_URL = "https://app.prizepicks.com/projections"

HEADERS = {
    # PrizePicks sometimes blocks non-browsers; a common UA helps
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ── SCRAPER ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_prizepicks_props() -> pd.DataFrame:
    """
    Scrape PrizePicks projections page, extract the __NEXT_DATA__ JSON,
    locate the 'entries' list, then filter for MLB props and return
    a DataFrame with player, prop description, odds, and implied probability.
    """
    # 1) GET the page
    resp = requests.get(PRIZEPICKS_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    # 2) Parse out the Next.js JSON blob
    soup   = BeautifulSoup(resp.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    data   = json.loads(script.string)

    # 3) Recursively find the first "entries": [...]
    def find_entries(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "entries" and isinstance(v, list):
                    return v
                sub = find_entries(v)
                if sub:
                    return sub
        elif isinstance(obj, list):
            for item in obj:
                sub = find_entries(item)
                if sub:
                    return sub
        return None

    entries = find_entries(data) or []
    records = []

    # 4) Pull out only MLB entries
    for e in entries:
        if e.get("sport", "").lower() != "mlb":
            continue

        # Player name: try explicit field, else parse from the prop name
        player = (
            e.get("player", {}).get("name")
            or re.split(r"\s+(Over|Under)\s+", e.get("name", ""), maxsplit=1)[0]
        ).strip()

        prop_desc = e.get("name", "").strip()

        # Odds: PrizePicks usually provides decimal directly
        dec = e.get("oddsDecimal")
        ao  = e.get("oddsAmerican")
        if dec is None and ao is not None:
            # convert American → decimal
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


# ── STREAMLIT APP ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="MLB Player Props (PrizePicks)", layout="wide")
st.title("⚾ Best-Value MLB Player Props (Top 25 by Implied Probability)")

with st.spinner("Loading PrizePicks projections…"):
    df = fetch_prizepicks_props()

if df.empty:
    st.error("No MLB player props found. PrizePicks may have changed their page structure.")
    st.stop()

# Sort descending by implied probability (largest chance → highest value)
df = df.sort_values("implied_prob", ascending=False).reset_index(drop=True)
top25 = df.head(25)

st.subheader("Top 25 Player Props")
st.dataframe(
    top25[["player", "prop", "american_odds", "decimal_odds", "implied_prob"]],
    height=600,
)

st.subheader("Player Implied Probability")
st.bar_chart(top25.set_index("player")["implied_prob"])

