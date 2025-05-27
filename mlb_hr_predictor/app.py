import streamlit as st
import pandas as pd

st.title("MLB Daily Home Run Value Bets")

df = pd.read_csv("mlb_hr_predictor/data/todays_predictions.csv")
st.write("Top HR value picks (model vs. Vegas):")
st.dataframe(df[['player','team','pred_hr_prob','vegas_prob','edge']].head(15))
st.write("All predictions:")
st.dataframe(df)
