# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com
import pandas as pd
import streamlit as st
import ast

# File path to historical data
CSV_FILE_PATH = "data/historical_bugout_index.csv"


# Function to load the latest BugOut Index score
@st.cache_data
def load_latest_bugout_index():
    try:
        df = pd.read_csv(CSV_FILE_PATH, parse_dates=["date"])
        if df.empty:
            return None
        latest_entry = df.sort_values(by="date", ascending=False).iloc[0]  # Get the latest row
        return latest_entry
    except FileNotFoundError:
        return None


# Load latest data
latest_data = load_latest_bugout_index()

# Streamlit UI
st.title("BugOut Index Dashboard")

if latest_data is not None:
    #st.header(f"📅 Date: {latest_data['date'].strftime('%Y-%m-%d')}")
    st.subheader(f"BugOut Index as of {latest_data['date'].strftime('%Y-%m-%d')}: "
                 f"**{latest_data['bugout_index']:.2f}**")

    st.write("### Breakdown of Latest Metrics:")

    # Display each metric
    for column in latest_data.index:
        if column not in ["date", "bugout_index"]:
            try:
                # Convert string to dictionary if it's stored as a string representation
                value = latest_data[column]
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    value = ast.literal_eval(value)  # Convert to real dictionary

                # Extract numerical value from dictionary or convert directly
                if isinstance(value, dict):
                    value = float(list(value.values())[0])  # Extract the first numeric value
                else:
                    value = float(value)  # Convert to float if it's already numeric

                st.write(f"**{column.replace('_', ' ').title()}**: {value:.2f}")
            except (ValueError, SyntaxError):
                st.write(f"**{column.replace('_', ' ').title()}**: {latest_data[column]}")  # Fallback

else:
    st.error("No historical data found. Run the index calculation first.")

st.write("\nThis product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.")