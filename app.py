import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import io, os
from collections import Counter
from datetime import datetime

# ========================= CONFIGURATION =========================
# Ensuring fonts stay as editable text for Adobe Illustrator
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['svg.fonttype'] = 'none' 
mpl.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans', 'sans-serif']

APP_TITLE_COLOR = '#000000'
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
    .apply-btn button {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
        height: 3.5rem !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# ========================= CACHED ENGINES =========================

@st.cache_data
def load_data(file, sheet_name=None):
    ext = os.path.splitext(file.name)[1].lower()
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(file, sheet_name=sheet_name, engine="openpyxl" if ext == ".xlsx" else "xlrd")
    try:
        return pd.read_csv(file)
    except:
        return pd.read_csv(file, encoding="latin-1")

@st.cache_data
def process_industry_buzzword(df_active, layout, amount_choice=None):
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
                amts = pd.to_numeric(df_in[amount_choice], errors='coerce').fillna(0).values
                res["amt"] = np.repeat(amts, s.str.len())[mask]
                return res
            combined = pd.concat([explode_amt(df_active, layout["ind_col"]), explode_amt(df_active, layout["buzz_col"])])
            return combined.groupby("item")["amt"].sum()
        return counts
    else:
        pieces = []
        cols_to_process = layout.get("ind_cols", []) + layout.get("buzz_cols", [])
        if not cols_to_process: return pd.Series(dtype=float)
        for c in cols_to_process:
            if c in df_active.columns:
                name = c.split(" - ", 1)[-1]
                pieces.append(df_active[c].rename(name))
        if not pieces: return pd.Series(dtype=float)
        M = pd.concat(pieces, axis=1).groupby(level=0, axis=1).sum()
        M = (M.fillna(0) != 0) 
        if amount_choice:
            amt = pd.to_numeric(df_active[amount_choice], errors='coerce').fillna(0)
            return M.multiply(amt, axis=0).sum()
        return M.sum()

@st.cache_data
def process_generic_explode(df_active, target_col):
    """Cached function to split and count comma-separated strings"""
    s = df_active[target_col].dropna().astype(str).str.split(",")
    ex = s.explode().str.strip()
    return ex[~ex.isin(["","nan", "None"])].value_counts()

# ========================= HELPERS =========================

def money_fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v == 0: return "£0"
    if v >= 1e9: return f"£{v/1e9:.1f}b"
    if v >= 1e6: return f"£{v/1e6:.1f}m"
    if v >= 1e3: return f"£{v/1e3:.1f}k"
    return f"£{v:.0f}"

def plot_bar(labels, values, title, highlight_first=True, right_formatter=lambda x: str(x)):
    fig, ax = plt.subplots(figsize=(10, 6))
    if not labels: return fig
    max_val = max(values) if values else 1
    y_pos = list(range(len(labels)))
    ax.barh(y_pos, [max_val] * len(values), color='#E0E0E0', height=0.8)
    for i, (y, v) in enumerate(zip(y_pos, values)):
        color = '#4B4897' if (highlight_first and i == 0) else '#A4A2F2'
        ax.barh(y, float(v), color=color, height=0.8)
    ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.xaxis.set_visible(False)
    offset = max_val * 0.015
    for i, (label, v) in enumerate(zip(labels, values)):
        text_c = 'white' if (highlight_first and i == 0) else 'black'
        ax.text(offset, i, str(label), va='center', color=text_c, fontsize=11)
        ax.text(max_val - offset, i, right_formatter(v), va='center', ha='right', color=text_c, fontweight='bold')
    ax.set_title(title, fontsize=14, pad=20)
    ax.invert_yaxis()
    return fig

def detect_layout(df):
    cols = list(df.columns.astype(str))
    ind_s = "Industries" if "Industries" in cols else ("(Company) Industries" if "(Company) Industries" in cols else None)
    buzz_s = "Buzzwords" if "Buzzwords" in cols else ("(Company) Buzzwords" if "(Company) Buzzwords" in cols else None)
    ind_w = [c for c in cols if "Industries - " in c]
    buzz_w = [c for c in cols if "Buzzwords - " in c]
    if ind_s and buzz_s: return {"mode": "single", "ind_col": ind_s, "buzz_col": buzz_s}
    if ind_w or buzz_w: return {"mode": "wide", "ind_cols": ind_w, "buzz_cols": buzz_w}
    return {"mode": "unknown"}

def find_amount_columns(cols):
    return [c for c in cols if any(x in c.lower() for x in ["amount raised", "gbp", "converted to gbp"])]

# ========================= APP START =========================

st.markdown(f'<h1 style="color:{APP_TITLE_COLOR};">Ranklin</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload File", type=["csv", "xlsx", "xls"])
    sheet_name = None
    if uploaded_file and os.path.splitext(uploaded_file.name)[1].lower() in [".xlsx", ".xls"]:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = st.selectbox("Select sheet:", xls.sheet_names)

if uploaded_file:
    df = load_data(uploaded_file, sheet_name)
    
    with st.sidebar:
        st.markdown("---")
        chart_title = st.text_input("Chart Title:", "Ranking Chart")
        
        st.header("2. Analysis Options")
        mode = st.radio("Ranking Industries/Buzzwords?", ["Yes", "No"], horizontal=True)
        
        if mode == "No":
            analysis_type = st.radio("Analysis Type:", ["Count", "Sum"], horizontal=True)
            target_col = st.selectbox("Select Column to Rank", df.columns)
            # Re-adding the Explode option for generic columns
            explode_enabled = st.checkbox("Explode comma-separated values", help="Split values like 'Apple, Orange' into separate counts")
            if analysis_type == "Sum":
                sum_col = st.selectbox("Numeric Column to Sum", df.select_dtypes(include='number').columns)
        else:
            ranking_by = st.radio("Rank by:", ["Count", "Total Amount Raised"], horizontal=True)
            amt_choice_raw = st.selectbox("Amount column", ["<None>"] + find_amount_columns(df.columns))
            amount_choice = None if amt_choice_raw == "<None>" else amt_choice_raw

        st.markdown("---")
        st.header("3. Raw Data Filters")
        if 'rules' not in st.session_state: st.session_state.rules = []
        
        c1, c2 = st.columns(2)
        if c1.button("➕ Add"): st.session_state.rules.append({'col': df.columns[0], 'mode': 'Include', 'vals': []})
        if c2.button("➖ Rem"): 
            if st.session_state.rules: st.session_state.rules.pop()

        for i, rule in enumerate(st.session_state.rules):
            with st.expander(f"Filter {i+1}: {rule['col']}"):
                rule['col'] = st.selectbox("Column", df.columns, key=f"f_col_{i}")
                rule['mode'] = st.radio("Action", ["Include", "Exclude"], key=f"f_mode_{i}", horizontal=True)
                opts = sorted(df[rule['col']].astype(str).unique().tolist())
                rule['vals'] = st.multiselect("Select Values", opts, key=f"f_vals_{i}")

        st.markdown('<div class="apply-btn">', unsafe_allow_html=True)
        apply_trigger = st.button("🚀 APPLY CHANGES", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Filtering Execution
    if apply_trigger or 'df_active' not in st.session_state:
        df_active = df.copy()
        for rule in st.session_state.rules:
            if rule['vals']:
                mask = df_active[rule['col']].astype(str).isin(rule['vals'])
                df_active = df_active[mask] if rule['mode'] == "Include" else df_active[~mask]
        st.session_state.df_active = df_active

    df_active = st.session_state.df_active

    # --- CALCULATION LOGIC ---
    if mode == "Yes":
        layout = detect_layout(df_active)
        if layout["mode"] == "unknown":
            st.error("Could not find Industry or Buzzword columns.")
            st.stop()
        metric_series = process_industry_buzzword(df_active, layout, amount_choice if ranking_by != "Count" else None)
        agg_label = ranking_by
    else:
        if analysis_type == "Sum":
            metric_series = df_active.groupby(target_col)[sum_col].sum()
            agg_label = "Sum"
        else:
            if explode_enabled:
                metric_series = process_generic_explode(df_active, target_col)
            else:
                metric_series = df_active[target_col].value_counts()
            agg_label = "Count"

    # --- CHART OPTIONS ---
    metric_series = metric_series.sort_values(ascending=False)
    
    with st.sidebar:
        st.markdown("---")
        st.header("4. View Options")
        exclude = st.multiselect("Exclude from chart:", metric_series.index.tolist())
        final_series = metric_series.drop(exclude, errors='ignore')
        
        top_n = st.number_input("Number of bars", 1, max(1, len(final_series)), min(10, max(1, len(final_series))))
        rank_mode = st.radio("Order:", ["Highest first", "Lowest first"], horizontal=True)

    l_chart = final_series.index.tolist()
    v_chart = final_series.values.tolist()
    if rank_mode == "Lowest first": l_chart, v_chart = l_chart[::-1][:top_n], v_chart[::-1][:top_n]
    else: l_chart, v_chart = l_chart[:top_n], v_chart[:top_n]

    # --- MAIN DISPLAY ---
    st.subheader(f"Analysis Results ({len(df_active):,} rows)")
    if not l_chart:
        st.warning("No data found.")
    else:
        is_money = (mode == "Yes" and ranking_by != "Count") or (mode == "No" and analysis_type == "Sum")
        fmt = money_fmt if is_money else lambda x: f"{int(x):,}"
        fig = plot_bar(l_chart, v_chart, chart_title, highlight_first=(rank_mode=="Highest first"), right_formatter=fmt)
        st.pyplot(fig)

    with st.sidebar:
        st.markdown("---")
        st.header("5. Download")
        col_a, col_b = st.columns(2)
        svg_b = io.BytesIO(); fig.savefig(svg_b, format="svg", bbox_inches="tight", transparent=True)
        col_a.download_button("SVG (Adobe)", svg_b.getvalue(), "chart.svg", "image/svg+xml")
        png_b = io.BytesIO(); fig.savefig(png_b, format="png", bbox_inches="tight", dpi=300)
        col_b.download_button("PNG (High Res)", png_b.getvalue(), "chart.png", "image/png")
else:
    st.info("Please upload a file to begin.")
