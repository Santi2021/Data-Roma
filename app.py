import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from scraper import (
    get_superinvestors,
    get_portfolio,
    get_recent_activity,
    get_aggregated_holdings,
)
from analyzer import (
    clean_holdings,
    get_overlap_matrix,
    get_overlap_detail,
    aggregate_by_stock,
    net_activity_by_stock,
    top_stocks_by_conviction,
    manager_summary,
)

st.set_page_config(
    page_title="DataRoma Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary:    #0a0a0a;
    --bg-secondary:  #111111;
    --bg-card:       #161616;
    --bg-hover:      #1e1e1e;
    --border:        #2a2a2a;
    --border-bright: #3a3a3a;
    --orange:        #ff6600;
    --orange-dim:    #cc5200;
    --orange-glow:   rgba(255,102,0,0.15);
    --green:         #00c853;
    --green-dim:     rgba(0,200,83,0.1);
    --red:           #ff3d3d;
    --red-dim:       rgba(255,61,61,0.1);
    --text-primary:  #e8e8e8;
    --text-secondary:#999999;
    --text-dim:      #555555;
    --mono:          'IBM Plex Mono', monospace;
    --sans:          'IBM Plex Sans', sans-serif;
}

html, body, [class*="css"], .stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: var(--sans) !important;
}
section[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * {
    font-family: var(--mono) !important;
    color: var(--text-secondary) !important;
}
.logo-bar { display:flex; align-items:baseline; gap:12px; margin-bottom:4px; }
.logo-main { font-family:var(--mono); font-size:26px; font-weight:600; color:var(--orange); letter-spacing:-.02em; }
.logo-sub  { font-family:var(--mono); font-size:11px; color:var(--text-dim); letter-spacing:.15em; text-transform:uppercase; }
.section-header { display:flex; align-items:center; gap:10px; margin:28px 0 16px 0; padding-bottom:8px; border-bottom:1px solid var(--border); }
.section-label  { font-family:var(--mono); font-size:10px; font-weight:600; letter-spacing:.2em; text-transform:uppercase; color:var(--orange); }
.section-line   { flex:1; height:1px; background:var(--border); }
.metric-row  { display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }
.metric-card { flex:1; min-width:140px; background:var(--bg-card); border:1px solid var(--border); border-top:2px solid var(--orange); padding:14px 18px; }
.metric-label { font-family:var(--mono); font-size:9px; letter-spacing:.18em; text-transform:uppercase; color:var(--text-dim); margin-bottom:6px; }
.metric-value { font-family:var(--mono); font-size:22px; font-weight:600; color:var(--text-primary); line-height:1; }
.metric-delta { font-family:var(--mono); font-size:10px; color:var(--text-secondary); margin-top:4px; }
.debug-box { background:#0d1117; border:1px solid #30363d; border-left:3px solid #ff6600;
             padding:12px 16px; font-family:monospace; font-size:11px; color:#8b949e;
             margin:8px 0; border-radius:2px; white-space:pre-wrap; word-break:break-all; }
.stButton > button { background:transparent !important; border:1px solid var(--orange) !important;
    color:var(--orange) !important; font-family:var(--mono) !important; font-size:11px !important;
    letter-spacing:.1em !important; text-transform:uppercase !important; padding:6px 18px !important; }
.stButton > button:hover { background:var(--orange-glow) !important; }
.stSelectbox > div > div, .stMultiSelect > div > div {
    background:var(--bg-card) !important; border-color:var(--border-bright) !important;
    color:var(--text-primary) !important; font-family:var(--mono) !important; font-size:12px !important; }
.stTabs [data-baseweb="tab-list"] { background:transparent !important; border-bottom:1px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] { background:transparent !important; color:var(--text-secondary) !important;
    font-family:var(--mono) !important; font-size:10px !important; letter-spacing:.15em !important;
    text-transform:uppercase !important; border-radius:0 !important; padding:8px 20px !important; }
.stTabs [aria-selected="true"] { color:var(--orange) !important; border-bottom:2px solid var(--orange) !important; }
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:var(--bg-secondary); }
::-webkit-scrollbar-thumb { background:var(--border-bright); border-radius:3px; }
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
    font=dict(family="IBM Plex Mono", color="#e8e8e8", size=11),
    colorway=["#ff6600", "#00c853", "#3399ff", "#ffcc00", "#cc44ff", "#00cccc"],
    xaxis=dict(gridcolor="#2a2a2a", linecolor="#2a2a2a"),
    yaxis=dict(gridcolor="#2a2a2a", linecolor="#2a2a2a"),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(bgcolor="#111111", bordercolor="#2a2a2a", borderwidth=1),
)

