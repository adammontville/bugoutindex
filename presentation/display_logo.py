import base64
import pandas as pd
import streamlit as st

CSV_FILE_PATH = "data/historical_bugout_index.csv"


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


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Display Logo
def display_logo():

    latest_data = load_latest_bugout_index()
    if latest_data is not None:
        stability_class = get_stability_class(latest_data["bugout_index"])
        image_base64 = get_base64_image(f"static/media/BugOutIndex200x200-{stability_class}.png")

        st.markdown(
            f"""
            <div style="display: flex; justify-content: center;">
                <img src="data:image/png;base64,{image_base64}" width="200">
            </div>
            """,
            unsafe_allow_html=True
)