import streamlit as st
from presentation.display_logo import display_logo
from processing.formula import (
    METRIC_RANGES as metric_ranges,
    calculate_category_score,
    stability_css_class as get_stability_class,
)
from viewer_io import load_published_snapshot

CSS_FILE_PATH = "presentation/styles.css"


# Function to load CSS from an external file
def load_css(css_file):
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css(CSS_FILE_PATH)
display_logo()

def _midpoint(metric):
    low, high = metric_ranges[metric]
    return (low + high) / 2


def load_latest_values():
    """Slider defaults from the published snapshot. Does not write the site."""
    snapshot = load_published_snapshot()
    metrics = (snapshot or {}).get("metrics") or {}
    values = {}
    for metric, (low, high) in metric_ranges.items():
        raw = (metrics.get(metric) or {}).get("raw")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            values[metric] = min(float(high), max(float(low), float(raw)))
        else:
            values[metric] = _midpoint(metric)
    return values


# Load latest values from CSV
latest_values = load_latest_values()

# Display the title
st.markdown("<h1 style='text-align: center;'>BugOut Index Simulator</h1>", unsafe_allow_html=True)
st.caption(
    "Local what-if on the published raw values. Moving a slider does not "
    "change the live score and does not write docs/."
)

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
            step=(metric_ranges[metric][1] - metric_ranges[metric][0]) / 100,
            key=metric,
        )

with col2:
    for metric in list(metric_ranges.keys())[3:]:  # Last three metrics in column 2
        user_inputs[metric] = st.slider(
            label=metric.replace("_", " ").title(),
            min_value=float(metric_ranges[metric][0]),
            max_value=float(metric_ranges[metric][1]),
            value=latest_values[metric],
            step=(metric_ranges[metric][1] - metric_ranges[metric][0]) / 100,
            key=metric,
        )


# Calculate the BugOut Index dynamically
boi_score = calculate_category_score(user_inputs)

stability_class = get_stability_class(boi_score)

# Display BOI with color indicator
st.markdown(f'<div class="{stability_class}">Simulated BugOut Index Score: {boi_score:.2f}</div>',
            unsafe_allow_html=True)

st.write("Use the sliders above to adjust the metrics and see how the BugOut Index changes dynamically.")

st.markdown(
    "\n\n<div class='footnote'>*This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.*</div>",
    unsafe_allow_html=True
)
