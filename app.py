import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Strangle Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BG_COL   = "#0d1117"
CARD_COL = "#161b22"
TEXT_COL = "#f0f6fc"
GRID_COL = "#30363d"
MUTED    = "#8b949e"

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #f0f6fc; }
    .block-container { padding-top: 4rem; padding-bottom: 1rem; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px 20px;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    div[data-testid="stMetric"] label { font-size: 13px; color: #8b949e !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 26px; font-weight: 700; color: #ffffff !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] * { color: #ffffff !important; }
    div[data-testid="stMetricDelta"] { font-size: 12px; min-height: 20px; color: #ffffff !important; }
    div[data-testid="stMetricDelta"] * { color: #ffffff !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px; color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #f0f6fc !important; }
    h1, h2, h3, h4 { color: #f0f6fc !important; }
    p { color: #8b949e; }
    [data-testid="stSidebar"] { background-color: #161b22; }
</style>
""", unsafe_allow_html=True)

GREEN  = "#39d353"
RED    = "#f85149"
GOLD   = "#e3b341"
BLUE   = "#58a6ff"
PURPLE = "#bc8cff"

def render_table(df):
    st.dataframe(df, use_container_width=True, hide_index=True)

_AXIS = dict(
    gridcolor=GRID_COL, zeroline=False, showline=False,
    tickfont=dict(color=TEXT_COL), title_font=dict(color=TEXT_COL)
)
_LEGEND = dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COL))
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_COL, size=12),
    title_font=dict(color=TEXT_COL),
    margin=dict(l=50, r=20, t=40, b=40),
    xaxis=_AXIS,
    yaxis=_AXIS,
)

# ── Data loaders ──────────────────────────────────────────────────────────────

@st.cache_data
def load_backtest():
    df = pd.read_csv("data/Nifty+Sensex_945.csv")
    df.columns = df.columns.str.strip()
    df['_idx'] = pd.to_numeric(df['Index'], errors='coerce')

    parent = df[df['_idx'] == df['_idx'].apply(np.floor)].copy()
    child  = df[df['_idx'] != df['_idx'].apply(np.floor)].copy()

    parent['PL']      = pd.to_numeric(parent['P/L'], errors='coerce')
    parent['Date']    = pd.to_datetime(parent['Entry Date'].str.strip(), format='mixed', dayfirst=False)
    parent['VIX']     = pd.to_numeric(parent['Vix'].replace('NA', np.nan), errors='coerce')
    parent['idx_str'] = parent['_idx'].astype(int).astype(str)

    child['parent_idx'] = child['_idx'].apply(lambda x: str(int(np.floor(x))))
    child['Strike']     = pd.to_numeric(child['Strike'], errors='coerce')
    child['sl_hit']     = child['Exit Time'].str.strip() != '3:15:00 PM'

    def instr(idx, cdf):
        legs = cdf[cdf['parent_idx'] == str(idx)]
        return 'SENSEX' if (not legs.empty and legs['Strike'].mean() > 40000) else 'NIFTY'

    parent['Instrument'] = parent['idx_str'].apply(lambda x: instr(x, child))

    sl_pp = child.groupby('parent_idx')['sl_hit'].sum().reset_index()
    sl_pp.columns = ['idx_str', 'legs_stopped']
    parent = parent.merge(sl_pp, on='idx_str', how='left')
    parent['legs_stopped'] = parent['legs_stopped'].fillna(0).astype(int)
    parent['instr_cat'] = parent['legs_stopped'].map(
        {0: 'Clean', 1: '50% SL only', 2: '50%SL + BE hit'})

    daily = parent.groupby('Date').agg(
        PL=('PL', 'sum'), VIX=('VIX', 'first')).reset_index().sort_values('Date')
    daily = daily.dropna(subset=['PL']).reset_index(drop=True)
    daily['Cumulative'] = daily['PL'].cumsum()
    daily['Win'] = daily['PL'] > 0

    # Day category
    wide = parent.pivot_table(index='Date', columns='Instrument',
                               values='legs_stopped', aggfunc='first').reset_index()
    wide.columns.name = None
    for col in ['NIFTY', 'SENSEX']:
        if col not in wide.columns:
            wide[col] = 0
    wide = wide.rename(columns={'NIFTY': 'N_SL', 'SENSEX': 'S_SL'})
    wide['N_SL'] = wide['N_SL'].fillna(0).astype(int)
    wide['S_SL'] = wide['S_SL'].fillna(0).astype(int)

    def day_cat(r):
        n, s = r['N_SL'], r['S_SL']
        if n == 0 and s == 0: return 'Both Clean'
        if (n == 1 and s == 0) or (n == 0 and s == 1): return '1 Instr: 50% SL only'
        if n == 1 and s == 1: return 'Both: 50% SL only'
        if (n == 2 and s == 0) or (n == 0 and s == 2): return '1 Instr: 50%+BE hit'
        if (n == 2 and s == 1) or (n == 1 and s == 2): return 'Mixed: 50%+BE + 50%SL'
        if n == 2 and s == 2: return 'Both: 50%+BE hit'
        return 'Other'

    wide['Day_Cat'] = wide.apply(day_cat, axis=1)
    daily = daily.merge(wide[['Date', 'Day_Cat']], on='Date', how='left')

    # Day of week
    daily['DOW'] = daily['Date'].dt.day_name()
    daily['DOW_num'] = daily['Date'].dt.dayofweek  # 0=Mon

    # VIX buckets
    daily['VIX_Bucket'] = pd.cut(
        daily['VIX'],
        bins=[0, 12, 14, 16, 18, 20, 100],
        labels=['<12', '12–14', '14–16', '16–18', '18–20', '>20']
    )

    return daily, parent

@st.cache_data
def load_live():
    df = pd.read_csv("data/live_trades.csv")
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    return df

# ── Load data ─────────────────────────────────────────────────────────────────
bt, bt_parent = load_backtest()
live = load_live()

live_daily = live.drop_duplicates(subset=['Date'])[
    ['Date', 'Day_PL', 'Day_Category',
     'VIX_Open', 'VIX_Close', 'VIX_Change_Pct']].copy()
live_daily = live_daily.sort_values('Date').reset_index(drop=True)
live_daily['Cumulative'] = live_daily['Day_PL'].cumsum()
live_daily['Win'] = live_daily['Day_PL'] > 0

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center; font-size:28px; margin-bottom:4px;'>
    NIFTY + SENSEX &nbsp;|&nbsp; 20&Delta; Short Strangle &nbsp;|&nbsp; 9:45 Entry
</h1>
<p style='text-align:center; color:#8b949e; margin-top:0;'>
    Backtest: Jan 2024 – Jun 2026 (1 lot each) &nbsp;|&nbsp; Live from 11 Jun 2026
</p>
""", unsafe_allow_html=True)

tab_bt, tab_live, tab_compare = st.tabs(["📊 Backtest", "🟢 Live Trading", "🔍 Backtest vs Live"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BACKTEST
# ══════════════════════════════════════════════════════════════════════════════
with tab_bt:

    total_days = len(bt)
    win_days   = bt['Win'].sum()
    loss_days  = total_days - win_days
    win_rate   = win_days / total_days * 100
    avg_win    = bt[bt['Win']]['PL'].mean()
    avg_loss   = bt[~bt['Win']]['PL'].mean()
    total_pl   = bt['PL'].sum()
    pf         = bt[bt['Win']]['PL'].sum() / abs(bt[~bt['Win']]['PL'].sum())
    sharpe     = (bt['PL'].mean() / bt['PL'].std()) * np.sqrt(252)
    roll_max   = bt['Cumulative'].cummax()
    max_dd     = (bt['Cumulative'] - roll_max).min()
    best_day   = bt['PL'].max()
    worst_day  = bt['PL'].min()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Win Rate",       f"{win_rate:.1f}%",              f"{win_days}W / {loss_days}L")
    c2.metric("Total P&L",     f"₹{total_pl:,.0f}",             f"{bt['Date'].min().strftime('%b %Y')} – {bt['Date'].max().strftime('%b %Y')}")
    c3.metric("Sharpe Ratio",  f"{sharpe:.2f}",                  "annualised")
    c4.metric("Profit Factor", f"{pf:.2f}",                      f"Best ₹{best_day:,.0f} / Worst ₹{worst_day:,.0f}")
    c5.metric("Max Drawdown",  f"₹{max_dd:,.0f}",               f"{(max_dd/500000)*100:.1f}% of ₹5L capital")
    c6.metric("Avg Win / Loss", f"{avg_win/abs(avg_loss):.2f}×", f"₹{avg_win:,.0f} / ₹{avg_loss:,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Equity curve
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=bt['Date'], y=bt['Cumulative'],
        mode='lines', line=dict(color=GREEN, width=2),
        fill='tozeroy', fillcolor='rgba(57,211,83,0.1)',
        name='Cumulative P&L', hovertemplate='%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>'
    ))
    fig_eq.add_hline(y=0, line_color=MUTED, line_dash='dash', line_width=0.8)
    fig_eq.update_layout(**PLOT_LAYOUT, height=300,
                          title=dict(text='Cumulative P&L — Backtest', font=dict(size=14)))
    fig_eq.update_xaxes(tickformat='%b %Y')
    fig_eq.update_yaxes(tickprefix='₹', tickformat=',.0f')
    st.plotly_chart(fig_eq, use_container_width=True)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Daily P&L histogram
        fig_hist = go.Figure()
        wins_data   = bt[bt['Win']]['PL']
        losses_data = bt[~bt['Win']]['PL']
        fig_hist.add_trace(go.Histogram(
            x=wins_data, xbins=dict(size=500),
            marker_color=GREEN, opacity=0.85, name='Win days'
        ))
        fig_hist.add_trace(go.Histogram(
            x=losses_data, xbins=dict(size=500),
            marker_color=RED, opacity=0.85, name='Loss days'
        ))
        fig_hist.add_vline(x=avg_win,  line_color=GREEN, line_dash='dot', line_width=1.5)
        fig_hist.add_vline(x=avg_loss, line_color=RED,   line_dash='dot', line_width=1.5)
        fig_hist.add_vline(x=0, line_color='white', line_dash='dash', line_width=0.8)
        fig_hist.update_layout(**PLOT_LAYOUT, height=280, barmode='overlay',
                                title=dict(text='Daily P&L Distribution', font=dict(size=14)),
                                legend=_LEGEND)
        fig_hist.update_xaxes(tickprefix='₹', tickformat=',.0f')
        fig_hist.update_yaxes(title_text='Days')
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_right:
        # Monthly P&L
        bt['Month'] = bt['Date'].dt.to_period('M')
        monthly = bt.groupby('Month')['PL'].sum().reset_index()
        monthly['Month_str'] = monthly['Month'].astype(str)
        monthly['Color'] = monthly['PL'].apply(lambda x: GREEN if x >= 0 else RED)
        fig_m = go.Figure(go.Bar(
            x=monthly['Month_str'], y=monthly['PL'],
            marker_color=monthly['Color'], opacity=0.85,
            hovertemplate='%{x}<br>₹%{y:,.0f}<extra></extra>'
        ))
        fig_m.add_hline(y=0, line_color=MUTED, line_dash='dash', line_width=0.8)
        fig_m.update_layout(**PLOT_LAYOUT, height=280,
                             title=dict(text='Monthly P&L', font=dict(size=14)))
        fig_m.update_xaxes(tickangle=90, tickfont=dict(size=8))
        fig_m.update_yaxes(tickprefix='₹', tickformat=',.0f')
        st.plotly_chart(fig_m, use_container_width=True)

    # Day category breakdown
    st.markdown("#### Day Category Breakdown")
    cat_order = ['Both Clean', '1 Instr: 50% SL only', 'Both: 50% SL only',
                 '1 Instr: 50%+BE hit', 'Mixed: 50%+BE + 50%SL', 'Both: 50%+BE hit']
    cat_colors = [GREEN, '#2ea043', GOLD, BLUE, '#ff7b54', RED]

    rows = []
    for cat in cat_order:
        d = bt[bt['Day_Cat'] == cat]
        if len(d) == 0: continue
        wins_c  = d['Win'].sum()
        losses_c = len(d) - wins_c
        rows.append({
            'Category': cat,
            'Days': len(d),
            'Days (%)': round(len(d)/total_days*100, 1),
            'Win Rate (%)': round(wins_c/len(d)*100, 1),
            'W/L': f"{wins_c}/{losses_c}",
            'Avg Day (₹)': int(round(d['PL'].mean(), 0)),
            'Total P&L (₹)': int(round(d['PL'].sum(), 0)),
            'Contribution (%)': round(d['PL'].sum()/total_pl*100, 1),
        })

    cat_df = pd.DataFrame(rows)

    col_tbl, col_pie = st.columns([3, 2])
    with col_tbl:
        render_table(cat_df)
    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=[r['Category'] for r in rows],
            values=[int(r['Days']) for r in rows],
            marker_colors=cat_colors[:len(rows)],
            hole=0.55,
            textinfo='label+percent',
            textfont=dict(size=10),
            hovertemplate='%{label}<br>%{value} days (%{percent})<extra></extra>'
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, height=280,
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(text='Day Mix', font=dict(size=14))
        )
        st.plotly_chart(fig_pie, use_container_width=True)


    # ── VIX Analysis ─────────────────────────────────────────────────────────
    st.markdown("#### VIX Analysis")

    vix_grp = bt.groupby('VIX_Bucket', observed=True).agg(
        Days=('PL','count'),
        Win_Rate=('Win','mean'),
        Avg_PL=('PL','mean'),
        Total_PL=('PL','sum')
    ).reset_index()
    vix_grp['Win_Rate_pct'] = vix_grp['Win_Rate'] * 100

    col_vb, col_vs = st.columns(2)

    with col_vb:
        fig_vb = go.Figure()
        bar_colors = [GREEN if v >= 0 else RED for v in vix_grp['Avg_PL']]
        fig_vb.add_trace(go.Bar(
            x=vix_grp['VIX_Bucket'].astype(str),
            y=vix_grp['Avg_PL'],
            marker_color=bar_colors, opacity=0.85,
            text=[f"₹{v:,.0f}" for v in vix_grp['Avg_PL']],
            textposition='outside', textfont=dict(color=TEXT_COL),
            hovertemplate='VIX %{x}<br>Avg P&L: ₹%{y:,.0f}<extra></extra>'
        ))
        fig_vb.add_hline(y=0, line_color=MUTED, line_dash='dash', line_width=0.8)
        fig_vb.update_layout(**PLOT_LAYOUT, height=280,
                              title=dict(text='Avg Day P&L by VIX Zone', font=dict(size=14)))
        fig_vb.update_xaxes(title_text='VIX Range')
        fig_vb.update_yaxes(tickprefix='₹', tickformat=',.0f')
        st.plotly_chart(fig_vb, use_container_width=True)

    with col_vs:
        fig_vw = go.Figure()
        fig_vw.add_trace(go.Bar(
            x=vix_grp['VIX_Bucket'].astype(str),
            y=vix_grp['Win_Rate_pct'],
            marker_color=BLUE, opacity=0.85,
            text=[f"{v:.1f}%" for v in vix_grp['Win_Rate_pct']],
            textposition='outside', textfont=dict(color=TEXT_COL),
            hovertemplate='VIX %{x}<br>Win Rate: %{y:.1f}%<extra></extra>'
        ))
        fig_vw.add_hline(y=50, line_color=MUTED, line_dash='dot', line_width=0.8)
        fig_vw.update_layout(**PLOT_LAYOUT, height=280,
                              title=dict(text='Win Rate by VIX Zone', font=dict(size=14)))
        fig_vw.update_xaxes(title_text='VIX Range')
        fig_vw.update_yaxes(title_text='Win Rate %', range=[0, 100])
        st.plotly_chart(fig_vw, use_container_width=True)

    vix_table = vix_grp.copy()
    vix_table['Win Rate (%)']  = vix_table['Win_Rate_pct'].round(1)
    vix_table['Avg P&L (₹)']   = vix_table['Avg_PL'].round(0).astype(int)
    vix_table['Total P&L (₹)'] = vix_table['Total_PL'].round(0).astype(int)
    vix_table['Days (%)']      = (vix_table['Days'] / total_days * 100).round(1)
    render_table(vix_table[['VIX_Bucket','Days','Days (%)','Win Rate (%)','Avg P&L (₹)','Total P&L (₹)']].rename(
        columns={'VIX_Bucket': 'VIX Zone'}))

    # ── Day of Week ───────────────────────────────────────────────────────────
    st.markdown("#### Day of Week Performance")
    st.caption("Tuesday = NIFTY expiry  |  Thursday = SENSEX expiry")

    dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday']
    dow_grp = bt.groupby('DOW').agg(
        Days=('PL','count'),
        Win_Rate=('Win','mean'),
        Avg_PL=('PL','mean'),
        Total_PL=('PL','sum'),
        Best=('PL','max'),
        Worst=('PL','min')
    ).reindex(dow_order).reset_index()
    dow_grp['Win_Rate_pct'] = dow_grp['Win_Rate'] * 100

    expiry_colors = [GOLD if d in ['Tuesday','Thursday'] else BLUE for d in dow_grp['DOW']]

    col_da, col_dw = st.columns(2)

    with col_da:
        fig_da = go.Figure()
        fig_da.add_trace(go.Bar(
            x=dow_grp['DOW'],
            y=dow_grp['Avg_PL'],
            marker_color=expiry_colors, opacity=0.85,
            text=[f"₹{v:,.0f}" for v in dow_grp['Avg_PL']],
            textposition='outside', textfont=dict(color=TEXT_COL),
            hovertemplate='%{x}<br>Avg P&L: ₹%{y:,.0f}<extra></extra>'
        ))
        fig_da.add_hline(y=0, line_color=MUTED, line_dash='dash', line_width=0.8)
        fig_da.update_layout(**PLOT_LAYOUT, height=280,
                              title=dict(text='Avg Day P&L by Weekday  (🟡 = expiry day)', font=dict(size=14)))
        fig_da.update_yaxes(tickprefix='₹', tickformat=',.0f')
        st.plotly_chart(fig_da, use_container_width=True)

    with col_dw:
        fig_dw = go.Figure()
        fig_dw.add_trace(go.Bar(
            x=dow_grp['DOW'],
            y=dow_grp['Win_Rate_pct'],
            marker_color=expiry_colors, opacity=0.85,
            text=[f"{v:.1f}%" for v in dow_grp['Win_Rate_pct']],
            textposition='outside', textfont=dict(color=TEXT_COL),
            hovertemplate='%{x}<br>Win Rate: %{y:.1f}%<extra></extra>'
        ))
        fig_dw.add_hline(y=50, line_color=MUTED, line_dash='dot', line_width=0.8)
        fig_dw.update_layout(**PLOT_LAYOUT, height=280,
                              title=dict(text='Win Rate by Weekday  (🟡 = expiry day)', font=dict(size=14)))
        fig_dw.update_yaxes(title_text='Win Rate %', range=[0, 100])
        st.plotly_chart(fig_dw, use_container_width=True)

    DTE = {
        'Monday':    {'NIFTY DTE': 1, 'SENSEX DTE': 3},
        'Tuesday':   {'NIFTY DTE': 0, 'SENSEX DTE': 2},
        'Wednesday': {'NIFTY DTE': 6, 'SENSEX DTE': 1},
        'Thursday':  {'NIFTY DTE': 5, 'SENSEX DTE': 0},
        'Friday':    {'NIFTY DTE': 4, 'SENSEX DTE': 6},
    }
    dow_table = dow_grp.copy()
    dow_table['Expiry']          = dow_table['DOW'].apply(lambda d: '🟡 NIFTY' if d == 'Tuesday' else ('🟡 SENSEX' if d == 'Thursday' else '—'))
    dow_table['NIFTY DTE']       = dow_table['DOW'].map(lambda d: DTE[d]['NIFTY DTE'])
    dow_table['SENSEX DTE']      = dow_table['DOW'].map(lambda d: DTE[d]['SENSEX DTE'])
    dow_table['Win Rate (%)']    = dow_table['Win_Rate_pct'].round(1)
    dow_table['Avg P&L (₹)']     = dow_table['Avg_PL'].round(0).astype(int)
    dow_table['Total P&L (₹)']   = dow_table['Total_PL'].round(0).astype(int)
    dow_table['Best Day (₹)']    = dow_table['Best'].round(0).astype(int)
    dow_table['Worst Day (₹)']   = dow_table['Worst'].round(0).astype(int)
    render_table(dow_table[['DOW','Expiry','NIFTY DTE','SENSEX DTE','Days','Win Rate (%)','Avg P&L (₹)','Total P&L (₹)','Best Day (₹)','Worst Day (₹)']].rename(
        columns={'DOW': 'Day'}))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LIVE TRADING
# ══════════════════════════════════════════════════════════════════════════════
with tab_live:

    live_days  = len(live_daily)
    live_wins  = live_daily['Win'].sum()
    live_total = live_daily['Day_PL'].sum()
    live_wr    = live_wins / live_days * 100 if live_days > 0 else 0
    bt_avg_day = bt['PL'].mean()
    expected   = bt_avg_day * live_days

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Live Days",        str(live_days),               f"since {live_daily['Date'].min().strftime('%d %b %Y')}" if live_days > 0 else "—")
    c2.metric("Live P&L",        f"₹{live_total:,.0f}",        f"{'↑' if live_total >= 0 else '↓'} vs expected ₹{expected:,.0f}")
    c3.metric("Win Rate",        f"{live_wr:.1f}%",            f"{live_wins}W / {live_days-live_wins}L")
    c4.metric("Backtest Avg/Day",f"₹{bt_avg_day:,.0f}",       "per day expected")

    st.markdown("<br>", unsafe_allow_html=True)

    col_eq, col_vix = st.columns([3, 2])

    with col_eq:
        fig_live = go.Figure()
        # Expected line
        expected_line = [bt_avg_day * (i+1) for i in range(live_days)]
        fig_live.add_trace(go.Scatter(
            x=live_daily['Date'], y=expected_line,
            mode='lines', line=dict(color=MUTED, width=1.5, dash='dot'),
            name='Backtest Expected', hovertemplate='Expected: ₹%{y:,.0f}<extra></extra>'
        ))
        # Actual
        color_actual = GREEN if live_total >= 0 else RED
        fig_live.add_trace(go.Scatter(
            x=live_daily['Date'], y=live_daily['Cumulative'],
            mode='lines+markers', line=dict(color=color_actual, width=2.5),
            marker=dict(size=8, color=color_actual),
            name='Actual', hovertemplate='%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>'
        ))
        fig_live.add_hline(y=0, line_color=MUTED, line_dash='dash', line_width=0.8)
        fig_live.update_layout(**PLOT_LAYOUT, height=280,
                                title=dict(text='Live Cumulative P&L vs Expected', font=dict(size=14)),
                                legend=_LEGEND)
        fig_live.update_yaxes(tickprefix='₹', tickformat=',.0f')
        st.plotly_chart(fig_live, use_container_width=True)

    with col_vix:
        fig_vix = go.Figure()
        bar_colors = [GREEN if p >= 0 else RED for p in live_daily['Day_PL']]
        fig_vix.add_trace(go.Bar(
            x=live_daily['Date'], y=live_daily['Day_PL'],
            marker_color=bar_colors, opacity=0.85, name='Day P&L',
            hovertemplate='%{x|%d %b}<br>₹%{y:,.0f}<extra></extra>'
        ))
        fig_vix.add_trace(go.Scatter(
            x=live_daily['Date'], y=live_daily['VIX_Close'],
            mode='lines+markers', yaxis='y2',
            line=dict(color=GOLD, width=2), marker=dict(size=6),
            name='VIX Close', hovertemplate='VIX: %{y:.2f}<extra></extra>'
        ))
        fig_vix.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_COL, size=12),
            margin=dict(l=50, r=50, t=40, b=40),
            height=280,
            title=dict(text='Day P&L vs VIX', font=dict(size=14, color=TEXT_COL)),
            xaxis=dict(gridcolor=GRID_COL, zeroline=False,
                       tickfont=dict(color=TEXT_COL), title_font=dict(color=TEXT_COL)),
            yaxis=dict(title='P&L (₹)', gridcolor=GRID_COL, tickprefix='₹',
                       zeroline=False, tickfont=dict(color=TEXT_COL),
                       title_font=dict(color=TEXT_COL)),
            yaxis2=dict(title='VIX', overlaying='y', side='right',
                        gridcolor='rgba(0,0,0,0)', zeroline=False,
                        tickfont=dict(color=GOLD), title_font=dict(color=GOLD)),
            legend=_LEGEND,
        )
        st.plotly_chart(fig_vix, use_container_width=True)

    # Trade log
    st.markdown("#### Trade Log")
    log_display = live.copy()
    log_display['Date'] = log_display['Date'].dt.strftime('%d-%b-%Y')
    log_display['PL_fmt'] = log_display['PL'].apply(lambda x: f"₹{x:,.2f}")

    def color_pl(val):
        try:
            v = float(str(val).replace('₹','').replace(',',''))
            return f"color: {'#39d353' if v >= 0 else '#f85149'}"
        except: return ""

    cols_show = ['Date','Index','Type','Strike','Entry_Price','Entry_Time',
                 'Exit_Price','Exit_Time','Exit_Reason','PL','Instr_Category','Day_Category']
    render_table(log_display[cols_show].rename(columns={
        'Entry_Price':'Entry', 'Entry_Time':'E.Time',
        'Exit_Price':'Exit',  'Exit_Time':'X.Time',
        'Exit_Reason':'Reason','Instr_Category':'Instr Cat',
        'Day_Category':'Day Cat'
    }))

    # Day summary
    st.markdown("#### Day Summary")
    day_summary = live_daily.copy()
    day_summary['Date_fmt'] = day_summary['Date'].dt.strftime('%d-%b-%Y (%a)')
    day_summary['Result']   = day_summary['Day_PL'].apply(lambda x: '✅ Win' if x > 0 else '❌ Loss')
    render_table(day_summary[['Date_fmt','Result','Day_PL','Cumulative',
                     'Day_Category','VIX_Open','VIX_Close','VIX_Change_Pct']].rename(
            columns={'Date_fmt':'Date','Day_PL':'Day P&L (₹)',
                     'Cumulative':'Running Total (₹)','Day_Category':'Category',
                     'VIX_Change_Pct':'VIX Chg (%)'}))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("#### Live vs Backtest — Category Distribution")

    bt_cats = bt.groupby('Day_Cat').agg(
        Days=('PL','count'), Total_PL=('PL','sum'), Avg_PL=('PL','mean')
    ).reset_index()
    bt_cats['Win_Rate'] = bt.groupby('Day_Cat')['Win'].mean().values * 100
    bt_cats['Source'] = 'Backtest'

    if live_days > 0:
        live_cat_grp = live_daily.groupby('Day_Category').agg(
            Days=('Day_PL','count'), Total_PL=('Day_PL','sum'), Avg_PL=('Day_PL','mean')
        ).reset_index().rename(columns={'Day_Category':'Day_Cat'})
        live_cat_grp['Win_Rate'] = live_daily.groupby('Day_Category')['Win'].mean().values * 100
        live_cat_grp['Source'] = 'Live'

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Backtest**")
            bt_show = bt_cats[['Day_Cat','Days','Win_Rate','Avg_PL']].copy()
            bt_show['Win_Rate'] = bt_show['Win_Rate'].round(1)
            bt_show['Avg_PL']   = bt_show['Avg_PL'].round(0).astype(int)
            render_table(bt_show.rename(columns={'Day_Cat':'Category','Win_Rate':'Win Rate (%)','Avg_PL':'Avg P&L (₹)'}))

        with col2:
            st.markdown("**Live**")
            live_show = live_cat_grp[['Day_Cat','Days','Win_Rate','Avg_PL']].copy()
            live_show['Win_Rate'] = live_show['Win_Rate'].round(1)
            live_show['Avg_PL']   = live_show['Avg_PL'].round(0).astype(int)
            render_table(live_show.rename(columns={'Day_Cat':'Category','Win_Rate':'Win Rate (%)','Avg_PL':'Avg P&L (₹)'}))

    st.markdown("#### Slippage Tracker")
    st.caption("Difference between live fill prices and backtest assumed prices — to be populated as data grows")

    if live_days >= 5:
        live_avg  = live_daily['Day_PL'].mean()
        bt_avg    = bt['PL'].mean()
        slippage  = live_avg - bt_avg
        c1, c2, c3 = st.columns(3)
        c1.metric("Live Avg/Day",      f"₹{live_avg:,.0f}")
        c2.metric("Backtest Avg/Day",  f"₹{bt_avg:,.0f}")
        c3.metric("Gap (Slippage est)",f"₹{slippage:,.0f}",
                  f"{'Better' if slippage >= 0 else 'Worse'} than backtest")
    else:
        st.info(f"Need at least 5 live days for meaningful slippage estimate. Currently: {live_days} days.")

    st.markdown("#### Running P&L Tracker")
    track_data = {
        'Metric': ['Days traded', 'Wins', 'Losses', 'Win Rate',
                   'Total P&L', 'Avg/Day', 'Backtest Expected', 'vs Expected'],
        'Live': [
            live_days, int(live_wins), int(live_days - live_wins),
            f"{live_wr:.1f}%", f"₹{live_total:,.0f}",
            f"₹{live_daily['Day_PL'].mean():,.0f}" if live_days > 0 else '—',
            f"₹{expected:,.0f}",
            f"₹{live_total - expected:,.0f}"
        ],
        'Backtest': [
            597, 339, 258, '56.8%', '₹2,02,089',
            f"₹{bt_avg_day:,.0f}", '—', '—'
        ]
    }
    render_table(pd.DataFrame(track_data))
