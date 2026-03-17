import pandas as pd
import numpy as np
from collections import defaultdict


def parse_pct(val: str) -> float:
    """Convert '12.5%' or '12.5' to float."""
    if not val:
        return 0.0
    val = str(val).replace("%", "").replace(",", "").strip()
    try:
        return float(val)
    except ValueError:
        return 0.0


def parse_value(val: str) -> float:
    """Convert '$1,234,567' to float in thousands."""
    if not val:
        return 0.0
    val = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(val)
    except ValueError:
        return 0.0


def clean_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and normalize holdings dataframe."""
    if df.empty:
        return df
    df = df.copy()
    df["pct_portfolio_num"] = df["pct_portfolio"].apply(parse_pct)
    df["value_num"] = df["value_000"].apply(parse_value)
    df["reported_price_num"] = df["reported_price"].apply(lambda x: parse_value(str(x)))
    return df


def get_overlap_matrix(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build an overlap matrix between managers.
    Each cell = number of stocks in common.
    """
    if holdings_df.empty:
        return pd.DataFrame()

    managers = holdings_df["manager"].unique().tolist()
    matrix = pd.DataFrame(index=managers, columns=managers, data=0)

    manager_tickers = {
        m: set(holdings_df[holdings_df["manager"] == m]["ticker"].tolist())
        for m in managers
    }

    for m1 in managers:
        for m2 in managers:
            overlap = len(manager_tickers[m1] & manager_tickers[m2])
            matrix.loc[m1, m2] = overlap

    return matrix.astype(int)


def get_overlap_detail(holdings_df: pd.DataFrame, m1: str, m2: str) -> pd.DataFrame:
    """Get stocks held by both m1 and m2."""
    tickers_m1 = set(holdings_df[holdings_df["manager"] == m1]["ticker"])
    tickers_m2 = set(holdings_df[holdings_df["manager"] == m2]["ticker"])
    common = tickers_m1 & tickers_m2

    rows = []
    for t in sorted(common):
        row_m1 = holdings_df[(holdings_df["manager"] == m1) & (holdings_df["ticker"] == t)].iloc[0]
        row_m2 = holdings_df[(holdings_df["manager"] == m2) & (holdings_df["ticker"] == t)].iloc[0]
        rows.append({
            "ticker": t,
            "company": row_m1["company"],
            f"% port ({m1[:15]})": row_m1["pct_portfolio"],
            f"% port ({m2[:15]})": row_m2["pct_portfolio"],
        })

    return pd.DataFrame(rows)


def aggregate_by_stock(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate all holdings by ticker.
    Shows how many managers hold each stock, total value, avg % portfolio.
    """
    if holdings_df.empty:
        return pd.DataFrame()

    df = clean_holdings(holdings_df)

    agg = df.groupby(["ticker", "company"]).agg(
        num_managers=("manager", "nunique"),
        managers=("manager", lambda x: ", ".join(sorted(x.unique()))),
        total_value_000=("value_num", "sum"),
        avg_pct_portfolio=("pct_portfolio_num", "mean"),
        max_pct_portfolio=("pct_portfolio_num", "max"),
    ).reset_index()

    agg = agg.sort_values("num_managers", ascending=False)
    return agg


def net_activity_by_stock(activity_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize net buying/selling pressure per stock across all managers.
    Returns: ticker, company, net_buyers, net_sellers, net_score
    """
    if activity_df.empty:
        return pd.DataFrame()

    df = activity_df.copy()
    df["action_clean"] = df["action"].str.lower().str.strip()

    buy_keywords = ["buy", "add", "new"]
    sell_keywords = ["sell", "reduce", "trim", "exit"]

    def classify(a):
        for kw in buy_keywords:
            if kw in a:
                return "BUY"
        for kw in sell_keywords:
            if kw in a:
                return "SELL"
        return "NEUTRAL"

    df["side"] = df["action_clean"].apply(classify)

    summary = df.groupby(["ticker", "company", "side"]).size().unstack(fill_value=0).reset_index()
    for col in ["BUY", "SELL", "NEUTRAL"]:
        if col not in summary.columns:
            summary[col] = 0

    summary["net_score"] = summary["BUY"] - summary["SELL"]
    summary["total_activity"] = summary["BUY"] + summary["SELL"] + summary["NEUTRAL"]
    summary = summary.sort_values("net_score", ascending=False)
    return summary


def top_stocks_by_conviction(holdings_df: pd.DataFrame, top_n=20) -> pd.DataFrame:
    """Top stocks by number of managers + avg weight in portfolio."""
    agg = aggregate_by_stock(holdings_df)
    if agg.empty:
        return agg
    # Conviction score: managers * avg_pct
    agg["conviction_score"] = agg["num_managers"] * agg["avg_pct_portfolio"]
    return agg.sort_values("conviction_score", ascending=False).head(top_n)


def manager_summary(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Summary stats per manager."""
    if holdings_df.empty:
        return pd.DataFrame()
    df = clean_holdings(holdings_df)
    return df.groupby("manager").agg(
        num_stocks=("ticker", "nunique"),
        total_value_000=("value_num", "sum"),
        top_holding=("ticker", lambda x: x.iloc[0] if len(x) > 0 else ""),
    ).reset_index().sort_values("total_value_000", ascending=False)
