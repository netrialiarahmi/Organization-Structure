import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import csv
from collections import defaultdict

st.set_page_config(page_title="Organization Structure (Upload CSV)", layout="wide")
st.title("🏢 Organization Hierarchy Viewer — Upload CSV & Explore")

st.markdown(
    """
    **Cara pakai**
    1. Upload file CSV (contoh kolom: No; NAMA; POSITION; DIVISION; DEPT; SECTION).  
    2. Pilih kolom yang merepresentasikan hierarchy dari **atas ke bawah** (mis. DIVISION → DEPT → SECTION → POSITION).  
    3. Klik box di chart untuk zoom/expand. Untuk melihat nama orang, pilih node di dropdown **Select Node**.
    """
)

uploaded_file = st.file_uploader("Upload organization structure CSV file (CSV UTF-8 recommended)", type=["csv"])

def safe_read_csv(uploaded_file):
    # Try to detect delimiter (',' or ';'), fallback to ';'
    try:
        sample = uploaded_file.read(4096)
        # if bytes, decode
        if isinstance(sample, bytes):
            sample_text = sample.decode("utf-8", errors="ignore")
        else:
            sample_text = str(sample)
        uploaded_file.seek(0)
        dialect = csv.Sniffer().sniff(sample_text, delimiters=";,")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";"
    # read with python engine for robustness
    df = pd.read_csv(uploaded_file, sep=delimiter, engine="python", encoding="utf-8", on_bad_lines="warn")
    return df, delimiter

