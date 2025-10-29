import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import csv

# --- CONFIGURATIONS ---
st.set_page_config(page_title="Organization Structure", layout="wide")

st.title("🏢 Organization Structure Viewer")

# --- UPLOAD FILE ---
uploaded_file = st.file_uploader("Upload organization structure CSV file", type=["csv"])

if uploaded_file:
    # --- SAFE CSV READER ---
    try:
        sample = uploaded_file.read(2048).decode("utf-8")
        uploaded_file.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";"

    try:
        df = pd.read_csv(
            uploaded_file,
            sep=delimiter,
            engine="python",
            encoding="utf-8",
            on_bad_lines="warn"
        )
        st.success(f"✅ File uploaded successfully! Detected delimiter: '{delimiter}'")
    except Exception as e:
        st.error(f"❌ Error reading CSV file: {e}")
        st.stop()

    # --- DISPLAY DATA ---
    st.subheader("Raw Data Preview")
    st.dataframe(df.head())

    # --- DEFINE COLUMN NAMES ---
    with st.expander("⚙️ Configure Columns"):
        hierarchy_cols = st.multiselect(
            "Select columns representing hierarchy (from top to bottom):",
            df.columns.tolist(),
            # auto pick last 3–4 levels if they exist (like Division → Dept → Section)
            default=df.columns[-4:-1].tolist() if len(df.columns) >= 4 else df.columns[:-1].tolist(),
        )
        name_col = st.selectbox(
            "Select the column containing employee names:",
            df.columns.tolist(),
            index=1 if "NAMA" in df.columns else len(df.columns) - 1,
        )

    # --- BUILD HIERARCHY TREE ---
    def build_hierarchy_with_names(df, cols, name_col):
        hierarchy = {}
        for _, row in df.iterrows():
            d = hierarchy
            for col in cols[:-1]:
                d = d.setdefault(str(row[col]).strip(), {})
            d.setdefault(str(row[cols[-1]]).strip(), []).append(str(row[name_col]).strip())
        return hierarchy

    hierarchy = build_hierarchy_with_names(df, hierarchy_cols, name_col)

    # --- CREATE GRAPH ---
    def create_tree_edges(hierarchy, parent=None, edges=None):
        if edges is None:
            edges = []
        for key, value in hierarchy.items():
            if isinstance(value, dict):
                if parent:
                    edges.append((parent, key))
                create_tree_edges(value, key, edges)
            elif isinstance(value, list):
                for name in value:
                    edges.append((key, name))
        return edges

    edges = create_tree_edges(hierarchy)

    # --- VISUALIZATION ---
    G = nx.DiGraph()
    G.add_edges_from([(a, b) for a, b in edges if a])

    pos = nx.spring_layout(G, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode='lines',
        line=dict(width=1, color='#BBBBBB')
    )

    node_x, node_y, node_text = [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        marker=dict(size=20, color='#2E86C1', line=dict(width=2, color='white'))
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(l=10, r=10, t=10, b=10),
        height=700,
    )

    st.subheader("📊 Organization Hierarchy Map")
    st.plotly_chart(fig, use_container_width=True)

    # --- SELECT NODE INFO ---
    st.subheader("🔍 Explore Organization Nodes")

    all_nodes = list(G.nodes())
    selected_node = st.selectbox("Select a position/division to view details:", all_nodes)

    def find_people_in_hierarchy(hierarchy, target):
        result = []
        for k, v in hierarchy.items():
            if k == target:
                if isinstance(v, list):
                    result.extend(v)
                elif isinstance(v, dict):
                    for sub_v in v.values():
                        if isinstance(sub_v, list):
                            result.extend(sub_v)
                return result
            elif isinstance(v, dict):
                nested = find_people_in_hierarchy(v, target)
                if nested:
                    return nested
        return result

    employees = find_people_in_hierarchy(hierarchy, selected_node)

    if employees:
        st.write(f"👥 People under **{selected_node}**:")
        for e in employees:
            st.markdown(f"- {e}")
    else:
        st.info("No employees found under this node.")
else:
    st.info("📁 Please upload a CSV file to start.")
