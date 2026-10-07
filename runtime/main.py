# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Optional local viewer. Reads the published snapshot. Does not publish."""
import streamlit as st

st.set_page_config(
    page_title="BugOut Index",
    page_icon="static/media/favicon.ico",
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header[data-testid="stNavSectionHeader"] {
        font-size: 1.3em !important;
        font-weight: bold !important;
        margin-top: 12px !important;
    }
    a[data-testid="stSidebarNavLink"] {
        font-size: 1em !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Optional viewer. It reads docs/data/latest.json and does not write the weekly site. "
    "To publish, run the weekly pipeline, then serve the docs/ directory."
)

pages = {
    "🪲 BugOut Index": [
        st.Page("pages/dashboard.py", title="Dashboard", icon="📟"),
        st.Page("pages/about.py", title="About the BOI", icon="ℹ️"),
        st.Page("pages/boi_simulator.py", title="Index Simulator", icon="🎛️"),
    ],
    "📓 Metrics Documentation": [
        st.Page("pages/inflation_rate.py", title="Inflation Rate", icon="💰"),
        st.Page("pages/crime_rate.py", title="Crime Rate", icon="🚔"),
        st.Page("pages/unemployment_rate.py", title="Unemployment Rate", icon="📉"),
        st.Page("pages/debt_to_gdp_ratio.py", title="Debt to GDP", icon="💸"),
        st.Page("pages/homeless_rate.py", title="Homelessness Rate", icon="🏠"),
        st.Page("pages/trust_in_government.py", title="Trust in Government", icon="🏛"),
    ],
}

pg = st.navigation(pages)
pg.run()
