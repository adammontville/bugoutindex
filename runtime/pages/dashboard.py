# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Optional viewer page. Displays the published snapshot. Does not publish."""
import streamlit as st
from presentation.display_logo import display_logo
from processing.formula import CORE_METRICS, stability_css_class as get_stability_class
from viewer_io import load_published_snapshot

CSS_FILE_PATH = "./presentation/styles.css"

METRIC_LABELS = {
    "inflation_rate": "Inflation",
    "incident_rate": "Crime",
    "unemployment_rate": "Unemployment",
    "debt_to_gdp_ratio": "Debt to GDP",
    "homelessness_rate": "Homelessness",
    "trust_in_government": "Trust in government",
}


def load_css(css_file):
    with open(css_file, "r", encoding="utf-8") as handle:
        st.markdown(f"<style>{handle.read()}</style>", unsafe_allow_html=True)


load_css(CSS_FILE_PATH)
snapshot = load_published_snapshot()
display_logo()

st.markdown("<h1 style='text-align: center;'>BugOut Index</h1>", unsafe_allow_html=True)
st.caption("Read-only view of the published snapshot. This page does not update the site.")

if snapshot is None:
    st.error("No published snapshot found at docs/data/latest.json.")
else:
    score = snapshot.get("bugout_index")
    stability_class = get_stability_class(score)
    st.markdown(
        f'<div class="{stability_class}">{float(score):.2f}</div>',
        unsafe_allow_html=True,
    )
    band = (snapshot.get("interpretation") or {}).get("band", "")
    risk = (snapshot.get("interpretation") or {}).get("risk", "")
    st.write(
        f"Published {snapshot.get('publication_date')} · {band} ({risk}) · "
        f"methodology {snapshot.get('methodology_version')}"
    )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Current metrics")
        lines = ["| Metric | Raw | Normalized | Observed |", "| --- | --- | --- | --- |"]
        metrics = snapshot.get("metrics") or {}
        for name in CORE_METRICS:
            block = metrics.get(name) or {}
            raw = block.get("raw")
            normalized = block.get("normalized")
            observed = block.get("observation_date") or ""
            raw_text = "" if raw is None else f"{float(raw):.2f}"
            norm_text = "" if normalized is None else f"{float(normalized):.2f}"
            lines.append(
                f"| {METRIC_LABELS.get(name, name)} | {raw_text} | {norm_text} | {observed} |"
            )
        st.markdown("\n".join(lines))
    with col2:
        st.markdown(
            """
            #### Stability matrix
            | **Range** | **Interpretation** |
            | --- | --- |
            | **70–100** | High Stability (Low Risk) |
            | **55–69** | Moderate Stability (Warning Signs) |
            | **40–54** | Low Stability (Heightened Risk) |
            | **<40** | Critical Instability (Collapse Likely) |
            """
        )

st.markdown("---")
st.markdown(
    "<div class='footnote'>*This product uses the FRED® API but is not endorsed or "
    "certified by the Federal Reserve Bank of St. Louis.*</div>",
    unsafe_allow_html=True,
)
