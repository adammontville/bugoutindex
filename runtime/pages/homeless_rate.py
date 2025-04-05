import streamlit as st
from presentation.display_logo import display_logo

CSS_FILE_PATH = "presentation/styles.css"
MARKDOWN_FILE_PATH = "static/markdown/homeless_rate" \
                     ".md"


# Function to load CSS from an external file
def load_css(css_file):
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def load_markdown(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()



# Set up the style and grab latest data
load_css(CSS_FILE_PATH)

display_logo()

st.markdown("<h1 style='text-align: center;'>Homelessness Rate</h1>", unsafe_allow_html=True)

# Load the Markdown file
markdown_content = load_markdown(MARKDOWN_FILE_PATH)

# Display the Markdown content
st.markdown(markdown_content, unsafe_allow_html=True)
