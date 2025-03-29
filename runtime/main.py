# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com
import streamlit as st
import os

st.set_page_config(
    page_title="BugOut Index",
    page_icon="static/media/favicon.ico"
)

# CSS for hamburger menu and Deploy button
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}  /* Hamburger menu */
    </style>
""", unsafe_allow_html=True)

# Set toolbar mode based on environment
env = os.getenv("STREAMLIT_ENV", "dev")  # Default to "dev"
toolbar_mode = "viewer" if env == "prod" else "auto"
st.set_option("client.toolbarMode", toolbar_mode)

# Inject custom CSS for navigation
st.markdown("""
    <style>
    /* Make category headings larger, bold, and spaced out */
    header[data-testid="stNavSectionHeader"] {
        font-size: 1.3em !important;  /* Adjust size for categories */
        font-weight: bold !important; /* Make category labels stand out */
        margin-top: 12px !important;  /* Add spacing between categories */
    }

    /* Keep individual page links at default size */
    a[data-testid="stSidebarNavLink"] {
        font-size: 1em !important;
    }
    </style>
""", unsafe_allow_html=True)


pages = {
    "🪲 BugOut Index": [
        st.Page("pages/dashboard.py", title="Dashboard", icon="📟"),
        st.Page("pages/about.py", title="About the BOI", icon="ℹ️"),
        st.Page("pages/boi_simulator.py", title="Index Simulator", icon="🎛️")
     ],
    "📓 Metrics Documentation": [
        st.Page("pages/inflation_rate.py", title="Inflation Rate", icon="💰"),
        st.Page("pages/crime_rate.py", title="Crime Rate", icon="🚔"),
        st.Page("pages/unemployment_rate.py", title="Unemployment Rate", icon="📉"),
        st.Page("pages/debt_to_gdp_ratio.py", title="Debt to GDP", icon="💸"),
        st.Page("pages/homeless_rate.py", title="Homelessness Rate", icon="🏠"),
        st.Page("pages/trust_in_government.py", title="Trust in Government", icon="🏛")
    ],
}

pg = st.navigation(pages)
pg.run()
