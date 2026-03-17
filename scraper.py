import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import streamlit as st

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

BASE_URL = "https://www.dataroma.com/m"


def get_page(url, retries=3, delay=2.0):
    session = requests.Session()
    try:
        session.get("https://www.dataroma.com/", headers=HEADERS, timeout=15)
        time.sleep(0.5)
    except Exception:
        pass

    for i in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            time.sleep(delay)
            return r.text, None
        except requests.exceptions.HTTPError as e:
            status = getattr(r, 'status_code', 0)
            if status == 403:
                return None, f"403 Forbidden — DataRoma is blocking this IP/request"
            if i == retries - 1:
                return None, f"HTTP error: {e}"
            time.sleep(delay * 2)
        except Exception as e:
            if i == retries - 1:
                return None, f"Connection error: {e}"
            time.sleep(delay * 2)
    return None, "Max retries exceeded"


@st.cache_data(ttl=3600, show_spinner=False)
def get_superinvestors():
    url = f"{BASE_URL}/managers.php"
    html, err = get_page(url)
    if err:
        return pd.DataFrame(), err

    soup = BeautifulSoup(html, "html.parser")
    managers = []

    table = soup.find("table", {"id": "grid"}) or soup.find("table")
    if not table:
        return pd.DataFrame(), "Could not find manager table on DataRoma page"

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        link = cols[0].find("a")
        if not link:
            continue

        href = link.get("href", "")
        m_id_match = re.search(r"[?&]f=([^&]+)", href)
        manager_id = m_id_match.group(1) if m_id_match else ""
        name = cols[0].get_text(strip=True)
        portfolio_val = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        num_stocks = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        turnover = cols[3].get_text(strip=True) if len(cols) > 3 else ""

        if name and manager_id:
            managers.append({
                "id": manager_id,
                "name": name,
                "portfolio_value": portfolio_val,
                "num_stocks": num_stocks,
                "turnover": turnover,
                "href": href,
            })

    if not managers:
        return pd.DataFrame(), "Parsed page but found 0 managers"

    return pd.DataFrame(managers), None


@st.cache_data(ttl=3600, show_spinner=False)
def get_portfolio(manager_id: str, manager_name: str = ""):
    url = f"{BASE_URL}/holdings.php?f={manager_id}&v=o"
    html, err = get_page(url)
    if err:
        return pd.DataFrame(), err

    soup = BeautifulSoup(html, "html.parser")
    holdings = []

    table = soup.find("table", {"id": "grid"}) or soup.find("table")
    if not table:
        page_text = soup.get_text()[:300].strip()
        return pd.DataFrame(), f"No table found. Page: {page_text[:200]}"

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        ticker_el = cols[0].find("a")
        ticker = ticker_el.get_text(strip=True) if ticker_el else cols[0].get_text(strip=True)
        company = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        pct_portfolio = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        shares = cols[3].get_text(strip=True) if len(cols) > 3 else ""
        reported_price = cols[4].get_text(strip=True) if len(cols) > 4 else ""
        value = cols[5].get_text(strip=True) if len(cols) > 5 else ""
        activity = cols[6].get_text(strip=True) if len(cols) > 6 else ""

        if ticker:
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

    if not holdings:
        page_text = soup.get_text()[:200].strip()
        return pd.DataFrame(), f"Table found but 0 rows. Page snippet: {page_text}"

    return pd.DataFrame(holdings), None


@st.cache_data(ttl=3600, show_spinner=False)
def get_recent_activity():
    url = f"{BASE_URL}/activity.php"
    html, err = get_page(url)
    if err:
        return pd.DataFrame(), err

    soup = BeautifulSoup(html, "html.parser")
    activity = []

    table = soup.find("table", {"id": "grid"}) or soup.find("table")
    if not table:
        return pd.DataFrame(), "No activity table found"

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        manager = cols[0].get_text(strip=True)
        ticker_el = cols[1].find("a")
        ticker = ticker_el.get_text(strip=True) if ticker_el else cols[1].get_text(strip=True)
        company = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        action = cols[3].get_text(strip=True) if len(cols) > 3 else ""
        pct_change = cols[4].get_text(strip=True) if len(cols) > 4 else ""
        date_reported = cols[5].get_text(strip=True) if len(cols) > 5 else ""

        if ticker:
            activity.append({
                "manager": manager,
                "ticker": ticker,
                "company": company,
                "action": action,
                "pct_change": pct_change,
                "date_reported": date_reported,
            })

    if not activity:
        return pd.DataFrame(), "Activity table found but 0 rows"

    return pd.DataFrame(activity), None


@st.cache_data(ttl=7200, show_spinner=False)
def get_aggregated_holdings(manager_ids: list, manager_names: dict):
    all_holdings = []
    errors = {}

    for mid in manager_ids:
        name = manager_names.get(mid, mid)
        df, err = get_portfolio(mid, name)
        if err:
            errors[name] = err
        elif not df.empty:
            all_holdings.append(df)

    if not all_holdings:
        return pd.DataFrame(), errors

    return pd.concat(all_holdings, ignore_index=True), errors
