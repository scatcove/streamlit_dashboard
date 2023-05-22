import streamlit as st
from pymongo import MongoClient
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime

# from dotenv import load_dotenv
# import os

# load_dotenv()

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.sidebar.header("Dashboard `version 2`")

st.sidebar.subheader("Heat map parameter")
time_hist_color = st.sidebar.selectbox("Color by", ("temp_min", "temp_max"))

st.sidebar.subheader("Donut chart parameter")
donut_theta = st.sidebar.selectbox("Select data", ("q2", "q3"))

st.sidebar.subheader("Line chart parameters")
plot_data = st.sidebar.multiselect(
    "Select data", ["temp_min", "temp_max"], ["temp_min", "temp_max"]
)
plot_height = st.sidebar.slider("Specify plot height", 200, 500, 250)

# Connect to MongoDB

MONGO_URL = st.secrets["MONGO_URL"]
client = MongoClient(MONGO_URL)
db = client.BettingData
collection = db.Trades

# Fetch data from MongoDB
data = collection.find()
data = pd.DataFrame(list(data))

# Get placed trades and not placed trades
trades_p = data[data["placed"] == "placed"]
trades_np = data[data["placed"] != "placed"]

# Creating a three column layout
col1, col2, col3 = st.columns(3)

# Plot balance over time for last 20 placed trades in the first column
col1.header("Balance Over Time")
col1.line_chart(trades_p["balance"])

# Table of Last 20 Placed and Not Placed Trades in the second column

col2.header("10 Most Recent Trades")
col2.table(
    trades_p[["win_odds", "balance", "best_lay_price", "stake_size", "bsp"]].tail(10)
)
# col2.header("Not Placed Trades")
# col2.table(trades_np)

# Histogram of EV's (assuming a column "EV" exists) in the third column
col3.header("Histogram of EV's")
trades_evs = trades_p[trades_p["bsp"] != 0.0]
trades_evs = trades_evs[trades_evs["bsp"].notnull()]

for index, row in trades_evs.iterrows():
    trades_evs.loc[index, "ev"] = float(row.win_odds) / float(row.bsp)

missed_evs = trades_np[trades_np["bsp"] != 0.0]
missed_evs = missed_evs[missed_evs["bsp"].notnull()]
# filter out duplicates of market ids
missed_evs = missed_evs.drop_duplicates(subset=["market_id"])

for index, row in missed_evs.iterrows():
    missed_evs.loc[index, "ev"] = float(row.win_odds) / float(row.bsp)

figure = plt.figure(figsize=(10, 5))
sns.distplot(trades_evs["ev"], label="Placed")
sns.distplot(missed_evs["ev"], label="Missed")

col3.pyplot(figure)

col4, col5, col6 = st.columns(3)

## Add EV for all orders placed within past 24 hours from now
now = datetime.datetime.utcnow()
trades_p["timestamp"] = pd.to_datetime(trades_p["timestamp"])
last_24 = trades_p.loc[trades_p["timestamp"] > now - datetime.timedelta(days=1)].copy()

# Display Mean Forecasted EV from Past 24 hours
last_24["EV"] = last_24["win_odds"] / last_24["best_lay_price"]

# Now compute actual EV with bsp
# last_24["actual_ev"] = last_24["win_odds"] / last_24["bsp"]
day_evmean = round(last_24["EV"].mean(), 3)

col4.header(f"Mean Forecasted EV for Past 24 hours: {day_evmean}")

## Calculate all time EV
col5.header(f"All Time EV of Trades Placed: {trades_evs['ev'].mean()}")

col6.header(f"All Time EV of Trades Missed: {missed_evs['ev'].mean()}")

## Profit Loss

col7, col8, col9 = st.columns(3)

## use trades_evs to determine profit/loss
col7.header(
    f"All time Profit/Loss for Placed Bets: {sum(trades_evs['return'].astype(float)) - sum(trades_evs['stake_size'].astype(float))}"
)

# suppose stake size of 20 for all missed bets
# now compute return based on win being true or false
missed_evs["stake_size"] = 20
missed_evs["return"] = missed_evs["win"].apply(
    lambda x: 0 if x == "False" else missed_evs["win_odds"].astype(float) * 20
)

col8.header(
    f"All time Profit/Loss for Missed Bets with Constant Bet Size of 20: {sum(missed_evs['return'].astype(float)) - sum(missed_evs['stake_size'].astype(float))}"
)


# Display the full data at the end (not in a column)
# st.write(data)
