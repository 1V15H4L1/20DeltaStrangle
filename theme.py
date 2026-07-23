"""Central theme — colors, Plotly layout, CSS, and shared UI helpers.

Single source of truth imported by app.py and every dashboard module so the
whole app shares one palette, one chart style, and one set of widgets.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

# ── Palette (GitHub dark) ──────────────────────────────────────────────────────
BG = "#0d1117"
CARD = "#161b22"
TEXT = "#f0f6fc"
GRID = "#30363d"
MUTED = "#8b949e"

GREEN = "#39d353"
RED = "#f85149"
GOLD = "#e3b341"
BLUE = "#58a6ff"
PURPLE = "#bc8cff"

# Back-compat aliases (older modules referenced *_COL names)
BG_COL = BG
CARD_COL = CARD
TEXT_COL = TEXT
GRID_COL = GRID

# ── Plotly layout ───────────────────────────────────────────────────────────────
AXIS = dict(
    gridcolor=GRID, zeroline=False, showline=False,
    tickfont=dict(color=TEXT), title_font=dict(color=TEXT),
)
LEGEND = dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT))
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, size=12),
    title_font=dict(color=TEXT),
    margin=dict(l=50, r=20, t=40, b=40),
    xaxis=AXIS,
    yaxis=AXIS,
)


# ── Formatting ──────────────────────────────────────────────────────────────────
def fmt_inr(v) -> str:
    return f"₹{v:,.0f}"


def render_table(df: pd.DataFrame):
    """Standard full-width, index-less table used across every page."""
    st.dataframe(df, width="stretch", hide_index=True)


# ── Global CSS ──────────────────────────────────────────────────────────────────
def inject_theme():
    """Inject the app-wide stylesheet. Call once, right after set_page_config."""
    st.markdown(
        """
    <style>
        .stApp { background-color: #0d1117; color: #f0f6fc; }
        .block-container { padding-top: 3rem; padding-bottom: 1rem; }

        /* Metric cards */
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

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-radius: 8px; padding: 4px; }
        .stTabs [data-baseweb="tab"] { border-radius: 6px; color: #8b949e; }
        .stTabs [aria-selected="true"] { color: #f0f6fc !important; }

        h1, h2, h3, h4 { color: #f0f6fc !important; }
        p { color: #8b949e; }

        /* Sidebar / navigation */
        [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
        [data-testid="stSidebarNav"] { padding-top: 0.5rem; }
        [data-testid="stSidebarNav"] ul { padding-top: 0.25rem; }
        [data-testid="stSidebarNav"] a { border-radius: 6px; }
        [data-testid="stSidebarNav"] a:hover { background-color: rgba(88,166,255,0.10); }

        /* Page header block */
        .page-header { text-align: center; margin: 0 0 0.25rem 0; }
        .page-header h1 { font-size: 28px; margin-bottom: 4px; }
        .page-header .subtitle { color: #8b949e; margin-top: 0; font-size: 14px; }

        /* Status badge pills */
        .status-badge {
            display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 11px; font-weight: 700; letter-spacing: 0.03em;
            vertical-align: middle; margin-left: 6px;
        }
        .status-badge.live     { background: rgba(57,211,83,0.15);  color: #39d353; border: 1px solid rgba(57,211,83,0.4); }
        .status-badge.backtest { background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid rgba(88,166,255,0.4); }
        .status-badge.paper    { background: rgba(227,179,65,0.15); color: #e3b341; border: 1px solid rgba(227,179,65,0.4); }

        .last-updated { text-align: center; color: #8b949e; font-size: 12px; margin-bottom: 0.5rem; }

        /* Strategy summary cards (Home) */
        .strategy-card {
            background: #161b22; border: 1px solid #30363d; border-radius: 10px;
            padding: 18px 20px; height: 100%;
        }
        .strategy-card .sc-title { font-size: 16px; font-weight: 700; color: #f0f6fc; margin-bottom: 2px; }
        .strategy-card .sc-desc { font-size: 12px; color: #8b949e; margin-bottom: 12px; min-height: 32px; }
        .strategy-card .sc-kpis { display: flex; gap: 18px; flex-wrap: wrap; }
        .strategy-card .sc-kpi .k { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.03em; }
        .strategy-card .sc-kpi .v { font-size: 20px; font-weight: 700; }

        /* Callout box */
        .callout {
            background: #161b22; border: 1px solid #30363d; border-left: 3px solid #58a6ff;
            border-radius: 8px; padding: 14px 18px; margin: 8px 0;
        }
        .callout .c-title { font-size: 13px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.03em; }
        .callout .c-body { font-size: 14px; color: #f0f6fc; margin-top: 4px; }
    </style>
    """,
        unsafe_allow_html=True,
    )


# ── HTML helpers ─────────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str | None = None, badge: str | None = None):
    """Centered page title with optional subtitle line and status badge."""
    badge_html = f'<span class="status-badge {badge.lower()}">{badge.upper()}</span>' if badge else ""
    sub_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="page-header"><h1>{title}{badge_html}</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def status_badge(kind: str) -> str:
    """Return HTML for a LIVE / BACKTEST / PAPER pill (inline use)."""
    return f'<span class="status-badge {kind.lower()}">{kind.upper()}</span>'


def last_updated(ts: datetime | pd.Timestamp | None = None):
    """Render a centered 'last updated' caption."""
    if ts is None:
        return
    if not isinstance(ts, (datetime, pd.Timestamp)):
        ts = pd.Timestamp(ts)
    st.markdown(
        f'<div class="last-updated">Data updated {ts.strftime("%d %b %Y, %I:%M %p")}</div>',
        unsafe_allow_html=True,
    )


def color_for(v: float) -> str:
    return GREEN if v >= 0 else RED


def strategy_card(label: str, description: str, kpis: list[tuple[str, str, str]],
                  page, link_label: str = "Open dashboard →"):
    """Render a strategy summary card with KPIs and a page link.

    kpis: list of (name, value, css_color) tuples.
    page: an st.Page (or url path str) passed straight to st.page_link.
    """
    with st.container(border=False):
        kpi_html = "".join(
            f'<div class="sc-kpi"><div class="k">{k}</div>'
            f'<div class="v" style="color:{c}">{v}</div></div>'
            for k, v, c in kpis
        )
        st.markdown(
            f'<div class="strategy-card">'
            f'<div class="sc-title">{label}</div>'
            f'<div class="sc-desc">{description}</div>'
            f'<div class="sc-kpis">{kpi_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.page_link(page, label=link_label, icon="📂")
