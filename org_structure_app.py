import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import csv
import re

st.set_page_config(page_title="Organization Structure", layout="wide")
st.title("🏢 Organization Hierarchy (Auto Inference)")

uploaded_file = st.file_uploader("Upload organization structure CSV file", type=["csv"])

if uploaded_file:
    # --- Smart CSV Reader ---
    try:
        sample = uploaded_file.read(2048).decode("utf-8")
        uploaded_file.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";"

    df = pd.read_csv(uploaded_file, sep=delimiter, engine="python", encoding="utf-8")

    st.success(f"✅ File uploaded (delimiter='{delimiter}')")
    st.dataframe(df.head())

    # --- Level Detection ---
    def detect_level(position):
        pos = str(position).lower()
        if re.search(r"senior general manager|general manager|head", pos):
            return 1
        elif re.search(r"manager|lead|superintendent", pos):
            return 2
        elif re.search(r"officer|engineer|analyst|specialist|administrator|designer|developer|qa", pos):
            return 3
        else:
            return 4  # fallback
    df["level"] = df["POSITION"].apply(detect_level)

    # --- Build Hierarchy Links ---
    edges = []
    top_positions = df[df["level"] == 1]
    mid_positions = df[df["level"] == 2]
    low_positions = df[df["level"] == 3]

    # Link: top → mid (same division)
    for _, top in top_positions.iterrows():
        for _, mid in mid_positions.iterrows():
            if (pd.notna(top["DIVISION"]) and pd.notna(mid["DIVISION"])
                and top["DIVISION"].strip() in mid["DIVISION"]):
                edges.append((top["POSITION"], mid["POSITION"]))

    # Link: mid → low (same dept or section)
    for _, mid in mid_positions.iterrows():
        for _, low in low_positions.iterrows():
            if pd.notna(mid["DEPT"]) and pd.notna(low["DEPT"]):
                if mid["DEPT"].strip() in low["DEPT"]:
                    edges.append((mid["POSITION"], low["POSITION"]))
            elif pd.notna(mid["SECTION"]) and pd.notna(low["SECTION"]):
                if mid["SECTION"].strip() in low["SECTION"]:
                    edges.append((mid["POSITION"], low["POSITION"]))

    # Build tree structure for Plotly
    parents = []
    labels = []
    for parent, child in edges:
        parents.append(parent)
        labels.append(child)

    # Add top-level nodes
    roots = list(top_positions["POSITION"].unique())
    for r in roots:
        parents.append("")
        labels.append(r)

    # --- Plot Tree as Treemap ---
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        textinfo="label",
        marker=dict(colorscale="Blues", line=dict(color="white", width=2)),
        hovertemplate="<b>%{label}</b><extra></extra>"
    ))

    fig.update_layout(
        title="📊 Auto-Detected Organization Structure",
        margin=dict(t=30, l=10, r=10, b=10),
        height=850
    )

    st.plotly_chart(fig, use_container_width=True)

    st.info("""
    ✅ Hierarchy auto-detected:
    - Level 1: General Manager / Head
    - Level 2: Manager / Lead / Superintendent
    - Level 3: Engineer / Analyst / Officer / Specialist
    """)
else:
    st.info("📁 Please upload your CSV file to generate the organization structure.")