if uploaded_file:
    try:
        df, detected_delimiter = safe_read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")
        st.stop()

    st.success(f"File uploaded. Detected delimiter: '{detected_delimiter}'")
    st.subheader("Raw data preview")
    st.dataframe(df.head(10))

    # Standardize column names to stripped uppercase for easier selection
    df.columns = [c.strip() for c in df.columns]
    cols = df.columns.tolist()

    with st.expander("⚙️ Configure hierarchy columns (top → bottom) and name column"):
        st.write("Pilih kolom yang menunjukkan level dari atas ke bawah. Contoh: DIVISION → DEPT → SECTION → POSITION")
        hierarchy_cols = st.multiselect("Hierarchy columns (top → bottom):", cols, default=[c for c in cols if c.upper() in ("DIVISION","DEPT","SECTION","POSITION")])
        if not hierarchy_cols:
            st.warning("Pilih minimal 1 kolom untuk membuat struktur. Saya akan menggunakan kolom POSITION sebagai fallback.")
            # fallback to POSITION if exists
            if "POSITION" in [c.upper() for c in cols]:
                # find original name for POSITION
                for c in cols:
                    if c.upper() == "POSITION":
                        hierarchy_cols = [c]
                        break
        name_col = st.selectbox("Column for employee name:", cols, index=0 if "NAMA" in [c.upper() for c in cols] else min(1, len(cols)-1))

    # Build path string per row from chosen hierarchy columns (skip empty)
    def build_path(row, hierarchy_cols):
        parts = []
        for col in hierarchy_cols:
            v = row.get(col, "")
            if pd.isna(v):
                continue
            text = str(v).strip()
            if text == "":
                continue
            parts.append(text)
        return " / ".join(parts) if parts else None

    df["__path"] = df.apply(lambda r: build_path(r, hierarchy_cols), axis=1)
    # For some rows (missing hierarchy) we still want POSITION as node
    # Keep only rows with path not None
    df = df[df["__path"].notna()].copy()
    if df.empty:
        st.error("Tidak ada baris yang memiliki value untuk kombinasi hierarchy yang dipilih.")
        st.stop()

    # Aggregate: group by path, collect names, and get counts
    agg = df.groupby("__path").agg(
        count=(name_col, "count"),
        names=(name_col, lambda x: list(x.dropna().astype(str)))
    ).reset_index()

    # Build nodes for treemap: for each unique path create id (the full path),
    # parent is path without last segment
    nodes = []
    id_to_names = {}
    for _, row in agg.iterrows():
        full = row["__path"]
        names = row["names"]
        count = int(row["count"])
        parts = full.split(" / ")
        label = parts[-1]
        parent = " / ".join(parts[:-1]) if len(parts) > 1 else ""  # root uses empty parent
        nodes.append({"id": full, "label": label, "parent": parent, "value": count})
        id_to_names[full] = names

    # Also ensure intermediary nodes (parent nodes that may not appear as a full path) exist
    # Example: if we have "A / B / C", ensure "A" and "A / B" are nodes
    existing_ids = set(n["id"] for n in nodes)
    extra_nodes = {}
    for n in list(nodes):
        parts = n["id"].split(" / ")
        for k in range(1, len(parts)):
            pid = " / ".join(parts[:k])
            if pid not in existing_ids and pid not in extra_nodes:
                extra_nodes[pid] = {"id": pid, "label": parts[k-1], "parent": (" / ".join(parts[:k-1]) if k-1 > 0 else ""), "value": 0}
    # add extras
    for v in extra_nodes.values():
        nodes.append(v)
        existing_ids.add(v["id"])

    # Determine root nodes (parents == "")
    ids = [n["id"] for n in nodes]
    parents = [n["parent"] for n in nodes]
    labels = [n["label"] for n in nodes]
    values = [n["value"] for n in nodes]

    # Build treemap
    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        textinfo="label+value",
        marker=dict(colorscale="Blues", showscale=False, line=dict(width=2, color="white")),
        hovertemplate="<b>%{label}</b><br>Path: %{id}<br>People: %{value}<extra></extra>"
    ))
    fig.update_layout(margin=dict(t=40, l=10, r=10, b=10), height=750, title="Organization Structure (click boxes to expand/zoom)")

    st.subheader("Organization Hierarchy Map")
    st.plotly_chart(fig, use_container_width=True)

    # Build flattened list of node ids for selection (show root first)
    node_choices = sorted(ids)
    selected_node = st.selectbox("Select Node (to view employees under this node):", ["(root)"] + node_choices)

    # Function: find names under a node (all descendant nodes)
    def find_descendant_names(selected_id, nodes_list, id_to_names_map):
        if selected_id == "(root)" or selected_id == "":
            # return all names
            all_names = []
            for k, v in id_to_names_map.items():
                all_names.extend(v)
            return all_names
        # find descendants: any id that starts with selected_id + " / " or equals selected_id
        prefix = selected_id + " / "
        collected = []
        for nid, names in id_to_names_map.items():
            if nid == selected_id or nid.startswith(prefix):
                collected.extend(names)
        return collected

    if selected_node:
        # if user chose "(root)" show top-level summary
        if selected_node == "(root)":
            st.subheader("People (entire organization)")
            people = find_descendant_names("", ids, id_to_names)
            if people:
                st.write(f"Total people: {len(people)}")
                # show as bullet list
                for p in people:
                    st.markdown(f"- {p}")
            else:
                st.info("No people found")
        else:
            st.subheader(f"People under: {selected_node}")
            people = find_descendant_names(selected_node, ids, id_to_names)
            if people:
                st.write(f"Total: {len(people)}")
                # show compact cards in columns (for nicer UI)
                cols = st.columns(2)
                for i, person in enumerate(people):
                    with cols[i % 2]:
                        st.write(f"- {person}")
            else:
                st.info("No people found under this node.")

    # Extra: allow export of the node->people mapping as JSON/CSV
    if st.button("Download node->people CSV"):
        # flatten mapping
        rows = []
        for nid, names in id_to_names.items():
            for nm in names:
                rows.append({"node": nid, "name": nm})
        out_df = pd.DataFrame(rows)
        csv_data = out_df.to_csv(index=False)
        st.download_button("Download CSV", data=csv_data, file_name="node_people_mapping.csv", mime="text/csv")

else:
    st.info("📁 Please upload your organization CSV file to start.")
