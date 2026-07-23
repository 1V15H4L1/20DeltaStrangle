"""Load Theta Shifting backtest data (mirrors strangle loader shape)."""

from __future__ import annotations

import pandas as pd

from portfolio.algotest_loader import load_algotest_csv
from portfolio.analysis import load_config

SLOT_945 = "9:45"
SLOT_1145 = "11:45"


def load_theta_backtest():
    """Return daily, parent — same columns/shape as strangle load_backtest()."""
    cfg = load_config()
    s = cfg["strategies"]["theta_shifting"]
    rates = cfg.get("charges", {})
    window = cfg.get("comparison_window", {})

    daily, parent = load_algotest_csv(
        s["csv_path"], dayfirst=s.get("dayfirst", False), charge_rates=rates,
    )

    if window.get("start"):
        start = pd.Timestamp(window["start"])
        daily = daily[daily["Date"] >= start]
        parent = parent[parent["Date"] >= start]
    if window.get("end"):
        end = pd.Timestamp(window["end"])
        daily = daily[daily["Date"] <= end]
        parent = parent[parent["Date"] <= end]

    daily = daily.sort_values("Date").reset_index(drop=True)
    daily["Cumulative"] = daily["PL"].cumsum()
    daily["Win"] = daily["PL"] > 0
    daily["DOW"] = daily["Date"].dt.day_name()
    daily["DOW_num"] = daily["Date"].dt.dayofweek

    if "VIX_Bucket" not in daily.columns:
        daily["VIX_Bucket"] = pd.cut(
            daily["VIX"],
            bins=[0, 12, 14, 16, 18, 20, 100],
            labels=["<12", "12–14", "14–16", "16–18", "18–20", ">20"],
        )

    parent = parent.copy()
    parent["legs_stopped"] = parent.get("legs_stopped", 0).fillna(0).astype(int)
    parent["Entry Time"] = parent["Entry Time"].astype(str).str.strip()
    parent["slot"] = parent["Entry Time"].apply(
        lambda t: SLOT_945 if "9:45" in t else (SLOT_1145 if "11:45" in t else "Other")
    )

    wide = parent.pivot_table(
        index="Date", columns="slot", values="legs_stopped", aggfunc="max",
    ).reset_index()
    wide.columns.name = None
    rename = {}
    if SLOT_945 in wide.columns:
        rename[SLOT_945] = "N_SL"
    if SLOT_1145 in wide.columns:
        rename[SLOT_1145] = "S_SL"
    wide = wide.rename(columns=rename)
    for col in ["N_SL", "S_SL"]:
        if col not in wide.columns:
            wide[col] = 0
    wide["N_SL"] = wide["N_SL"].fillna(0).astype(int)
    wide["S_SL"] = wide["S_SL"].fillna(0).astype(int)

    def day_cat(r):
        n, s = r["N_SL"], r["S_SL"]
        if n == 0 and s == 0:
            return "Both Clean"
        if (n == 1 and s == 0) or (n == 0 and s == 1):
            return "1 Instr: 50% SL only"
        if n == 1 and s == 1:
            return "Both: 50% SL only"
        if (n == 2 and s == 0) or (n == 0 and s == 2):
            return "1 Instr: 50%+BE hit"
        if (n == 2 and s == 1) or (n == 1 and s == 2):
            return "Mixed: 50%+BE + 50%SL"
        if n == 2 and s == 2:
            return "Both: 50%+BE hit"
        return "Other"

    wide["Day_Cat"] = wide.apply(day_cat, axis=1)
    daily = daily.merge(wide[["Date", "Day_Cat"]], on="Date", how="left")
    daily["Day_Cat"] = daily["Day_Cat"].fillna("Other")

    return daily, parent
