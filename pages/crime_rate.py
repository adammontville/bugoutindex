import streamlit as st
import base64

CSS_FILE_PATH = "presentation/styles.css"
MARKDOWN_FILE_PATH = "static/markdown/crime_rate.md"


# Function to load CSS from an external file
def load_css(css_file):
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def load_markdown(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


# Set up the style and grab latest data
load_css(CSS_FILE_PATH)

# Show centered logo
image_base64 = get_base64_image("static/media/BugOutIndex200x200.png")
st.markdown(
    f"""
    <div style="display: flex; justify-content: center;">
        <img src="data:image/png;base64,{image_base64}" width="200">
    </div>
    """,
    unsafe_allow_html=True
)

# Load the Markdown file
markdown_content = load_markdown(MARKDOWN_FILE_PATH)

# Display the Markdown content
st.markdown(markdown_content, unsafe_allow_html=True)
