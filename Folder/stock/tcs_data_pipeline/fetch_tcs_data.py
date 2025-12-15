import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# =====================================================
# CONFIG
# =====================================================
SYMBOL = "TCS.NS"
YEARS = 10
OUTPUT_FILE = "TCS_DAILY_FULL_DATA_10Y.csv"

# =====================================================
# 1️⃣ DAILY MARKET DATA
# =====================================================
def fetch_market_data_daily():
    df = yf.download(SYMBOL, period=f"{YEARS}y", auto_adjust=True)

    df["Returns"] = df["Close"].pct_change()
    df["DMA_50"] = df["Close"].rolling(50).mean()
    df["DMA_200"] = df["Close"].rolling(200).mean()
    df["Volatility_30D"] = df["Returns"].rolling(30).std()

    df.reset_index(inplace=True)
    df["Year"] = df["Date"].dt.year

    return df


# =====================================================
# 2️⃣ SCRAPE YEARLY FINANCIALS (SCREENER.IN)
# =====================================================
def scrape_screener_financials():
    url = "https://www.screener.in/company/TCS/consolidated/"
    headers = {"User-Agent": "Mozilla/5.0"}

    soup = BeautifulSoup(requests.get(url, headers=headers).text, "lxml")
    tables = soup.find_all("table", class_="data-table")

    data = {}
    years = []

    for table in tables:
        rows = table.find_all("tr")

        # ---- Extract YEARS safely from header ----
        header_cells = rows[0].find_all("th")
        extracted_years = [
            th.text.strip() for th in header_cells[1:]
            if th.text.strip()[-4:].isdigit()
        ]

        if extracted_years:
            years = [int(y[-4:]) for y in extracted_years]

        # ---- Extract row data ----
        for row in rows[1:]:
            cols = [c.text.strip() for c in row.find_all(["th", "td"])]
            if len(cols) > 1:
                data[cols[0]] = cols[1:]

    # Keep last N years
    years = years[-YEARS:]
    target_len = len(years)

    # ---- Helper to ALIGN row lengths ----
    def safe_row(name):
        values = data.get(name, [])
        values = values[-target_len:]           # trim
        if len(values) < target_len:             # pad if short
            values = [np.nan] * (target_len - len(values)) + values
        return values

    df = pd.DataFrame({
        "Year": years,
        "Revenue": safe_row("Sales"),
        "Net_Income": safe_row("Net Profit"),
        "EPS": safe_row("EPS"),
        "Equity": safe_row("Total Equity")
    })

    # ---- Safe numeric conversion ----
    for col in df.columns:
        if col != "Year":
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "")
                .replace("None", np.nan)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# =====================================================
# 3️⃣ MERGE DAILY + YEARLY (KEY FIX)
# =====================================================
def merge_daily_with_financials(daily_df, fin_df):
    merged = pd.merge(daily_df, fin_df, on="Year", how="left")

    merged[["Revenue", "Net_Income", "EPS", "Equity"]] = (
        merged[["Revenue", "Net_Income", "EPS", "Equity"]]
        .ffill()
    )

    return merged


# =====================================================
# 4️⃣ DERIVED FEATURES (ML READY)
# =====================================================
def add_derived_features(df):
    df["PE"] = df["Close"] / df["EPS"]
    df["ROE"] = (df["Net_Income"] / df["Equity"]) * 100

    return df


# =====================================================
# 5️⃣ PIPELINE
# =====================================================
def main():
    print("📥 Fetching daily market data...")
    daily_df = fetch_market_data_daily()

    print("📥 Scraping yearly financials...")
    fin_df = scrape_screener_financials()

    print("🔗 Merging datasets...")
    final_df = merge_daily_with_financials(daily_df, fin_df)

    print("🧮 Creating derived features...")
    final_df = add_derived_features(final_df)

    final_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    final_df.fillna(method="ffill", inplace=True)

    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ DONE: {OUTPUT_FILE} created successfully")


if __name__ == "__main__":
    main()
