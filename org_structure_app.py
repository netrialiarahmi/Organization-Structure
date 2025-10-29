import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Organization Structure (Manual)", layout="wide")
st.title("🏢 Organization Structure (Manual Hierarchy)")

# --- Manual hierarchy mapping ---
hierarchy = {
    "Senior General Manager Technology": [
        "General Manager Product & Data",
        "General Manager Engineering"
    ],
    "General Manager Product & Data": [
        "Data & Marketing Technology Lead",
        "Data Science & Analytic Lead",
        "Marketing Technology Officer"
    ],
    "Data & Marketing Technology Lead": [
        "Data Engineer",
        "Data Analyst"
    ],
    "Data Science & Analytic Lead": [
        "AI Engineer",
        "Data Analyst"
    ],
    "General Manager Engineering": [
        "Development Manager",
        "DevOps Superintendent",
        "UI/UX Engineer"
    ],
    "Development Manager": [
        "Software Engineer",
        "QA Engineer"
    ]
}

# --- Flatten hierarchy into edges ---
edges = []
for parent, children in hierarchy.items():
    for child in children:
        edges.append((parent, child))

# Build Plotly Tree Diagram
parents = []
labels = []
for parent, child in edges:
    parents.append(parent)
    labels.append(child)

# Add top-level nodes
roots = [p for p in hierarchy.keys() if all(p not in c for ch in hierarchy.values() for c in ch)]
for r in roots:
    parents.append("")
    labels.append(r)

fig = go.Figure(go.Treemap(
    labels=labels,
    parents=parents,
    textinfo="label",
    root_color="lightsteelblue",
    marker=dict(
        colorscale="Blues",
        line=dict(color="white", width=2)
    ),
    hovertemplate="<b>%{label}</b><extra></extra>"
))

fig.update_layout(
    title="📊 Organization Structure (Manual Mapping)",
    margin=dict(t=30, l=10, r=10, b=10),
    height=800
)

st.plotly_chart(fig, use_container_width=True)
