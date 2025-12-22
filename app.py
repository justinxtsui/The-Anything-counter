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

# Custom CSS
st.markdown("""
    <style>
    h1 { color: #000000 !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #fafafa; }
    .stDownloadButton button {
        background-color: #302A7E; color: white; border-radius: 6px;
        font-weight: 600; border: none; padding: 0.5rem 1rem; width: 100%;
        margin-bottom: 10px;
    }
    .stDownloadButton button:hover { background-color: #8884B3; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f'<h1 style="color:{APP_TITLE_COLOR};">Ranklin </h1>', unsafe_allow_html=True)

if 'uploaded_file' not in st.session_state or st.session_state.uploaded_file is None:
    st.info("👈🏻 Please upload your data file using the controls in the sidebar to begin.")

# ========================= HELPERS =========================
def read_any_table(file, sheet_name=None):
    name = getattr(file, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext in [".xlsx", ".xls"]:
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        xls = pd.ExcelFile(file, engine=engine)
        if sheet_name is None: return None, xls.sheet_names
        return pd.read_excel(file, sheet_name=sheet_name, engine=engine), None
    try:
        return pd.read_csv(file), None
    except:
        return pd.read_csv(file, encoding="latin-1"), None

def money_fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v == 0: return "£0"
    if v >= 1e9: return f"£{v/1e9:.1f}b"
    if v >= 1e6: return f"£{v/1e6:.1f}m"
    if v >= 1e3: return f"£{v/1e3:.1f}k"
    return f"£{v:.0f}"

def int_commas(n):
    try: return f"{int(n):,}"
    except: return str(n)

def find_amount_columns(cols):
    return [c for c in cols if any(x in c.lower() for x in ["amount raised", "gbp", "converted to gbp"])]

def detect_layout(df):
    cols = list(df.columns.astype(str))
    ind_s = "Industries" if "Industries" in cols else ("(Company) Industries" if "(Company) Industries" in cols else None)
    buzz_s = "Buzzwords" if "Buzzwords" in cols else ("(Company) Buzzwords" if "(Company) Buzzwords" in cols else None)
    ind_w = [c for c in cols if "Industries - " in c]
    buzz_w = [c for c in cols if "Buzzwords - " in c]
    if ind_s and buzz_s: return {"mode": "single", "ind_col": ind_s, "buzz_col": buzz_s}
    if ind_w or buzz_w: return {"mode": "wide", "ind_cols": ind_w, "buzz_cols": buzz_w}
    return {"mode": "unknown"}

def coerce_bool_df(df_bool_like):
    out = df_bool_like.copy()
    num_cols = out.select_dtypes(include=[np.number]).columns
    out[num_cols] = out[num_cols].fillna(0) != 0
    other_cols = [c for c in out.columns if c not in num_cols]
    if other_cols:
        s = out[other_cols].astype(str).str.strip().str.lower()
        out[other_cols] = s.isin(["y", "yes", "true", "1", "✓", "x"]) | (s.ne("") & s.ne("nan"))
    return out.fillna(False)

def plot_bar(labels, values, title, highlight_first=True, right_formatter=int_commas):
    plt.rcParams['font.family'] = 'sans-serif'
    fig, ax = plt.subplots(figsize=(10, 6))
    max_val = max(values) if values else 1
    y_pos = list(range(len(labels)))
    ax.barh(y_pos, [max_val] * len(values), color='#E0E0E0', height=0.8)
    for i, (y, v) in enumerate(zip(y_pos, values)):
        color = '#4B4897' if (highlight_first and i == 0) else '#A4A2F2'
        ax.barh(y, float(v), color=color, height=0.8)
    ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.xaxis.set_visible(False)
    offset = max_val * 0.02
    for i, (label, v) in enumerate(zip(labels, values)):
        text_c = 'white' if (highlight_first and i == 0) else 'black'
        ax.text(offset, i, str(label), va='center', color=text_c, fontsize=12)
        ax.text(max_val - offset, i, right_formatter(v), va='center', ha='right', color=text_c, fontweight='bold')
    ax.set_title(title, fontsize=14, pad=20)
    ax.invert_yaxis()
    return fig

def _drag_order_ui(default_labels, metric_map, top_n):
    try:
        from streamlit_sortables import sort_items
        ordered_full = sort_items(default_labels)
        if isinstance(ordered_full, list) and len(ordered_full) == len(default_labels):
            vals_full = [metric_map.get(l, 0) for l in ordered_full]
            return ordered_full[:top_n], vals_full[:top_n], False, ordered_full, vals_full
    except: pass
    return default_labels[:top_n], [metric_map.get(l, 0) for l in default_labels[:top_n]], False, default_labels, [metric_map.get(l, 0) for l in default_labels]

# ========================= MULTI-FILTER COMPONENT =========================
def apply_multi_filters(df, key_prefix):
    st.subheader("Raw Data Filtering")
    
    if f'filter_rules_{key_prefix}' not in st.session_state:
        st.session_state[f'filter_rules_{key_prefix}'] = []

    col_a, col_b = st.columns(2)
    if col_a.button("➕ Add Filter", key=f"add_{key_prefix}"):
        st.session_state[f'filter_rules_{key_prefix}'].append({'column': df.columns[0], 'mode': 'Include', 'vals': []})
    if col_b.button("➖ Remove Last", key=f"rem_{key_prefix}"):
        if st.session_state[f'filter_rules_{key_prefix}']:
            st.session_state[f'filter_rules_{key_prefix}'].pop()

    df_temp = df.copy()
    rules = st.session_state[f'filter_rules_{key_prefix}']
    
    for i, rule in enumerate(rules):
        with st.expander(f"Rule {i+1}: {rule['column']}", expanded=True):
            c1, c2 = st.columns([2,1])
            rule['column'] = c1.selectbox("Column", df.columns, key=f"col_{key_prefix}_{i}")
            rule['mode'] = c2.radio("Mode", ["Include", "Exclude"], key=f"m_{key_prefix}_{i}", horizontal=True)
            
            opts = sorted(df[rule['column']].astype(str).unique().tolist())
            display_opts = [("(blank)" if x in ["nan", "None", ""] else x) for x in opts]
            rule['vals'] = st.multiselect("Values", display_opts, key=f"v_{key_prefix}_{i}")
            
            if rule['vals']:
                actual_vals = [("" if v == "(blank)" else v) for v in rule['vals']]
                mask = df_temp[rule['column']].astype(str).replace({"nan":"", "None":""}).isin(actual_vals)
                df_temp = df_temp[mask] if rule['mode'] == "Include" else df_temp[~mask]
    
    st.caption(f"Rows remaining: {len(df_temp):,}")
    return df_temp

# ========================= APP LOGIC =========================
with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload File", type=["csv", "xlsx", "xls"])
    if uploaded_file:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        sheet_name = None
        if ext in [".xlsx", ".xls"]:
            _, sheets = read_any_table(uploaded_file)
            sheet_name = st.selectbox("Select sheet:", sheets)

if uploaded_file:
    df, _ = read_any_table(uploaded_file, sheet_name)
    
    with st.sidebar:
        st.markdown("---")
        chart_title_input = st.text_input("Chart Title:", "Ranking Chart")
        st.markdown("---")
        mode = st.radio("Ranking Industries/Buzzwords?", ["Yes", "No"], horizontal=True)

    if mode == "Yes":
        layout = detect_layout(df)
        with st.sidebar:
            st.markdown("---")
            ranking_by = st.radio("Rank by:", ["Count", "Total Amount Raised"])
            amt_cols = find_amount_columns(df.columns)
            amount_choice = st.selectbox("Amount column", ["<None>"] + amt_cols)
            amount_choice = None if amount_choice == "<None>" else amount_choice

            st.markdown("---")
            df_active = apply_multi_filters(df, "ind")

        # Recomputation logic
        if layout["mode"] == "single":
            inds = df_active[layout["ind_col"]].dropna().astype(str).str.split(",").explode().str.strip()
            buzz = df_active[layout["buzz_col"]].dropna().astype(str).str.split(",").explode().str.strip()
            items = pd.concat([inds, buzz])
            counts = items[~items.isin(["","nan"])].value_counts()
            
            if amount_choice:
                def explode_amt(df_in, col):
                    s = df_in[col].astype(str).str.split(",")
                    ex = s.explode().str.strip()
                    mask = ~ex.isin(["","nan"])
                    res = pd.DataFrame({"item": ex[mask]})
                    res["amt"] = np.repeat(pd.to_numeric(df_in[amount_choice], errors='coerce').fillna(0).values, s.str.len())[mask]
                    return res
                combined = pd.concat([explode_amt(df_active, layout["ind_col"]), explode_amt(df_active, layout["buzz_col"])])
                metric_series = combined.groupby("item")["amt"].sum()
            else: metric_series = counts
        else:
            pieces = [pd.DataFrame({c.split(" - ")[1]: df_active[c] for c in layout.get(k, [])}) for k in ["ind_cols", "buzz_cols"]]
            M = coerce_bool_df(pd.concat(pieces, axis=1).groupby(level=0, axis=1).sum())
            if amount_choice:
                amt = pd.to_numeric(df_active[amount_choice], errors='coerce').fillna(0)
                metric_series = M.multiply(amt, axis=0).sum()
            else: metric_series = M.sum()

    else: # Anything mode
        with st.sidebar:
            st.markdown("---")
            analysis_type = st.radio("Analysis:", ["Count Values", "Sum Values"])
            df_active = apply_multi_filters(df, "any")
            
            if analysis_type == "Count Values":
                col = st.selectbox("Column", df.columns)
                explode = st.checkbox("Explode commas")
                if explode:
                    vals = [s.strip() for val in df_active[col].dropna() for s in str(val).split(",") if s.strip()]
                    metric_series = pd.Series(Counter(vals))
                else:
                    metric_series = df_active[col].value_counts()
                ranking_by = "Count"
            else:
                g_col = st.selectbox("Group by", df.columns)
                s_col = st.selectbox("Sum column", df.select_dtypes(include='number').columns)
                is_money = st.toggle("Is Money (£)?", True)
                metric_series = pd.to_numeric(df_active[s_col], errors='coerce').groupby(df_active[g_col].astype(str)).sum()
                ranking_by = "Amount" if not is_money else "Money"

    # Common Ordering and Rendering
    metric_series = metric_series.sort_values(ascending=False)
    full_labels = [str(x) for x in metric_series.index]
    full_values = metric_series.values.tolist()

    with st.sidebar:
        st.markdown("---")
        st.subheader("Visualisation Filtering")
        excluded = st.multiselect("Exclude from chart:", full_labels)
        
        final_labels = [l for l in full_labels if l not in excluded]
        final_values = [v for l, v in zip(full_labels, full_values) if l not in excluded]

        st.markdown("---")
        rank_mode = st.radio("Order:", ["Highest first", "Lowest first", "Custom"])
        top_n = st.number_input("Bars to show", 1, len(final_labels) if final_labels else 1, min(10, len(final_labels) if final_labels else 1))

    if rank_mode == "Highest first":
        l_chart, v_chart = final_labels[:top_n], final_values[:top_n]
        hi = True
    elif rank_mode == "Lowest first":
        l_chart, v_chart = final_labels[::-1][:top_n], final_values[::-1][:top_n]
        hi = False
    else:
        m_map = {l: v for l, v in zip(final_labels, final_values)}
        l_chart, v_chart, hi, _, _ = _drag_order_ui(final_labels, m_map, top_n)

    # Output area
    st.subheader("Chart Preview")
    fmt = money_fmt if "Amount" in ranking_by or "Money" in ranking_by else int_commas
    fig = plot_bar(l_chart, v_chart, chart_title_input, highlight_first=hi, right_formatter=fmt)
    st.pyplot(fig)

    # Download Section
    with st.sidebar:
        st.markdown("---")
        st.header("7. Download Chart")
        
        # Save as SVG
        svg_buf = io.BytesIO()
        fig.savefig(svg_buf, format="svg", bbox_inches="tight")
        st.download_button(
            label="Download as SVG (Vector)",
            data=svg_buf.getvalue(),
            file_name=f"ranklin_chart_{datetime.now().strftime('%Y%m%d')}.svg",
            mime="image/svg+xml"
        )
        
        # Save as PNG
        png_buf = io.BytesIO()
        fig.savefig(png_buf, format="png", bbox_inches="tight", dpi=300)
        st.download_button(
            label="Download as PNG (High Res)",
            data=png_buf.getvalue(),
            file_name=f"ranklin_chart_{datetime.now().strftime('%Y%m%d')}.png",
            mime="image/png"
        )

# Interactive step:
# Would you like me to add a custom color picker to the sidebar so you can change the bar colors on the fly?
