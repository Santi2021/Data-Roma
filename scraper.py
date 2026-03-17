import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime
import streamlit as st

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.dataroma.com/",
}

BASE_URL = "https://www.dataroma.com/m"


def get_page(url, retries=3, delay=1.5):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            time.sleep(delay)
            return r.text
        except Exception as e:
            if i == retries - 1:
                raise e
            time.sleep(delay * 2)
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_superinvestors():
    """Scrape list of all superinvestors from DataRoma."""
    url = f"{BASE_URL}/managers.php"
    html = get_page(url)
    soup = BeautifulSoup(html, "html.parser")

    managers = []
    table = soup.find("table", {"id": "grid"})
    if not table:
        return pd.DataFrame()

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        link = cols[0].find("a")
        if not link:
            continue
        href = link.get("href", "")
        m_id = re.search(r"f=([^&]+)", href)
        manager_id = m_id.group(1) if m_id else ""

        name = cols[0].get_text(strip=True)
        portfolio_val = cols[1].get_text(strip=True)
        num_stocks = cols[2].get_text(strip=True)
        turnover = cols[3].get_text(strip=True)

        managers.append({
            "id": manager_id,
            "name": name,
            "portfolio_value": portfolio_val,
            "num_stocks": num_stocks,
            "turnover": turnover,
        })

    return pd.DataFrame(managers)


@st.cache_data(ttl=3600, show_spinner=False)
def get_portfolio(manager_id: str, manager_name: str = ""):
    """Scrape holdings for a specific manager."""
    url = f"{BASE_URL}/holdings.php?f={manager_id}&v=o"
    html = get_page(url)
    soup = BeautifulSoup(html, "html.parser")

    holdings = []
    table = soup.find("table", {"id": "grid"})
    if not table:
        return pd.DataFrame()

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        ticker_el = cols[0].find("a")
        ticker = ticker_el.get_text(strip=True) if ticker_el else cols[0].get_text(strip=True)
        company = cols[1].get_text(strip=True)
        pct_portfolio = cols[2].get_text(strip=True)
        shares = cols[3].get_text(strip=True)
        reported_price = cols[4].get_text(strip=True)
        value = cols[5].get_text(strip=True)
        activity = cols[6].get_text(strip=True) if len(cols) > 6 else ""

        holdings.append({
            "manager_id": manager_id,
            "manager": manager_name,
            "ticker": ticker,
            "company": company,
            "pct_portfolio": pct_portfolio,
            "shares": shares,
            "reported_price": reported_price,
            "value_000": value,
            "activity": activity,
        })

    return pd.DataFrame(holdings)


@st.cache_data(ttl=3600, show_spinner=False)
def get_recent_activity(manager_id: str = None):
    """Scrape recent buys/sells. If manager_id given, filter to that manager."""
    if manager_id:
        url = f"{BASE_URL}/activity.php?f={manager_id}"
    else:
        url = f"{BASE_URL}/activity.php"

    html = get_page(url)
    soup = BeautifulSoup(html, "html.parser")

    activity = []
    table = soup.find("table", {"id": "grid"})
    if not table:
        return pd.DataFrame()

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 6:
            continue

        manager = cols[0].get_text(strip=True)
        ticker_el = cols[1].find("a")
        ticker = ticker_el.get_text(strip=True) if ticker_el else cols[1].get_text(strip=True)
        company = cols[2].get_text(strip=True)
        action = cols[3].get_text(strip=True)
        pct_change = cols[4].get_text(strip=True)
        date_reported = cols[5].get_text(strip=True)

        activity.append({
            "manager": manager,
            "ticker": ticker,
            "company": company,
            "action": action,
            "pct_change": pct_change,
            "date_reported": date_reported,
        })

    return pd.DataFrame(activity)


@st.cache_data(ttl=7200, show_spinner=False)
def get_aggregated_holdings(manager_ids: list, manager_names: dict):
    """Fetch portfolios for multiple managers and combine them."""
    all_holdings = []
    for mid in manager_ids:
        name = manager_names.get(mid, mid)
        try:
            df = get_portfolio(mid, name)
            if not df.empty:
                all_holdings.append(df)
        except Exception:
            continue

    if not all_holdings:
        return pd.DataFrame()

    return pd.concat(all_holdings, ignore_index=True)
