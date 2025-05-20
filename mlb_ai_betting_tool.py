import json
import re
import requests
import pandas as pd
import streamlit as st

# ── CONFIG ──────────────────────────────────────────────────────────────────────
PRIZEPICKS_URL = "https://app.prizepicks.com/projections"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ── SCRAPER ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_prizepicks_props() -> pd.DataFrame:
    # 1) GET the page
    resp = requests.get(PRIZEPICKS_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    
    # 2) Extract the JSON from the <script id="__NEXT_DATA__"> … </script>
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if not m:
        st.error("Couldn’t find Next.js data on PrizePicks page.")
        return pd.DataFrame()
    data = json.loads(m.group(1))
    
    # 3) Recursively locate the first “entries” array in that JSON
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
    
    # 4) Filter and massage only MLB props
    for e in entries:
        if e.get("sport", "").lower() != "mlb":
            continue
        
        # Try explicit player field, else parse from name
        player = (
            e.get("player", {}).get("name")
            or re.split(r"\s+(Over|Under)\s+", e.get("name", ""), maxsplit=1)[0]
        ).strip()
        prop_desc = e.get("name", "").strip()
        
        dec = e.get("oddsDecimal")
        ao  = e.get("oddsAmerican")
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
st.set_page_config(page_title="MLB Player Props (PrizePicks)", layout="wide")
st.title("⚾ Best-Value MLB Player Props (Top 25 by Implied Probability)")

with st.spinner("Loading PrizePicks projections…"):
    df = fetch_prizepicks_props()

if df.empty:
    st.error("No MLB player props found. PrizePicks may have changed their page structure.")
    st.stop()

df = df.sort_values("implied_prob", ascending=False).reset_index(drop=True)
top25 = df.head(25)

st.subheader("Top 25 Player Props")
st.dataframe(
    top25[["player", "prop", "american_odds", "decimal_odds", "implied_prob"]],
    height=600,
)

st.subheader("Player Implied Probability")
st.bar_chart(top25.set_index("player")["implied_prob"])

