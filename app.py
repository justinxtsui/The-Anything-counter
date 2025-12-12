# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import io, os
from collections import Counter
from datetime import datetime

# ========================= CONFIGURATION =========================
APP_TITLE_COLOR = '#000000'
PRIMARY_COLOR = '#302A7E'
SECONDARY_COLOR = '#8884B3'
LIGHT_COLOR = '#D0CCE5'

# ========================= PAGE =========================
st.set_page_config(page_title="Ranklin", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for better styling
st.markdown("""
    <style>
    /* Main title styling */
    h1 {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #fafafa;
    }
    
    /* Section headers */
    .section-header {
        color: #302A7E;
        font-weight: 600;
        font-size: 1.2rem;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f5f7fa;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Button styling */
    .stDownloadButton button {
        background-color: #302A7E;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        width: 100%;
    }
    
    .stDownloadButton button:hover {
        background-color: #8884B3;
    }
    
    /* Radio button styling */
    [data-testid="stRadio"] > label {
        font-weight: 600;
    }
    
    /* Multiselect styling */
    [data-testid="stMultiSelect"] label {
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Main title
st.markdown(f'<h1 style="color:{APP_TITLE_COLOR};">Ranklin </h1>', unsafe_allow_html=True)

# *** MODIFICATION 1: Initial info message right after the title ***
# Use session state to track if a file has been uploaded
if 'uploaded_file' not in st.session_state or st.session_state.uploaded_file is None:
    st.session_state.uploaded_file = None
    st.info("👈🏻 Please upload your data file using the controls in the sidebar to begin.")

# Styled description box
st.markdown("""
    <div style="background: #f5f7fa; 
                padding: 20px; 
                border-radius: 10px; 
                border-left: 5px solid #302A7E; 
                margin: 15px 0;">
        <p style="margin: 0 0 10px 0; font-size: 16px; color: #333;">
        <a href="https://platform.beauhurst.com/search/advancedsearch/?avs_json=eyJiYXNlIjoiY29tcGFueSIsImNvbWJpbmUiOiJhbmQiLCJjaGlsZHJlbiI6W119" 
            target="_blank" 
            style="display: inline-block; background: #fff; padding: 10px 16px; border-radius: 6px; 
                   border: 1px solid #ddd; color: #302A7E; font-weight: 600; text-decoration: none; 
                   font-size: 14px; transition: all 0.2s ease; margin-bottom: 12px;">
            🔗 Beauhurst Advanced Search
        </a>
        <p style="margin: 12px 0 0 0; font-size: 14px; color: #666;">
            Contact <a href="mailto:justin.tsui@beauhurst.com" style="color: #302A7E; text-decoration: none; font-weight: 600;">justin.tsui@beauhurst.com</a> for support
        </p>
    </div>
""", unsafe_allow_html=True)

# ========================= HELPERS =========================
def read_any_table(file, sheet_name=None):
    name = getattr(file, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()

    if ext in [".xlsx", ".xls"]:
        if ext == ".xlsx":
            try:
                import openpyxl  # noqa: F401
                engine = "openpyxl"
            except Exception:
                st.error("Reading .xlsx requires `openpyxl` (pip install openpyxl).")
                st.stop()
        else:  # .xls
            try:
                import xlrd  # noqa: F401
                import xlrd as _xl
                # xlrd>=2.0 dropped .xls
                if tuple(int(x) for x in _xl.__version__.split(".")[:2]) >= (2, 0):
                    st.error("Reading .xls requires xlrd==1.2.0 (pip install xlrd==1.2.0).")
                    st.stop()
                engine = "xlrd"
            except Exception:
                st.error("Reading .xls requires xlrd==1.2.0 (pip install xlrd==1.2.0).")
                st.stop()

        try:
            xls = pd.ExcelFile(file, engine=engine)
            # Return sheet names if no sheet specified
            if sheet_name is None:
                return None, xls.sheet_names
            return pd.read_excel(file, sheet_name=sheet_name, engine=engine), None
        except Exception as e:
            st.exception(e)
            st.stop()

    # CSV fallback
    try:
        return pd.read_csv(file), None
    except UnicodeDecodeError:
        return pd.read_csv(file, encoding="latin-1"), None


def money_fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v == 0:
        return "£0"
    if v >= 1_000_000_000:
        x = v / 1_000_000_000
        return f"£{x:.0f}b" if x >= 100 else (f"£{x:.1f}b" if x >= 10 else f"£{x:.2f}b")
    if v >= 1_000_000:
        x = v / 1_000_000
        return f"£{x:.0f}m" if x >= 100 else (f"£{x:.1f}m" if x >= 10 else f"£{x:.2f}m")
    if v >= 1_000:
        x = v / 1_000
        return f"£{x:.0f}k" if x >= 100 else (f"£{x:.1f}k" if x >= 10 else f"£{x:.2f}k")
    return f"£{v:.0f}" if v >= 100 else (f"£{v:.1f}" if v >= 10 else f"£{v:.2f}")


def int_commas(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def find_amount_columns(cols):
    lc = [c.lower() for c in cols]
    candidates = []
    for i, c in enumerate(lc):
        if ("amount" in c and "gbp" in c) or ("amount raised" in c):
            candidates.append(cols[i])
        if "total amount received by the company" in c and "converted to gbp" in c:
            candidates.append(cols[i])
    # unique, keep order
    seen, out = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def detect_layout(df):
    cols = list(df.columns.astype(str))
    ind_single = "Industries" if "Industries" in cols else ("(Company) Industries" if "(Company) Industries" in cols else None)
    buzz_single = "Buzzwords" if "Buzzwords" in cols else ("(Company) Buzzwords" if "(Company) Buzzwords" in cols else None)
    ind_wide = [c for c in cols if c.startswith("Industries - ") or c.startswith("(Company) Industries - ")]
    buzz_wide = [c for c in cols if c.startswith("Buzzwords - ") or c.startswith("(Company) Buzzwords - ")]

    if ind_single and buzz_single:
        return {"mode": "single", "ind_col": ind_single, "buzz_col": buzz_single}
    if ind_wide or buzz_wide:
        return {"mode": "wide", "ind_cols": ind_wide, "buzz_cols": buzz_wide}
    return {"mode": "unknown"}


def coerce_bool_df(df_bool_like: pd.DataFrame) -> pd.DataFrame:
    out = df_bool_like.copy()
    # numeric -> nonzero True
    num_cols = out.select_dtypes(include=[np.number]).columns
    out[num_cols] = out[num_cols].fillna(0) != 0
    # others -> non-empty or truthy tokens
    other_cols = [c for c in out.columns if c not in num_cols]
    if other_cols:
        s = out[other_cols].astype(str).str.strip().str.lower()
        truthy = s.isin(["y", "yes", "true", "1", "✓", "✔", "x"])
        nonempty = s.ne("") & s.ne("nan")
        out[other_cols] = (truthy | nonempty)
    return out.fillna(False)


def plot_bar(labels, values, title, highlight_first=True, right_formatter=int_commas):
    mpl.rcParams['svg.fonttype'] = 'none'
    mpl.rcParams['pdf.fonttype'] = 42
    mpl.rcParams['font.family'] = 'Public Sans'
    mpl.rcParams['font.sans-serif'] = ['Public Sans', 'Arial', 'DejaVu Sans']
    mpl.rcParams['font.weight'] = 'normal'

    y_pos = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(10, 6))
    max_value = max(values) if values else 0

    # background bars (scale reference)
    ax.barh(y_pos, [max_value] * len(values), color='#E0E0E0', alpha=1.0, height=0.8)

    # foreground bars
    for i, (y, v) in enumerate(zip(y_pos, values)):
        color = '#4B4897' if (highlight_first and i == 0) else '#A4A2F2'
        ax.barh(y, float(v), color=color, height=0.8)

    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.tick_params(axis='y', which='both', length=0)

    offset_data = max_value * 0.02 if max_value else 0.05
    for i, (label, v) in enumerate(zip(labels, values)):
        text_color = 'white' if (highlight_first and i == 0) else 'black'
        ax.text(offset_data, y_pos[i], str(label),
                fontsize=13, ha='left', va='center', fontweight='normal', color=text_color)
        ax.text(max_value - offset_data, y_pos[i], right_formatter(v),
                fontsize=13, ha='right', va='center', fontweight='semibold', color=text_color)

    ax.set_title(title, fontsize=15, pad=20, fontweight='normal')
    ax.invert_yaxis()
    
    return fig


def _metric_map(labels, values):
    return {str(l): v for l, v in zip(labels, values)}


def _drag_order_ui(default_labels, metric_map, top_n):
    """
    Drag-and-drop if streamlit-sortables is available; otherwise fallback to an editable 'Rank' table.
    Returns (labels_topN, values_topN, highlight_first, full_ordered_labels, full_ordered_values).
    """
    # Try drag & drop
    try:
        from streamlit_sortables import sort_items  # pip install streamlit-sortables>=0.3.1
        
        st.markdown("""
            <style>
            /* Modern sortable styling */
            .sortable-item {
                background: white !important;
                border: 2px dashed #d0d0d0 !important;
                border-radius: 8px !important;
                padding: 14px 16px !important;
                margin: 10px 0 !important;
                cursor: grab !important;
                transition: all 0.2s ease !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
            }
            .sortable-item:hover {
                background: #fafafa !important;
                border-color: #8884B3 !important;
                border-style: solid !important;
                box-shadow: 0 2px 8px rgba(136,132,179,0.15) !important;
                transform: translateY(-1px) !important;
            }
            .sortable-item:active {
                cursor: grabbing !important;
            }
            .sortable-ghost {
                opacity: 0.4 !important;
                background: #f0f0f0 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        ordered_full = sort_items(default_labels)  # full list
        if isinstance(ordered_full, list) and len(ordered_full) == len(default_labels):
            values_full = [metric_map.get(lbl, 0) for lbl in ordered_full]
            labels_top = ordered_full[:top_n]
            values_top = values_full[:top_n]
            return labels_top, values_top, False, ordered_full, values_full
    except Exception:
        st.info(
            "Drag & drop requires `streamlit-sortables`. "
            "Fallback: edit the rank numbers below. "
            "Install with: `pip install streamlit-sortables>=0.3.1`"
        )

    # Fallback editable table
    df_order = pd.DataFrame({
        "Label": default_labels,
        "Value": [metric_map.get(lbl, 0) for lbl in default_labels],
        "Rank": list(range(1, len(default_labels) + 1)),
    })
    edited = st.data_editor(
        df_order,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "Label": st.column_config.TextColumn(disabled=True),
            "Value": st.column_config.NumberColumn(disabled=True),
            "Rank": st.column_config.NumberColumn(min_value=1, max_value=len(default_labels), step=1),
        },
        hide_index=True,
    )
    edited = edited.sort_values(by=["Rank", "Label"], ascending=[True, True])
    ordered_full = edited["Label"].tolist()
    values_full  = edited["Value"].tolist()
    labels_top   = ordered_full[:top_n]
    values_top   = values_full[:top_n]
    return labels_top, values_top, False, ordered_full, values_full


def _warn_boundary_tie(all_labels, all_values, top_n, metric_name, fmt=lambda x: x):
    """If the Nth and (N+1)th values are equal, show a reminder."""
    if not all_values or top_n is None:
        return
    if len(all_values) <= top_n:
        return
    try:
        vN = float(all_values[int(top_n) - 1])
        vNext = float(all_values[int(top_n)])
    except Exception:
        return
    if np.isfinite(vN) and np.isfinite(vNext) and vN == vNext:
        st.warning(
            f"⚠️ **Warning:** Rank {int(top_n)} (**{all_labels[int(top_n)-1]}**) "
            f"has the same {metric_name.lower()} as Rank {int(top_n)+1} (**{all_labels[int(top_n)]}**): **{fmt(vN)}**.\n\n"
            f"Consider increasing the count to break the tie."
        )


# ========================= APP =========================

# Sidebar for file upload
with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader(
        "Upload your Excel or CSV file", 
        type=["csv", "xlsx", "xls"],
        help="Upload a CSV or Excel file to begin creating your ranking chart."
    )
    st.session_state.uploaded_file = uploaded_file
    
    if uploaded_file:
        st.caption(f"✅ **{uploaded_file.name}** uploaded successfully")
        
        # Check if it's an Excel file and get sheet names
        name = getattr(uploaded_file, "name", "") or ""
        ext = os.path.splitext(name)[1].lower()
        
        sheet_name = None
        if ext in [".xlsx", ".xls"]:
            # Get sheet names first
            df_temp, sheet_names = read_any_table(uploaded_file, sheet_name=None)
            if sheet_names:
                sheet_name = st.selectbox("Select sheet:", sheet_names, index=0)

# Initialize df
df = None

if uploaded_file is not None:
    # Load the actual data with selected sheet
    name = getattr(uploaded_file, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    
    if ext in [".xlsx", ".xls"]:
        df, _ = read_any_table(uploaded_file, sheet_name=sheet_name)
    else:
        df, _ = read_any_table(uploaded_file)

    # ========================= CHART TITLE SECTION =========================
    with st.sidebar:
        st.markdown("---")
        st.header("2. Chart Title")
        chart_title_input = st.text_input(
            "Title:", 
            value="Ranking Chart",
            help="Customize the title shown above the chart"
        )

    # ========================= RANKING MODE SECTION =========================
    with st.sidebar:
        st.markdown("---")
        st.header("3. Are you ranking Industries/Buzzwords?")
        
        mode = st.radio(
            "",
            ["Yes", "No"],
            horizontal=True,
            help="Choose Yes for Industries/Buzzwords or No for general data ranking"
        )

    # ========================= INDUSTRIES/BUZZWORDS MODE =========================
    if mode == "Yes":
        layout = detect_layout(df)
        if layout["mode"] == "unknown":
            st.error("Expected either single columns ('Industries','Buzzwords') or wide columns starting with 'Industries - ' / 'Buzzwords - '.")
            st.stop()

        with st.sidebar:
            st.markdown("---")
            st.header("4. Analysis Options")
            
            ranking_by = st.radio("Rank by:", ["Count", "Total Amount Raised"], horizontal=True)
            
            amount_candidates = find_amount_columns(list(df.columns.astype(str)))
            amount_choice = st.selectbox(
                "Amount column (optional)", 
                ["<None>"] + amount_candidates, 
                index=0,
                help="Select the column containing amount values for ranking"
            )
            amount_choice = None if amount_choice == "<None>" else amount_choice

        # ---- Build tallies (same logic as before)
        if layout["mode"] == "single":
            industries_col = layout["ind_col"]
            buzzwords_col  = layout["buzz_col"]

            inds = df[industries_col].dropna().astype(str).str.split(",").explode().str.strip()
            buzz = df[buzzwords_col].dropna().astype(str).str.split(",").explode().str.strip()
            items = pd.concat([inds, buzz], ignore_index=True)
            items = items[items.ne("") & items.ne("nan")]
            counts = items.value_counts()

            if amount_choice:
                amt = pd.to_numeric(df[amount_choice], errors="coerce").fillna(0.0)

                def explode_with_rowkey(series, keyname):
                    s = series.where(series.notna(), "").astype(str).str.split(",")
                    ex = s.explode().str.strip()
                    mask = ex.ne("") & ex.ne("nan")
                    out = pd.DataFrame({keyname: ex[mask]})
                    out["__row__"] = np.repeat(np.arange(len(series), dtype=int), s.str.len())[mask]
                    return out

                ex_i = explode_with_rowkey(df[industries_col], "item")
                ex_b = explode_with_rowkey(df[buzzwords_col], "item")
                ex = pd.concat([ex_i, ex_b], ignore_index=True)
                ex = ex[ex["item"].ne("")]
                ex = ex.merge(pd.DataFrame({"__row__": np.arange(len(df), dtype=int), "amt": amt}), on="__row__", how="left")
                amount_per_item = ex.groupby("item", as_index=True)["amt"].sum()
            else:
                amount_per_item = pd.Series(0.0, index=counts.index)

        else:  # wide
            ind_cols  = layout.get("ind_cols", [])
            buzz_cols = layout.get("buzz_cols", [])
            pieces = []
            if ind_cols:
                pieces.append(pd.DataFrame({c.split(" - ", 1)[1]: df[c] for c in ind_cols}))
            if buzz_cols:
                pieces.append(pd.DataFrame({c.split(" - ", 1)[1]: df[c] for c in buzz_cols}))
            M = pd.concat(pieces, axis=1)
            M = M.groupby(level=0, axis=1).sum()
            M_bool = coerce_bool_df(M)
            counts = M_bool.sum(axis=0).sort_values(ascending=False)
            if amount_choice:
                amt = pd.to_numeric(df[amount_choice], errors="coerce").fillna(0.0)
                amount_per_item = (M_bool.astype(float).multiply(amt, axis=0)).sum(axis=0)
            else:
                amount_per_item = pd.Series(0.0, index=counts.index)

        metric_series = counts if ranking_by == "Count" else amount_per_item
        metric_series = metric_series.sort_values(ascending=False)

        labels = [str(x) for x in metric_series.index.tolist()]
        values = metric_series.values.tolist()

        # ========================= DATA FILTER SECTION =========================
        with st.sidebar:
            st.markdown("---")
            st.header("5. Data Filter (Optional)")
            
            filter_enabled = st.checkbox('Enable Data Filtering', value=False, key='filter_ind_buzz')
            
            if filter_enabled:
                filter_mode = st.radio("Filter mode:", ["Include", "Exclude"], horizontal=True, key='filter_mode_ind_buzz')
                
                cols = [str(c) for c in df.columns]
                if cols:
                    filter_col = st.selectbox("Filter column:", options=cols, index=0, key='filter_col_ind_buzz')
                    
                    # Normalise display values
                    ser_raw = df[filter_col]
                    ser_disp = ser_raw.astype(str).fillna("")
                    ser_disp = ser_disp.replace({"nan": "", "None": ""})

                    uniques = pd.Series(ser_disp.unique(), dtype=str)
                    uniques = uniques.fillna("")
                    display_vals = uniques.replace({"": "(blank)"})
                    display_vals = sorted(display_vals.tolist(), key=lambda x: x.lower())

                    if len(display_vals) > 300:
                        st.warning("Too many unique values — showing only the first 300.")
                        display_vals = display_vals[:300]

                    selected_vals = st.multiselect("Select categories:", options=display_vals, key='filter_vals_ind_buzz')

                    if selected_vals:
                        selected_raw = [("" if v == "(blank)" else v) for v in selected_vals]
                        mask = ser_disp.isin(selected_raw)
                        
                        # Filter the original data and recompute
                        df_filtered = df[mask] if filter_mode == "Include" else df[~mask]
                        st.success(f"Filtered to {len(df_filtered):,} rows")
                        
                        # Recompute with filtered data
                        if layout["mode"] == "single":
                            industries_col = layout["ind_col"]
                            buzzwords_col  = layout["buzz_col"]

                            inds = df_filtered[industries_col].dropna().astype(str).str.split(",").explode().str.strip()
                            buzz = df_filtered[buzzwords_col].dropna().astype(str).str.split(",").explode().str.strip()
                            items = pd.concat([inds, buzz], ignore_index=True)
                            items = items[items.ne("") & items.ne("nan")]
                            counts = items.value_counts()

                            if amount_choice:
                                amt = pd.to_numeric(df_filtered[amount_choice], errors="coerce").fillna(0.0)

                                def explode_with_rowkey(series, keyname):
                                    s = series.where(series.notna(), "").astype(str).str.split(",")
                                    ex = s.explode().str.strip()
                                    mask = ex.ne("") & ex.ne("nan")
                                    out = pd.DataFrame({keyname: ex[mask]})
                                    out["__row__"] = np.repeat(np.arange(len(series), dtype=int), s.str.len())[mask]
                                    return out

                                ex_i = explode_with_rowkey(df_filtered[industries_col], "item")
                                ex_b = explode_with_rowkey(df_filtered[buzzwords_col], "item")
                                ex = pd.concat([ex_i, ex_b], ignore_index=True)
                                ex = ex[ex["item"].ne("")]
                                ex = ex.merge(pd.DataFrame({"__row__": np.arange(len(df_filtered), dtype=int), "amt": amt}), on="__row__", how="left")
                                amount_per_item = ex.groupby("item", as_index=True)["amt"].sum()
                            else:
                                amount_per_item = pd.Series(0.0, index=counts.index)

                        else:  # wide
                            ind_cols  = layout.get("ind_cols", [])
                            buzz_cols = layout.get("buzz_cols", [])
                            pieces = []
                            if ind_cols:
                                pieces.append(pd.DataFrame({c.split(" - ", 1)[1]: df_filtered[c] for c in ind_cols}))
                            if buzz_cols:
                                pieces.append(pd.DataFrame({c.split(" - ", 1)[1]: df_filtered[c] for c in buzz_cols}))
                            M = pd.concat(pieces, axis=1)
                            M = M.groupby(level=0, axis=1).sum()
                            M_bool = coerce_bool_df(M)
                            counts = M_bool.sum(axis=0).sort_values(ascending=False)
                            if amount_choice:
                                amt = pd.to_numeric(df_filtered[amount_choice], errors="coerce").fillna(0.0)
                                amount_per_item = (M_bool.astype(float).multiply(amt, axis=0)).sum(axis=0)
                            else:
                                amount_per_item = pd.Series(0.0, index=counts.index)

                        metric_series = counts if ranking_by == "Count" else amount_per_item
                        metric_series = metric_series.sort_values(ascending=False)

                        labels = [str(x) for x in metric_series.index.tolist()]
                        values = metric_series.values.tolist()

        # ---- Ordering & Top N in sidebar
        with st.sidebar:
            st.markdown("---")
            st.header("6. Order & Display")
            
            rank_mode = st.radio(
                "Ranking mode:",
                ["Highest first", "Lowest first", "Custom (drag & drop)"],
                horizontal=True
            )
            
            top_n = st.number_input(
                "Number of bars to show:",
                min_value=1,
                max_value=len(labels),
                value=min(10, len(labels)),
                step=1,
                help="Use the + / – buttons to adjust."
            )

        formatter = money_fmt if ranking_by != "Count" else int_commas

        if rank_mode in ["Highest first", "Lowest first"]:
            reverse_flag = (rank_mode == "Highest first")
            full_labels_ordered, full_values_ordered = zip(*sorted(zip(labels, values), key=lambda lv: lv[1], reverse=reverse_flag))
            full_labels_ordered, full_values_ordered = list(full_labels_ordered), list(full_values_ordered)

            _warn_boundary_tie(
                full_labels_ordered,
                full_values_ordered,
                int(top_n),
                ranking_by,
                fmt=(money_fmt if ranking_by != "Count" else int_commas)
            )

            labels, values = full_labels_ordered[:int(top_n)], full_values_ordered[:int(top_n)]
            highlight_top = True
        else:
            default_labels = [lbl for lbl, _ in sorted(zip(labels, values), key=lambda lv: (-lv[1], str(lv[0]).lower()))]
            metric_map = _metric_map(labels, values)
            
            with st.sidebar:
                st.markdown("**Drag to Reorder:**")
                labels, values, highlight_top, full_ordered_labels, full_ordered_values = _drag_order_ui(default_labels, metric_map, int(top_n))

            _warn_boundary_tie(
                full_ordered_labels,
                full_ordered_values,
                int(top_n),
                ranking_by,
                fmt=(money_fmt if ranking_by != "Count" else int_commas)
            )

        # Chart title uses the input from section 2
        chart_title = chart_title_input

        # Main area: Chart display
        st.subheader("Chart Preview")
        
        col_left, col_chart, col_right = st.columns([0.05, 7, 0.05])
        with col_chart:
            fig = plot_bar(labels, values, chart_title, highlight_first=highlight_top, right_formatter=formatter)
            st.pyplot(fig, use_container_width=True)

        # Download in sidebar
        with st.sidebar:
            st.markdown("---")
            st.header("7. Download Chart")
            
            svg_buffer = io.BytesIO()
            fig.savefig(svg_buffer, format="svg", bbox_inches="tight")
            svg_buffer.seek(0)
            
            st.download_button(
                label="Download as SVG (Vector)",
                data=svg_buffer,
                file_name=f"{chart_title.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg",
                mime="image/svg+xml",
                use_container_width=True
            )

    # ========================= ANYTHING COUNTER MODE =========================
    else:
        with st.sidebar:
            st.markdown("---")
            st.header("4. Analysis Options")
            
            analysis_type = st.radio(
                "Select analysis type:", 
                ["Count Values", "Sum Values"], 
                horizontal=True,
                help="Choose whether to count occurrences or sum numeric values"
            )

        if analysis_type == "Count Values":
            with st.sidebar:
                col = st.selectbox("Select column:", df.columns.tolist())
                explode = st.checkbox(
                    "Explode comma-separated values",
                    help="Split comma-separated values and count each separately"
                )
                
            if explode:
                value_list = []
                for val in df[col].dropna():
                    items = [s.strip() for s in str(val).split(",") if s.strip()]
                    value_list.extend(items)
                counts = Counter(value_list)
                labels = list(counts.keys())
                values = list(counts.values())
            else:
                vc = df[col].value_counts(dropna=False)
                labels = [("(blank)" if (isinstance(k, float) and pd.isna(k)) else str(k)) for k in vc.index.tolist()]
                values = vc.values.tolist()
            ranking_by = "Count"
            formatter = int_commas

        else:  # Sum Values
            with st.sidebar:
                group_col = st.selectbox("Group by:", df.columns.tolist())
                num_cols = df.select_dtypes(include=["number"]).columns.tolist()
                if not num_cols:
                    st.warning("No numeric columns found to sum.")
                    st.stop()
                sum_col = st.selectbox("Sum column:", num_cols)
                is_money = st.toggle("Treat values as money (£)?", True)
                
            vals = pd.to_numeric(df[sum_col], errors="coerce")
            keys = df[group_col].astype(str).fillna("")
            summed = vals.groupby(keys, sort=False).sum()
            labels = summed.index.tolist()
            values = summed.values.tolist()
            ranking_by = "Amount (£)" if is_money else "Amount"
            formatter = money_fmt if is_money else int_commas

        # default sort by value desc
        if labels:
            labels, values = zip(*sorted(zip(labels, values), key=lambda lv: lv[1], reverse=True))
            labels, values = list(labels), list(values)

        # ========================= DATA FILTER SECTION =========================
        with st.sidebar:
            st.markdown("---")
            st.header("5. Data Filter (Optional)")
            
            filter_enabled = st.checkbox('Enable Data Filtering', value=False, key='filter_anything')
            
            if filter_enabled:
                filter_mode = st.radio("Filter mode:", ["Include", "Exclude"], horizontal=True, key='filter_mode_anything')
                
                cols = [str(c) for c in df.columns]
                if cols:
                    filter_col = st.selectbox("Filter column:", options=cols, index=0, key='filter_col_anything')
                    
                    # Normalise display values
                    ser_raw = df[filter_col]
                    ser_disp = ser_raw.astype(str).fillna("")
                    ser_disp = ser_disp.replace({"nan": "", "None": ""})

                    uniques = pd.Series(ser_disp.unique(), dtype=str)
                    uniques = uniques.fillna("")
                    display_vals = uniques.replace({"": "(blank)"})
                    display_vals = sorted(display_vals.tolist(), key=lambda x: x.lower())

                    if len(display_vals) > 300:
                        st.warning("Too many unique values — showing only the first 300.")
                        display_vals = display_vals[:300]

                    selected_vals = st.multiselect("Select categories:", options=display_vals, key='filter_vals_anything')

                    if selected_vals:
                        selected_raw = [("" if v == "(blank)" else v) for v in selected_vals]
                        mask = ser_disp.isin(selected_raw)
                        
                        # Filter and recompute
                        df_filtered = df[mask] if filter_mode == "Include" else df[~mask]
                        st.success(f"Filtered to {len(df_filtered):,} rows")
                        
                        # Recompute with filtered data
                        if analysis_type == "Count Values":
                            if explode:
                                value_list = []
                                for val in df_filtered[col].dropna():
                                    items = [s.strip() for s in str(val).split(",") if s.strip()]
                                    value_list.extend(items)
                                counts = Counter(value_list)
                                labels = list(counts.keys())
                                values = list(counts.values())
                            else:
                                vc = df_filtered[col].value_counts(dropna=False)
                                labels = [("(blank)" if (isinstance(k, float) and pd.isna(k)) else str(k)) for k in vc.index.tolist()]
                                values = vc.values.tolist()
                        else:  # Sum Values
                            vals = pd.to_numeric(df_filtered[sum_col], errors="coerce")
                            keys = df_filtered[group_col].astype(str).fillna("")
                            summed = vals.groupby(keys, sort=False).sum()
                            labels = summed.index.tolist()
                            values = summed.values.tolist()
                        
                        # Re-sort
                        if labels:
                            labels, values = zip(*sorted(zip(labels, values), key=lambda lv: lv[1], reverse=True))
                            labels, values = list(labels), list(values)

        # ---- Ordering & Top N in sidebar
        with st.sidebar:
            st.markdown("---")
            st.header("6. Order & Display")
            
            rank_mode = st.radio(
                "Ranking mode:",
                ["Highest first", "Lowest first", "Custom (drag & drop)"],
                horizontal=True
            )
            
            top_n = st.number_input(
                "Number of bars to show:",
                min_value=1,
                max_value=len(labels),
                value=min(10, len(labels)),
                step=1,
                help="Use the + / – buttons to adjust."
            )

        if rank_mode in ["Highest first", "Lowest first"]:
            reverse_flag = (rank_mode == "Highest first")
            full_labels_ordered, full_values_ordered = zip(*sorted(zip(labels, values), key=lambda lv: lv[1], reverse=reverse_flag))
            full_labels_ordered, full_values_ordered = list(full_labels_ordered), list(full_values_ordered)

            _warn_boundary_tie(
                full_labels_ordered,
                full_values_ordered,
                int(top_n),
                ranking_by,
                fmt=(money_fmt if ranking_by != "Count" else int_commas)
            )

            labels, values = full_labels_ordered[:int(top_n)], full_values_ordered[:int(top_n)]
            highlight_top = True
        else:
            default_labels = [lbl for lbl, _ in sorted(zip(labels, values), key=lambda lv: (-lv[1], str(lv[0]).lower()))]
            metric_map = _metric_map(labels, values)
            
            with st.sidebar:
                st.markdown("**Drag to Reorder:**")
                labels, values, highlight_top, full_ordered_labels, full_ordered_values = _drag_order_ui(default_labels, metric_map, int(top_n))

            _warn_boundary_tie(
                full_ordered_labels,
                full_ordered_values,
                int(top_n),
                ranking_by,
                fmt=(money_fmt if ranking_by != "Count" else int_commas)
            )

        # Chart title uses the input from section 2
        chart_title = chart_title_input

        # Main area: Chart display
        st.subheader("Chart Preview")
        
        col_left, col_chart, col_right = st.columns([0.05, 7, 0.05])
        with col_chart:
            fig = plot_bar(labels, values, chart_title, highlight_first=highlight_top, right_formatter=formatter)
            st.pyplot(fig, use_container_width=True)

        # Download in sidebar
        with st.sidebar:
            st.markdown("---")
            st.header("7. Download Chart")
            
            svg_buffer = io.BytesIO()
            fig.savefig(svg_buffer, format="svg", bbox_inches="tight")
            svg_buffer.seek(0)
            
            st.download_button(
                label="Download as SVG (Vector)",
                data=svg_buffer,
                file_name=f"{chart_title.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg",
                mime="image/svg+xml",
                use_container_width=True
            )

else:
    st.markdown("---")
 
