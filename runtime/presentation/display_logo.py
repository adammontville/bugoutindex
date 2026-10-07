# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Logo for the optional viewer. Color comes from the published snapshot."""
import base64
import streamlit as st
from processing.formula import stability_css_class as get_stability_class
from viewer_io import load_published_snapshot


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


def display_logo():
    snapshot = load_published_snapshot()
    if not snapshot or snapshot.get("bugout_index") is None:
        return
    stability_class = get_stability_class(snapshot["bugout_index"])
    image_base64 = get_base64_image(f"static/media/BugOutIndex200x200-{stability_class}.png")
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center;">
            <img src="data:image/png;base64,{image_base64}" width="200">
        </div>
        """,
        unsafe_allow_html=True,
    )