def section_header(label):
    st.markdown(f'<div class="section-header"><span class="section-label">{label}</span>'
                f'<div class="section-line"></div></div>', unsafe_allow_html=True)

def metric_card(label, value, delta=""):
    return (f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div>'
            + (f'<div class="metric-delta">{delta}</div>' if delta else "")
            + '</div>')

def show_error(msg, detail=None):
    st.error(f"⚠️ {msg}")
    if detail:
        st.markdown(f'<div class="debug-box">{detail}</div>', unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="logo-bar"><span class="logo-main">📡 DR</span>'
                '<span class="logo-sub">Intelligence</span></div>'
                '<div style="font-family:var(--mono);font-size:9px;color:#444;'
                'letter-spacing:.1em;margin-bottom:24px;">DATAROMA TERMINAL v1.1</div>',
                unsafe_allow_html=True)
    st.markdown("---")

    nav = st.radio("NAVIGATION", [
        "🏆 Superinvestors", "📋 Portfolio Viewer", "⚡ Recent Activity",
        "🔗 Overlap Analysis", "📊 Aggregate Intelligence", "🔧 Debug"
    ])

    st.markdown("---")
    st.markdown('<div style="font-family:var(--mono);font-size:9px;color:#444;line-height:1.8;">'
                'DATA SOURCE<br><span style="color:#666;">dataroma.com</span><br><br>'
                'CACHE TTL<br><span style="color:#666;">60 min</span></div>', unsafe_allow_html=True)

    if st.button("🔄 Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared!")

# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:2px solid #ff6600;padding-bottom:12px;margin-bottom:24px;">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#555;
                letter-spacing:.2em;text-transform:uppercase;margin-bottom:6px;">
        SMART MONEY TRACKER ◆ REAL-TIME INTELLIGENCE
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:28px;font-weight:600;color:#e8e8e8;">
        DataRoma <span style="color:#ff6600;">Intelligence</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG PAGE
