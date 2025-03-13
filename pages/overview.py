import streamlit as st
import base64

CSS_FILE_PATH = "presentation/styles.css"


# Function to load CSS from an external file
def load_css(css_file):
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


# Set up the style and grab latest data
load_css(CSS_FILE_PATH)

# Show logo
image_base64 = get_base64_image("static/BugOutIndex200x200.png")

st.markdown(
    f"""
    <div style="display: flex; justify-content: center;">
        <img src="data:image/png;base64,{image_base64}" width="200">
    </div>
    """,
    unsafe_allow_html=True
)

# Display the title
st.markdown("<h1 style='text-align: center;'>About the BugOut Index</h1>", unsafe_allow_html=True)

st.markdown("""
## What is the BugOut Index?
The BugOut Index is a measure of societal stability, combining economic, crime, and other metrics into a single score.

## Score Interpretation
| **Score Range** | **Interpretation** |
|----------------|-------------------|
| **90–100** | High Stability (Low Risk) |
| **70–89**  | Moderate Stability (Warning Signs) |
| **50–69**  | Low Stability (Heightened Risk) |
| **<50**    | Critical Instability (Collapse Likely) |

## How it Works
The index is calculated daily, using real-time data sources like the **FRED API** and crime reports. 
""")
