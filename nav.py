"""Navigation registry — builds the st.Page objects for the multipage app.

Kept separate from app.py so pages can be referenced from home.py (for the
strategy cards' page links) without importing the entry script. home.py reads
CURRENT_STRATEGY_PAGES lazily at render time to avoid an import cycle.
"""

from __future__ import annotations

import streamlit as st

from home import render_home
from portfolio.dashboard import render_portfolio_dashboard
from strangle.dashboard import render_strangle_dashboard
from theta.dashboard import render_theta_dashboard

# Populated by build_pages() each run; read lazily by home.render_home().
CURRENT_STRATEGY_PAGES: dict = {}


def _portfolio_page():
    render_portfolio_dashboard(embedded=True)


def build_pages():
    """Create fresh st.Page objects for this script run.

    Returns (pages_dict_for_st_navigation, {config_key: st.Page}).
    """
    global CURRENT_STRATEGY_PAGES

    home = st.Page(render_home, title="Overview", icon="📊", default=True, url_path="home")
    strangle = st.Page(render_strangle_dashboard, title="20Δ Short Strangle", icon="📉", url_path="strangle")
    theta = st.Page(render_theta_dashboard, title="Theta Shifting", icon="🔀", url_path="theta")
    portfolio = st.Page(_portfolio_page, title="Portfolio", icon="🧬", url_path="portfolio")

    pages = {
        "": [home],
        "Strategies": [strangle, theta],
        "Analytics": [portfolio],
    }
    CURRENT_STRATEGY_PAGES = {"strangle_20d": strangle, "theta_shifting": theta}
    return pages, CURRENT_STRATEGY_PAGES