# ══════════════════════════════════════════════════════════════════════════════
if nav == "🔧 Debug":
    section_header("SCRAPER DIAGNOSTICS")
    st.markdown('<div style="font-family:monospace;font-size:11px;color:#666;margin-bottom:16px;">'
                'Use this page to diagnose scraping issues. Shows raw errors from DataRoma requests.'
                '</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Test: Managers page"):
            with st.spinner("Fetching managers.php..."):
                df, err = get_superinvestors()
            if err:
                show_error("Managers fetch failed", err)
            else:
                st.success(f"✅ Got {len(df)} managers")
                st.write("First 3 rows:")
                st.dataframe(df.head(3))
                st.write("Sample IDs and hrefs:")
                st.dataframe(df[["id","name","href"]].head(5))

    with col2:
        if st.button("Test: Activity page"):
            with st.spinner("Fetching activity.php..."):
                df, err = get_recent_activity()
            if err:
                show_error("Activity fetch failed", err)
            else:
                st.success(f"✅ Got {len(df)} activity rows")
                st.dataframe(df.head(5))

    st.markdown("---")
    st.markdown("**Test a specific manager ID:**")
    test_id = st.text_input("Manager ID (e.g. BRK, brk, 0000102796)", value="BRK")
    if st.button("Test: Holdings for this ID"):
        with st.spinner(f"Fetching holdings for ID: {test_id}..."):
            df, err = get_portfolio(test_id, f"Test ({test_id})")
        if err:
            show_error(f"Holdings fetch failed for '{test_id}'", err)
        else:
            st.success(f"✅ Got {len(df)} holdings")
            st.dataframe(df.head(10))

    st.markdown("---")
    st.markdown("**Try manager from actual list:**")
    with st.spinner("Loading managers..."):
        managers_df, merr = get_superinvestors()
    if not managers_df.empty:
        pick = st.selectbox("Pick a manager", managers_df["name"].tolist(), key="dbg_pick")
        row = managers_df[managers_df["name"] == pick].iloc[0]
        st.markdown(f'<div class="debug-box">name: {row["name"]}\nid:   {row["id"]}\nhref: {row["href"]}</div>',
                    unsafe_allow_html=True)
        if st.button("Fetch this manager's holdings"):
            with st.spinner(f"Fetching {row['id']}..."):
                df, err = get_portfolio(row["id"], pick)
            if err:
                show_error(f"Failed for {pick}", err)
            else:
                st.success(f"✅ {len(df)} holdings")
                st.dataframe(df.head(10))


# ══════════════════════════════════════════════════════════════════════════════
# SUPERINVESTORS
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "🏆 Superinvestors":
    section_header("SUPERINVESTOR DIRECTORY")

    with st.spinner("Fetching managers from DataRoma..."):
        managers_df, err = get_superinvestors()

    if err:
        show_error("Could not fetch managers list", err)
        st.stop()

    st.markdown(
        '<div class="metric-row">' +
        metric_card("TOTAL MANAGERS", str(len(managers_df)), "tracked superinvestors") +
        metric_card("DATA SOURCE", "DataRoma", "13F filings") +
        '</div>', unsafe_allow_html=True)

    search = st.text_input("🔍 Filter managers", placeholder="e.g. Buffett, Ackman...", label_visibility="collapsed")
    display_df = managers_df.copy()
    if search:
        display_df = display_df[display_df["name"].str.contains(search, case=False, na=False)]

    st.dataframe(
        display_df[["name", "portfolio_value", "num_stocks", "turnover"]].rename(columns={
            "name": "MANAGER", "portfolio_value": "PORTFOLIO VALUE",
            "num_stocks": "# STOCKS", "turnover": "TURNOVER"}),
        use_container_width=True, height=520, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO VIEWER
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "📋 Portfolio Viewer":
    section_header("PORTFOLIO VIEWER")

    with st.spinner("Loading manager list..."):
        managers_df, err = get_superinvestors()

    if err:
        show_error("Could not fetch managers", err)
        st.stop()

    selected_name = st.selectbox("SELECT MANAGER", options=managers_df["name"].tolist())
    selected_row = managers_df[managers_df["name"] == selected_name].iloc[0]
    manager_id = selected_row["id"]

    with st.spinner(f"Fetching portfolio for {selected_name}..."):
        portfolio_df, err = get_portfolio(manager_id, selected_name)

    if err:
        show_error(f"Could not load holdings for {selected_name}", err)
        st.markdown(f'<div class="debug-box">Manager ID used: {manager_id}\n'
                    f'URL tried: https://www.dataroma.com/m/holdings.php?f={manager_id}&v=o</div>',
                    unsafe_allow_html=True)
        st.stop()

    portfolio_df = clean_holdings(portfolio_df)
    total_val = portfolio_df["value_num"].sum()

    st.markdown(
        '<div class="metric-row">' +
        metric_card("MANAGER", selected_name[:22], f"ID: {manager_id}") +
        metric_card("POSITIONS", str(len(portfolio_df)), "unique stocks") +
        metric_card("PORTFOLIO VALUE", f"${total_val:,.0f}K", "reported value") +
        metric_card("TOP HOLDING", portfolio_df.iloc[0]["ticker"],
                    portfolio_df.iloc[0]["pct_portfolio"]) +
        '</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["TABLE VIEW", "CHART VIEW"])

    with tab1:
        st.dataframe(
            portfolio_df[["ticker","company","pct_portfolio","shares","reported_price","value_000","activity"]].rename(columns={
                "ticker":"TICKER","company":"COMPANY","pct_portfolio":"% PORT",
                "shares":"SHARES","reported_price":"PRICE","value_000":"VALUE ($K)","activity":"ACTIVITY"}),
            use_container_width=True, height=480, hide_index=True)

    with tab2:
        top15 = portfolio_df.head(15)
        fig = go.Figure(go.Bar(
            x=top15["ticker"], y=top15["pct_portfolio_num"],
            marker=dict(color=top15["pct_portfolio_num"],
                        colorscale=[[0,"#1e1e1e"],[0.5,"#cc5200"],[1,"#ff6600"]],
                        line=dict(color="#0a0a0a", width=1)),
            text=top15["pct_portfolio"].astype(str), textposition="outside",
            textfont=dict(family="IBM Plex Mono", size=9, color="#999"),
        ))
        fig.update_layout(title=f"{selected_name} — Top 15 Holdings",
                          yaxis_title="% of Portfolio", **PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

        fig2 = go.Figure(go.Treemap(
            labels=top15["ticker"] + "<br>" + top15["pct_portfolio"].astype(str),
            parents=[""] * len(top15), values=top15["pct_portfolio_num"],
            marker=dict(colorscale=[[0,"#1a0a00"],[1,"#ff6600"]],
                        line=dict(color="#0a0a0a", width=2)),
            textfont=dict(family="IBM Plex Mono", size=11),
        ))
        fig2.update_layout(title="Portfolio Treemap", **PLOTLY_LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# RECENT ACTIVITY
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "⚡ Recent Activity":
    section_header("RECENT ACTIVITY — 13F MOVES")

    with st.spinner("Loading recent activity..."):
        activity_df, err = get_recent_activity()

    if err:
        show_error("Could not fetch activity data", err)
        st.stop()

    def classify_action(a):
        a = str(a).lower()
        if any(k in a for k in ["buy","add","new"]): return "BUY"
        if any(k in a for k in ["sell","reduce","trim","exit"]): return "SELL"
        return "NEUTRAL"

    activity_df["side"] = activity_df["action"].apply(classify_action)
    buys = activity_df[activity_df["side"] == "BUY"]
    sells = activity_df[activity_df["side"] == "SELL"]

    st.markdown(
        '<div class="metric-row">' +
        metric_card("TOTAL MOVES", str(len(activity_df)), "recent 13F activity") +
        metric_card("BUYS / ADDS", f'<span style="color:#00c853">{len(buys)}</span>', "bullish moves") +
        metric_card("SELLS / TRIMS", f'<span style="color:#ff3d3d">{len(sells)}</span>', "bearish moves") +
        metric_card("NET SENTIMENT",
            f'<span style="color:{"#00c853" if len(buys)>len(sells) else "#ff3d3d"}">'
            f'{"BULLISH" if len(buys)>len(sells) else "BEARISH"}</span>',
            f"ratio {len(buys)/(len(sells)+1):.2f}x") +
        '</div>', unsafe_allow_html=True)

    def show_activity_table(df):
        if df.empty:
            st.info("No data.")
            return
        d = df[["manager","ticker","company","action","pct_change","date_reported"]].copy()
        d.columns = ["MANAGER","TICKER","COMPANY","ACTION","% CHANGE","DATE"]
        st.dataframe(d, use_container_width=True, height=420, hide_index=True)

    tab1, tab2, tab3 = st.tabs(["ALL ACTIVITY","🟢 BUYS ONLY","🔴 SELLS ONLY"])
    with tab1:
        f = st.text_input("Filter by manager", placeholder="e.g. Buffett", key="act_f", label_visibility="collapsed")
        shown = activity_df[activity_df["manager"].str.contains(f, case=False, na=False)] if f else activity_df
        show_activity_table(shown)
    with tab2:
        show_activity_table(buys)
    with tab3:
        show_activity_table(sells)


# ══════════════════════════════════════════════════════════════════════════════
# OVERLAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "🔗 Overlap Analysis":
    section_header("PORTFOLIO OVERLAP ANALYSIS")

    with st.spinner("Loading manager list..."):
        managers_df, err = get_superinvestors()
    if err:
        show_error("Could not fetch managers", err)
        st.stop()

    selected_names = st.multiselect(
        "SELECT MANAGERS TO COMPARE", options=managers_df["name"].tolist(),
        default=managers_df["name"].tolist()[:3], max_selections=6)

    if len(selected_names) < 2:
        st.info("Select at least 2 managers to compare.")
        st.stop()

    selected_rows = managers_df[managers_df["name"].isin(selected_names)]
    manager_map = dict(zip(selected_rows["id"], selected_rows["name"]))
    manager_ids = selected_rows["id"].tolist()

    with st.spinner("Fetching portfolios..."):
        combined, errors = get_aggregated_holdings(manager_ids, manager_map)

    if errors:
        with st.expander(f"⚠️ {len(errors)} manager(s) failed to load"):
            for name, err in errors.items():
                st.markdown(f'<div class="debug-box"><b>{name}</b>\n{err}</div>', unsafe_allow_html=True)

    if combined.empty:
        show_error("Could not load any portfolio data. See errors above.")
        st.stop()

    combined = clean_holdings(combined)
    overlap_matrix = get_overlap_matrix(combined)

    section_header("OVERLAP HEATMAP")
    fig = go.Figure(go.Heatmap(
        z=overlap_matrix.values, x=overlap_matrix.columns.tolist(), y=overlap_matrix.index.tolist(),
        colorscale=[[0,"#0a0a0a"],[0.5,"#7a2e00"],[1,"#ff6600"]],
        text=overlap_matrix.values, texttemplate="%{text}",
        textfont=dict(family="IBM Plex Mono", size=12),
        colorbar=dict(tickfont=dict(family="IBM Plex Mono", color="#999", size=10)),
    ))
    fig.update_layout(title="Stocks in Common (count)", **PLOTLY_LAYOUT, height=400)
    st.plotly_chart(fig, use_container_width=True)

    section_header("PAIRWISE OVERLAP DETAIL")
    loaded_managers = combined["manager"].unique().tolist()
    if len(loaded_managers) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            m1 = st.selectbox("Manager A", loaded_managers, key="ov_m1")
        with col2:
            m2 = st.selectbox("Manager B", [n for n in loaded_managers if n != m1], key="ov_m2")
        detail = get_overlap_detail(combined, m1, m2)
        if detail.empty:
            st.info("No overlapping positions between these two managers.")
        else:
            st.caption(f"{len(detail)} stocks in common")
            st.dataframe(detail, use_container_width=True, hide_index=True)
    else:
        st.info("Need at least 2 managers with successful data loads.")


# ══════════════════════════════════════════════════════════════════════════════
# AGGREGATE INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "📊 Aggregate Intelligence":
    section_header("AGGREGATE SMART MONEY INTELLIGENCE")

    with st.spinner("Loading manager list..."):
        managers_df, err = get_superinvestors()
    if err:
        show_error("Could not fetch managers", err)
        st.stop()

    selected_names = st.multiselect(
        "SELECT MANAGERS TO AGGREGATE", options=managers_df["name"].tolist(),
        default=managers_df["name"].tolist()[:5], max_selections=10, key="agg_managers")

    if not selected_names:
        st.info("Select at least one manager.")
        st.stop()

    selected_rows = managers_df[managers_df["name"].isin(selected_names)]
    manager_map = dict(zip(selected_rows["id"], selected_rows["name"]))
    manager_ids = selected_rows["id"].tolist()

    with st.spinner("Fetching and aggregating portfolio data..."):
        combined, errors = get_aggregated_holdings(manager_ids, manager_map)

    if errors:
        with st.expander(f"⚠️ {len(errors)} manager(s) failed — click to see details"):
            for name, err in errors.items():
                st.markdown(f'<div class="debug-box"><b>{name}</b>\n{err}</div>', unsafe_allow_html=True)

    if combined.empty:
        show_error("Could not load any data. Check the Debug page for details.")
        st.stop()

    combined = clean_holdings(combined)
    agg = aggregate_by_stock(combined)
    conviction = top_stocks_by_conviction(combined, top_n=20)
    loaded_count = combined["manager"].nunique()

    st.markdown(
        '<div class="metric-row">' +
        metric_card("MANAGERS LOADED", str(loaded_count), f"of {len(selected_names)} selected") +
        metric_card("UNIQUE POSITIONS", str(agg["ticker"].nunique()), "distinct stocks") +
        metric_card("MOST HELD", agg.iloc[0]["ticker"] if not agg.empty else "-",
                    f"{agg.iloc[0]['num_managers']} managers" if not agg.empty else "") +
        '</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🏆 CONVICTION PLAYS","📈 NET ACTIVITY FLOW","🗂 FULL AGGREGATE"])

    with tab1:
        section_header("TOP CONVICTION STOCKS")
        st.caption("Ranked by: (# managers holding) × (avg % portfolio weight)")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=conviction["ticker"], y=conviction["num_managers"],
            name="# Managers", marker_color="#ff6600", yaxis="y"))
        fig.add_trace(go.Scatter(x=conviction["ticker"], y=conviction["avg_pct_portfolio"],
            name="Avg % Portfolio", mode="lines+markers",
            marker=dict(color="#00c853", size=7, symbol="diamond"),
            line=dict(color="#00c853", width=1.5), yaxis="y2"))
        fig.update_layout(
            title="Conviction Stocks — Manager Count vs Avg Weight",
            yaxis=dict(title="# Managers", gridcolor="#2a2a2a", color="#ff6600"),
            yaxis2=dict(title="Avg % Portfolio", overlaying="y", side="right",
                        gridcolor="rgba(0,0,0,0)", color="#00c853"),
            **PLOTLY_LAYOUT, height=420)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            conviction[["ticker","company","num_managers","avg_pct_portfolio","max_pct_portfolio","conviction_score"]].rename(columns={
                "ticker":"TICKER","company":"COMPANY","num_managers":"# MANAGERS",
                "avg_pct_portfolio":"AVG % PORT","max_pct_portfolio":"MAX % PORT","conviction_score":"CONVICTION SCORE"}),
            use_container_width=True, hide_index=True)

    with tab2:
        section_header("NET BUYING / SELLING FLOW BY STOCK")
        with st.spinner("Loading activity..."):
            activity_df, aerr = get_recent_activity()
        if aerr:
            show_error("Activity data unavailable", aerr)
        elif not activity_df.empty:
            net_act = net_activity_by_stock(activity_df)
            if not net_act.empty:
                top_n = net_act.reindex(net_act["net_score"].abs().sort_values(ascending=False).index).head(25)
                colors = ["#00c853" if v > 0 else ("#ff3d3d" if v < 0 else "#555") for v in top_n["net_score"]]
                fig = go.Figure(go.Bar(
                    x=top_n["ticker"], y=top_n["net_score"], marker_color=colors,
                    marker_line=dict(color="#0a0a0a", width=1),
                    text=top_n["net_score"].apply(lambda v: f"+{v}" if v > 0 else str(v)),
                    textposition="outside", textfont=dict(family="IBM Plex Mono", size=9, color="#999"),
                ))
                fig.add_hline(y=0, line_color="#3a3a3a", line_width=1)
                fig.update_layout(title="Net Activity Score (Buys − Sells)", **PLOTLY_LAYOUT, height=420)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    net_act[["ticker","company","BUY","SELL","net_score","total_activity"]].rename(columns={
                        "ticker":"TICKER","company":"COMPANY","BUY":"BUYS","SELL":"SELLS",
                        "net_score":"NET SCORE","total_activity":"TOTAL MOVES"}),
                    use_container_width=True, hide_index=True, height=380)

    with tab3:
        section_header("FULL AGGREGATED HOLDINGS TABLE")
        s = st.text_input("Search ticker/company", placeholder="e.g. AAPL", key="agg_s", label_visibility="collapsed")
        d = agg.copy()
        if s:
            d = d[d["ticker"].str.contains(s, case=False, na=False) | d["company"].str.contains(s, case=False, na=False)]
        st.dataframe(
            d[["ticker","company","num_managers","managers","avg_pct_portfolio","total_value_000"]].rename(columns={
                "ticker":"TICKER","company":"COMPANY","num_managers":"# MANAGERS",
                "managers":"HELD BY","avg_pct_portfolio":"AVG % PORT","total_value_000":"TOTAL VALUE ($K)"}),
            use_container_width=True, height=520, hide_index=True)
