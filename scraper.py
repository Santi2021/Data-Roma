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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
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
            status = getattr(r, "status_code", 0)
            if status == 403:
                return None, "403 Forbidden — DataRoma is blocking this IP"
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
    """
    Scrape managers from managers.php.
    Table id="grid", columns: td.man (name+link), td.val (portfolio value), td.cnt (# stocks)
    Holdings URL: /m/holdings.php?m=<id>  (e.g. ?m=AKO, ?m=BRK)
    """
    url = f"{BASE_URL}/managers.php"
    html, err = get_page(url)
    if err:
        return pd.DataFrame(), err

    soup = BeautifulSoup(html, "html.parser")
    managers = []

    table = soup.find("table", {"id": "grid"})
    if not table:
        return pd.DataFrame(), "Could not find table#grid on managers.php"

    rows = table.find_all("tr")
    for row in rows:
        # Manager name is in td.man
        man_td = row.find("td", class_="man")
        if not man_td:
            continue
        link = man_td.find("a", href=True)
        if not link:
            continue

        href = link.get("href", "")
        # Extract ?m=XXX
        m = re.search(r"[?&]m=([^&]+)", href)
        if not m:
            continue
        manager_id = m.group(1)
        name = link.get_text(strip=True)

        val_td = row.find("td", class_="val")
        cnt_td = row.find("td", class_="cnt")
        portfolio_val = val_td.get_text(strip=True) if val_td else ""
        num_stocks = cnt_td.get_text(strip=True) if cnt_td else ""

        managers.append({
            "id": manager_id,
            "name": name,
            "portfolio_value": portfolio_val,
            "num_stocks": num_stocks,
        })

    if not managers:
        return pd.DataFrame(), "Parsed managers.php but found 0 rows"

    return pd.DataFrame(managers), None


@st.cache_data(ttl=3600, show_spinner=False)
def get_portfolio(manager_id: str, manager_name: str = ""):
    """Holdings URL: /m/holdings.php?m=<id>"""
    url = f"{BASE_URL}/holdings.php?m={manager_id}"
    html, err = get_page(url)
    if err:
        return pd.DataFrame(), err

    soup = BeautifulSoup(html, "html.parser")
    holdings = []

    table = soup.find("table", {"id": "grid"}) or soup.find("table")
    if not table:
        snippet = soup.get_text()[:300].strip()
        return pd.DataFrame(), f"No table found. Page snippet: {snippet[:200]}"

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        ticker_el = cols[0].find("a")
        ticker        = ticker_el.get_text(strip=True) if ticker_el else cols[0].get_text(strip=True)
        company       = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        pct_portfolio = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        shares        = cols[3].get_text(strip=True) if len(cols) > 3 else ""
        reported_price= cols[4].get_text(strip=True) if len(cols) > 4 else ""
        value         = cols[5].get_text(strip=True) if len(cols) > 5 else ""
        activity      = cols[6].get_text(strip=True) if len(cols) > 6 else ""

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
        snippet = soup.get_text()[:200].strip()
        return pd.DataFrame(), f"Table found but 0 rows. Snippet: {snippet}"

    return pd.DataFrame(holdings), None


@st.cache_data(ttl=3600, show_spinner=False)
def get_recent_activity():
    """Activity page: /m/allact.php?typ=a"""
    url = f"{BASE_URL}/allact.php?typ=a"
    html, err = get_page(url)
    if err:
        return pd.DataFrame(), err

    soup = BeautifulSoup(html, "html.parser")
    activity = []

    table = soup.find("table", {"id": "grid"}) or soup.find("table")
    if not table:
        return pd.DataFrame(), "No activity table found"

    # Activity table: td.firm (manager), td.period, then td.sym (tickers with class buy/sell)
    rows = table.find_all("tr")
    for row in rows:
        firm_td = row.find("td", class_="firm")
        if not firm_td:
            continue
        manager = firm_td.get_text(strip=True)
        period_td = row.find("td", class_="period")
        period = period_td.get_text(strip=True) if period_td else ""

        # Each td.sym has an <a class="buy"> or <a class="sell">
        sym_tds = row.find_all("td", class_="sym")
        for sym_td in sym_tds:
            a = sym_td.find("a")
            if not a:
                continue
            ticker = a.get_text(strip=True)
            action_class = a.get("class", [""])[0]  # "buy" or "sell"
            # Tooltip div has: Company\nAction\nChange to portfolio: X%
            tooltip = sym_td.find("div")
            lines = [l.strip() for l in tooltip.get_text("\n").split("\n") if l.strip()] if tooltip else []
            company = lines[0] if len(lines) > 0 else ""
            action  = lines[1] if len(lines) > 1 else action_class
            pct_change = lines[2].replace("Change to portfolio:", "").strip() if len(lines) > 2 else ""

            activity.append({
                "manager": manager,
                "period": period,
                "ticker": ticker,
                "company": company,
                "action": action,
                "pct_change": pct_change,
                "side": "BUY" if action_class == "buy" else "SELL",
            })

    if not activity:
        return pd.DataFrame(), "Activity table found but 0 rows parsed"

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
