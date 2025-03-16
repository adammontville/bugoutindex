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
import base64


# File path to historical data
CSV_FILE_PATH = "data/historical_bugout_index.csv"
CSS_FILE_PATH = "presentation/styles.css"


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


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


def get_stability_class(score):
    if score >= 70:
        return "stable"
    elif 55 <= score < 70:
        return "moderate"
    elif 40 <= score < 55:
        return "severe"
    else:
        return "critical"


# Function to load CSS from an external file
def load_css(css_file):
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Set up the style and grab latest data
load_css(CSS_FILE_PATH)
latest_data = load_latest_bugout_index()

# Show logo
image_base64 = get_base64_image("static/media/BugOutIndex200x200.png")

st.markdown(
    f"""
    <div style="display: flex; justify-content: center;">
        <img src="data:image/png;base64,{image_base64}" width="200">
    </div>
    """,
    unsafe_allow_html=True
)

# Display the title
st.markdown("<h1 style='text-align: center;'>BugOut Index Dashboard</h1>", unsafe_allow_html=True)

if latest_data is not None:
    stability_class = get_stability_class(latest_data["bugout_index"])

    # Display BOI with color indicator
    st.markdown(f'<div class="{stability_class}">BugOut Index Score: {latest_data["bugout_index"]:.2f}</div>',
                unsafe_allow_html=True)
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

    st.markdown(
        """
        ### Stability Matrix
        | **Score Range** | **Interpretation** |
        |---------------|--------------------|
        | **70-100** | High Stability (Low Risk) |
        | **55–69** | Moderate Stability (Warning Signs) |
        | **40–54** | Low Stability (Heightened Risk) |
        | **<40** | Critical Instability (Collapse Likely) |
        """
    )
else:
    st.error("No historical data found. Run the index calculation first.")

st.markdown(
    "\n\n<div class='footnote'>*This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.*</div>",
    unsafe_allow_html=True
)
