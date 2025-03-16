import streamlit as st
import pandas as pd
import ast  # Converts string representations of dictionaries into actual dictionaries
import base64
from processing.scoring_v1 import calculate_category_score

CSS_FILE_PATH = "presentation/styles.css"

# Define metric ranges (same as used in normalization)
metric_ranges = {
    "inflation_rate": (0, 10),
    "incident_rate": (1000, 4000),
    "unemployment_rate": (0, 20),
    "debt_to_gdp_ratio": (0, 200),
    "homelessness_rate": (0, 1),
    "trust_in_government": (0, 80),
}

# Define weights for BOI calculation
weights = {
    "inflation_rate": 0.15,
    "incident_rate": 0.12,
    "unemployment_rate": 0.12,
    "debt_to_gdp_ratio": 0.09,
    "homelessness_rate": 0.09,
    "trust_in_government": 0.09,
}


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


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


load_css(CSS_FILE_PATH)

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


def extract_numeric(value):
    """Extracts the numeric value from a string or dictionary-like entry."""
    try:
        if isinstance(value, str) and value.startswith("{"):
            parsed_value = ast.literal_eval(value)  # Convert stringified dict
            return float(list(parsed_value.values())[0])  # Extract first numeric value
        return float(value)  # If already numeric, return as float
    except Exception as e:
        st.error(f"Error parsing value: {value} - {e}")
        return None  # Default fallback if parsing fails


def load_latest_values():
    """Loads the latest values from historical_bugout_index.csv"""
    csv_path = "data/historical_bugout_index.csv"
    try:
        df = pd.read_csv(csv_path)

        # Ensure columns are stripped of spaces and formatted correctly
        df.columns = df.columns.str.strip().str.lower()

        if df.empty:
            raise ValueError("Historical CSV is empty")

        latest_entry = df.iloc[-1]  # Get the most recent row

        # Ensure all values are extracted correctly
        return {
            metric: extract_numeric(latest_entry[metric]) for metric in metric_ranges.keys()
        }
    except KeyError as e:
        st.error(f"Column missing: {e}")
    except Exception as e:
        st.error(f"Error loading historical data: {e}")
        return {metric: (min_val + max_val) / 2 for metric, (min_val, max_val) in metric_ranges.items()}  # Defaults to mid-range if error


# Load latest values from CSV
latest_values = load_latest_values()

# Page title
st.title("BugOut Index Simulator")

# Organize sliders into columns for better layout
col1, col2 = st.columns(2)

# Create sliders in main content area
user_inputs = {}
with col1:
    for metric in list(metric_ranges.keys())[:3]:  # First three metrics in column 1
        user_inputs[metric] = st.slider(
            label=metric.replace("_", " ").title(),
            min_value=float(metric_ranges[metric][0]),
            max_value=float(metric_ranges[metric][1]),
            value=latest_values[metric],
            step=(metric_ranges[metric][1] - metric_ranges[metric][0]) / 100
        )

with col2:
    for metric in list(metric_ranges.keys())[3:]:  # Last three metrics in column 2
        user_inputs[metric] = st.slider(
            label=metric.replace("_", " ").title(),
            min_value=float(metric_ranges[metric][0]),
            max_value=float(metric_ranges[metric][1]),
            value=latest_values[metric],
            step=(metric_ranges[metric][1] - metric_ranges[metric][0]) / 100
        )


# Calculate the BugOut Index dynamically
boi_score = calculate_category_score(user_inputs, metric_ranges, weights)

stability_class = get_stability_class(boi_score)

# Display BOI with color indicator
st.markdown(f'<div class="{stability_class}">Simulated BugOut Index Score: {boi_score:.2f}</div>',
            unsafe_allow_html=True)

st.write("Use the sliders above to adjust the metrics and see how the BugOut Index changes dynamically.")

st.markdown(
    "\n\n<div class='footnote'>*This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.*</div>",
    unsafe_allow_html=True
)
