import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import csv
import io
import json
import urllib.parse
import urllib.request
import pandas as pd
from streamlit_autorefresh import st_autorefresh


# =========================
# Page Config
# =========================

st.set_page_config(
    page_title="全球市場總覽",
    page_icon="🌍",
    layout="wide"
)


# =========================
# Global CSS
# =========================

st.markdown("""
<style>

html, body, [class*="css"] { font-size: 13px; }
h1 { font-size: 26px !important; }
h2 { font-size: 20px !important; }
h3 { font-size: 16px !important; }
h4 { font-size: 14px !important; }

[data-testid="stMetricValue"] { font-size: 22px; }
[data-testid="stMetricDelta"] { font-size: 13px; }
[data-testid="stMetricLabel"] { font-size: 13px; }

:root {
    --dashboard-width: 1280px;
    --dashboard-left: 48px;
}

[data-testid="stMainBlockContainer"] {
    max-width: var(--dashboard-width) !important;
    width: var(--dashboard-width) !important;
    margin-left: var(--dashboard-left) !important;
    margin-right: auto !important;
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}

[data-testid="stAppViewContainer"] > .main .block-container {
    max-width: var(--dashboard-width) !important;
    width: var(--dashboard-width) !important;
    margin-left: var(--dashboard-left) !important;
    margin-right: auto !important;
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}

section.main > div.block-container {
    max-width: var(--dashboard-width) !important;
    width: var(--dashboard-width) !important;
    margin-left: var(--dashboard-left) !important;
    margin-right: auto !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}

@media (max-width: 1350px) {
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewContainer"] > .main .block-container,
    section.main > div.block-container {
        width: calc(100vw - 32px) !important;
        max-width: calc(100vw - 32px) !important;
        margin-left: 16px !important;
        margin-right: 16px !important;
    }
}

[data-testid="stHeaderActionElements"] { display: none !important; }

.info-icon {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 17px;
    height: 17px;
    min-width: 17px;
    border-radius: 50%;
    color: #8a94a6;
    cursor: help;
    line-height: 1;
    flex-shrink: 0;
    transition: color 0.12s ease, background 0.12s ease;
}

.info-icon:hover { color: #2563eb; background: rgba(37, 99, 235, 0.08); }

.info-icon svg {
    width: 15px; height: 15px; display: block;
    stroke: currentColor; stroke-width: 2; fill: none;
    stroke-linecap: round; stroke-linejoin: round;
    shape-rendering: geometricPrecision;
}

.info-icon::after {
    content: attr(data-tooltip);
    position: absolute;
    left: 50%;
    bottom: calc(100% + 9px);
    transform: translateX(-50%);
    min-width: 260px; max-width: 360px;
    padding: 8px 10px;
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.96);
    color: #ffffff;
    font-size: 12px; font-weight: 500; line-height: 1.5;
    white-space: normal; text-align: left;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.18);
    opacity: 0; visibility: hidden; pointer-events: none; z-index: 9999;
    transition: opacity 0.05s ease;
}

.info-icon::before {
    content: "";
    position: absolute;
    left: 50%; bottom: calc(100% + 4px);
    transform: translateX(-50%);
    border-width: 5px 5px 0 5px;
    border-style: solid;
    border-color: rgba(15, 23, 42, 0.96) transparent transparent transparent;
    opacity: 0; visibility: hidden; pointer-events: none; z-index: 9999;
    transition: opacity 0.05s ease;
}

.info-icon:hover::after, .info-icon:hover::before { opacity: 1; visibility: visible; }

.section-title {
    display: flex; align-items: center; gap: 4px;
    position: relative; overflow: visible;
}

.header-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.update-text { color: #8a94a6; font-size: 12px; }

hr { margin-top: 1rem; margin-bottom: 1rem; }

.market-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 0; border-bottom: 1px solid rgba(180,180,180,0.18);
}
.market-name { font-size: 14px; font-weight: 600; }
.market-value { text-align: right; }
.market-price { font-size: 20px; font-weight: 700; line-height: 1.15; }
.market-delta { font-size: 13px; font-weight: 600; line-height: 1.2; }

[data-testid="stRadio"] label { font-size: 12px !important; }
[data-testid="stRadio"] div[role="radiogroup"] { gap: 6px; }
[data-testid="stRadio"] div[role="radiogroup"] label { padding: 2px 6px; border-radius: 6px; }

/* =========================
   市場總結區塊
========================= */

.alert-card {
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left: 4px solid;
    font-size: 13px;
    line-height: 1.6;
}

.alert-danger {
    background: rgba(220, 38, 38, 0.07);
    border-left-color: #dc2626;
}

.alert-warning {
    background: rgba(245, 158, 11, 0.07);
    border-left-color: #f59e0b;
}

.alert-neutral {
    background: rgba(148, 163, 184, 0.10);
    border-left-color: #64748b;
}

.alert-positive {
    background: rgba(22, 163, 74, 0.07);
    border-left-color: #16a34a;
}

.alert-title {
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 4px;
}

.summary-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

@media (max-width: 900px) {
    .summary-grid { grid-template-columns: 1fr; }
}

</style>
""", unsafe_allow_html=True)


# =========================
# Auto Refresh (1 hour)
# =========================

st_autorefresh(interval=60 * 60 * 1000, key="global_market_refresh")


# =========================
# Constants
# =========================

WATCHLIST = {
    "S&P 500":   "^GSPC",
    "Nasdaq 100": "^NDX",
    "費城半導體": "^SOX",
    "道瓊工業":  "^DJI",
    "日經 225":  "^N225",
    "恆生指數":  "^HSI",
    "DAX":       "^GDAXI",
    "台灣加權":  "^TWII",
}

BOND_LIST = {"10Y": "^TNX"}

COMMODITY_LIST = {
    "黃金":   "GC=F",
    "銅":     "HG=F",
    "天然氣": "NG=F",
}

FX_LIST = {
    "美元指數 DXY":   "DX-Y.NYB",
    "USD/TWD":       "TWD=X",
    "USD/JPY":       "JPY=X",
    "EUR/USD":       "EURUSD=X",
}

OIL_CHART_LIST = {
    "布蘭特原油 Brent": "BZ=F",
    "西德州原油 WTI":   "CL=F",
}

CRYPTO_LIST = {
    "BTC Bitcoin": "BTC-USD",
    "ETH Ethereum": "ETH-USD",
    "SOL Solana":   "SOL-USD",
}

PERIOD_OPTIONS = {
    "1個月": "1mo",
    "3個月": "3mo",
    "6個月": "6mo",
    "1年":   "12mo",
}

VIX_PERIOD_OPTIONS = {
    "1天": "1d",
    "5天": "5d",
    "1月": "1mo",
    "3月": "3mo",
}

GLOBAL_INDEX_PERIOD_OPTIONS = {
    "1天": "1d",
    "1月": "1mo",
    "1年": "1y",
    "3年": "3y",
}

# 各標的對應的說明 tooltip（集中管理，避免散落各函式）
TOOLTIP_MAP = {
    "美元指數 DXY":      "美元指數 DXY 代表美元對六大貨幣的強弱，通常影響台股、黃金、外資與全球資金流向；美元強則新興市場壓力大。",
    "USD/TWD 台幣匯率":  "觀察美元與台幣強弱，反映外資流向、台股資金動能與匯率避險需求。",
    "USD/JPY 日幣匯率":  "日圓常被視為避險貨幣，可觀察全球風險情緒、日本央行政策與利差交易。",
    "布蘭特原油 Brent":  "Brent 為國際油價重要基準，反映全球能源供需、通膨壓力與地緣政治風險。",
    "西德州原油 WTI":    "WTI 為美國原油重要基準，可觀察美國能源供需、庫存變化與通膨壓力。",
    "BTC Bitcoin":       "Bitcoin 為加密貨幣市場代表資產，可觀察市場風險偏好、美元流動性與投機情緒。",
    "ETH Ethereum":      "Ethereum 為主要智能合約平台代幣，可觀察加密貨幣生態系與風險資產情緒。",
    "SOL Solana":        "Solana 為高波動成長型公鏈代幣，可作為加密市場風險偏好的輔助觀察。",
}

# 各 symbol 對應的警戒線設定（集中管理，draw_line_chart 統一讀取）
WARNING_LINES = {
    "DX-Y.NYB": [
        {"y": 100, "color": "red",    "dash": "dash", "text": "DXY 100 警戒線", "pos": "top left"},
    ],
    "JPY=X": [
        {"y": 155, "color": "orange", "dash": "dash", "text": "155 警戒線",  "pos": "top left"},
        {"y": 160, "color": "red",    "dash": "dash", "text": "160 危機線",  "pos": "top left"},
    ],
    "TWD=X": [
        {"y": 32,   "color": "red",   "dash": "dash", "text": "32 壓力線",    "pos": "top left"},
        {"y": 29.2, "color": "green", "dash": "dash", "text": "29.2 強勢台幣", "pos": "bottom left"},
    ],
    "BZ=F": [
        {"y": 90, "color": "red", "dash": "dash", "text": "90 美元警戒線", "pos": "top left"},
    ],
    "CL=F": [
        {"y": 90, "color": "red", "dash": "dash", "text": "90 美元警戒線", "pos": "top left"},
    ],
    "^TNX": [
        {"y": 4.5, "color": "red", "dash": "dash", "text": "4.5% 股市壓力警戒線", "pos": "top left"},
    ],
}

# DXY 固定 Y 軸範圍
SYMBOL_Y_RANGE = {
    "DX-Y.NYB": (94, 106),
}

# 債券 Y 軸固定下限
BOND_Y_CLAMP = (4.2, 4.7)


# =========================
# Helper Utilities
# =========================

def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def format_date(dt):
    if dt is None:
        return "--"
    try:
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(dt)


def tw_color_positive(positive):
    """台股慣例：上漲紅色，下跌綠色"""
    return "red" if positive else "green"


def info_icon_html(tooltip):
    safe = (
        tooltip
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<span class="info-icon" data-tooltip="{safe}">'
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10"></circle>'
        '<line x1="12" y1="16" x2="12" y2="12"></line>'
        '<line x1="12" y1="8" x2="12.01" y2="8"></line>'
        '</svg>'
        '</span>'
    )


def section_title_html(title, tooltip, font_size=20):
    return (
        '<div class="section-title">'
        f'<div style="font-size:{font_size}px;font-weight:700;line-height:1;">{title}</div>'
        f'{info_icon_html(tooltip)}'
        '</div>'
    )


def nearest_history_value(history_rows, target_date):
    if not history_rows:
        return None
    valid = [r for r in history_rows if r.get("date") is not None and r.get("score") is not None and r["date"] <= target_date]
    if not valid:
        return None
    return valid[-1].get("score")


def parse_fear_greed_rating(score):
    if score <= 25: return "Extreme Fear"
    if score <= 45: return "Fear"
    if score <= 55: return "Neutral"
    if score <= 75: return "Greed"
    return "Extreme Greed"


def rating_to_zh(rating):
    if rating is None:
        return "--"
    mapping = {
        "extreme fear": "極度恐懼",
        "fear": "恐懼",
        "neutral": "中性",
        "greed": "貪婪",
        "extreme greed": "極度貪婪",
    }
    return mapping.get(str(rating).strip().lower(), str(rating))


def build_fear_greed_result(score, rating, history_rows, source):
    today = datetime.now().date()
    return {
        "score": float(score),
        "rating": rating_to_zh(rating or parse_fear_greed_rating(float(score))),
        "previous_close":   nearest_history_value(history_rows, today - timedelta(days=1)),
        "previous_1_week":  nearest_history_value(history_rows, today - timedelta(days=7)),
        "previous_1_month": nearest_history_value(history_rows, today - timedelta(days=30)),
        "previous_1_year":  nearest_history_value(history_rows, today - timedelta(days=365)),
        "source": source,
    }


# =========================
# Shared Yahoo Chart Parser
# =========================

def _parse_yahoo_chart_ohlc(result):
    """
    共用解析邏輯：將 Yahoo Finance Chart API result 轉為 DataFrame 與 meta。
    回傳 (hist_df, meta) 或 (None, None)。
    """
    meta = result.get("meta", {})
    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]

    close_values = quote.get("close", [])
    open_values  = quote.get("open",  [])
    high_values  = quote.get("high",  [])
    low_values   = quote.get("low",   [])

    rows = []
    for idx, ts in enumerate(timestamps):
        cv = close_values[idx] if idx < len(close_values) else None
        if cv is None:
            continue
        rows.append({
            "Datetime": datetime.fromtimestamp(ts),
            "Open":  open_values[idx]  if idx < len(open_values)  and open_values[idx]  is not None else cv,
            "High":  high_values[idx]  if idx < len(high_values)  and high_values[idx]  is not None else cv,
            "Low":   low_values[idx]   if idx < len(low_values)   and low_values[idx]   is not None else cv,
            "Close": cv,
        })

    if not rows:
        return None, None

    return pd.DataFrame(rows), meta


def _fetch_yahoo_chart_raw(symbol, yahoo_range, yahoo_interval, timeout=12):
    """向 Yahoo Finance Chart API 發出請求，回傳解析後的 JSON 或 raise Exception。"""
    encoded = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?range={yahoo_range}&interval={yahoo_interval}&includePrePost=false"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    return json.loads(raw)


# =========================
# Data Functions
# =========================

def get_yahoo_chart_data(symbol, chart_period="1d"):
    """
    使用 Yahoo Finance Chart API 取得 OHLC 資料。
    主要用於 ^TWII 與其他需要對齊即時報價的標的。
    """
    if chart_period == "1d":
        yahoo_range, yahoo_interval = "1d", "5m"
    else:
        yahoo_range, yahoo_interval = chart_period, "1d"

    try:
        data   = _fetch_yahoo_chart_raw(symbol, yahoo_range, yahoo_interval)
        result = data["chart"]["result"][0]
        hist, meta = _parse_yahoo_chart_ohlc(result)

        if hist is None:
            return None

        price    = safe_float(meta.get("regularMarketPrice"))
        previous = safe_float(meta.get("chartPreviousClose"))

        if price is None:
            price = float(hist["Close"].iloc[-1])
        if previous is None:
            previous = safe_float(meta.get("previousClose")) or price

        change     = price - previous
        change_pct = change / previous * 100 if previous else 0

        return {
            "price":      float(price),
            "previous":   float(previous),
            "change":     float(change),
            "change_pct": float(change_pct),
            "hist":       hist,
            "last_time":  hist.iloc[-1]["Datetime"],
        }

    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_market_data(symbol, chart_period="1d"):
    """
    取得股市指數資料。
    ^TWII 優先使用 Yahoo Chart API（避免 yfinance 延遲問題）。
    其他標的使用 yfinance，漲跌以最近兩交易日收盤計算。
    """
    if symbol == "^TWII":
        result = get_yahoo_chart_data(symbol, chart_period)
        if result is not None:
            return result

    ticker = yf.Ticker(symbol)
    daily  = ticker.history(period="10d", interval="1d")

    if daily.empty or len(daily) < 2:
        return None

    daily_close = daily["Close"].dropna()
    if len(daily_close) < 2:
        return None

    last_close = daily_close.iloc[-1]
    prev_close = daily_close.iloc[-2]
    change     = last_close - prev_close
    change_pct = change / prev_close * 100

    if chart_period == "1d":
        hist = ticker.history(period="1d", interval="5m")
    else:
        hist = ticker.history(period=chart_period, interval="1d")

    if hist.empty:
        hist = daily

    hist = hist.reset_index()

    if "Datetime" in hist.columns:
        last_time = hist.iloc[-1]["Datetime"]
    elif "Date" in hist.columns:
        last_time = hist.iloc[-1]["Date"]
    else:
        last_time = None

    return {
        "price":      float(last_close),
        "previous":   float(prev_close),
        "change":     float(change),
        "change_pct": float(change_pct),
        "hist":       hist,
        "last_time":  last_time,
    }


@st.cache_data(ttl=3600)
def get_bond_history(symbol="^TNX", period="6mo"):
    ticker = yf.Ticker(symbol)
    hist   = ticker.history(period=period, interval="1d")

    if hist.empty or len(hist) < 2:
        return None

    close = hist["Close"].dropna()
    if len(close) < 2:
        return None

    last = close.iloc[-1]
    prev = close.iloc[-2]

    return {
        "price":      float(last),
        "previous":   float(prev),
        "change":     float(last - prev),
        "change_pct": float((last - prev) / prev * 100),
        "hist":       hist,
        "last_time":  hist.index[-1],
    }


@st.cache_data(ttl=3600)
def get_yield_curve_data(period="6mo"):
    """
    取得美國 13週（^IRX）與 10Y（^TNX）公債殖利率歷史，計算利差（10Y - 13W）。
    利差為負代表殖利率曲線倒掛，歷史上為衰退領先指標。
    yfinance 無直接 2Y 標的，以 13週短端（^IRX）代替，仍具高度參考性。
    """
    t_short = yf.Ticker("^IRX")
    t_long  = yf.Ticker("^TNX")

    h_short = t_short.history(period=period, interval="1d")
    h_long  = t_long.history(period=period,  interval="1d")

    if h_short.empty or h_long.empty:
        return None

    s_short = h_short["Close"].dropna().rename("Short")
    s_long  = h_long["Close"].dropna().rename("Long")

    merged = s_short.to_frame().join(s_long.to_frame(), how="inner")
    if merged.empty or len(merged) < 2:
        return None

    merged["Spread"] = merged["Long"] - merged["Short"]

    return {
        "hist":         merged,
        "last_short":   float(merged["Short"].iloc[-1]),
        "last_long":    float(merged["Long"].iloc[-1]),
        "last_spread":  float(merged["Spread"].iloc[-1]),
        "prev_spread":  float(merged["Spread"].iloc[-2]),
        "inverted":     float(merged["Spread"].iloc[-1]) < 0,
        "last_time":    merged.index[-1],
    }


@st.cache_data(ttl=3600)
def get_currency_history(symbol, period="12mo"):
    ticker = yf.Ticker(symbol)
    hist   = ticker.history(period=period, interval="1d")

    if hist.empty or len(hist) < 2:
        return None

    return hist


@st.cache_data(ttl=3600)
def get_oil_spread_data():
    brent = yf.Ticker("BZ=F").history(period="12mo", interval="1d")
    wti   = yf.Ticker("CL=F").history(period="12mo", interval="1d")

    if brent.empty or wti.empty:
        return None

    merged = (
        brent["Close"].dropna().rename("Brent").to_frame()
        .join(wti["Close"].dropna().rename("WTI").to_frame(), how="inner")
    )

    if merged.empty or len(merged) < 2:
        return None

    merged["Spread"] = merged["Brent"] - merged["WTI"]
    return merged


@st.cache_data(ttl=3600)
def get_vix_data(period="1d"):
    """
    VIX 資料：優先使用 Yahoo Chart API（對齊即時報價），
    失敗時 fallback 至 yfinance。
    """
    if period == "1d":
        yahoo_range, yahoo_interval = "1d", "5m"
    elif period == "5d":
        yahoo_range, yahoo_interval = "5d", "15m"
    else:
        yahoo_range, yahoo_interval = period, "1d"

    try:
        data   = _fetch_yahoo_chart_raw("^VIX", yahoo_range, yahoo_interval)
        result = data["chart"]["result"][0]
        hist_df, meta = _parse_yahoo_chart_ohlc(result)

        if hist_df is None or len(hist_df) < 2:
            raise ValueError("Not enough rows")

        hist = hist_df.set_index("Datetime")

        price    = safe_float(meta.get("regularMarketPrice")) or float(hist["Close"].iloc[-1])
        previous = safe_float(meta.get("chartPreviousClose")) or float(hist["Close"].iloc[-2])
        change   = price - previous

        return {
            "price":      float(price),
            "previous":   float(previous),
            "change":     float(change),
            "change_pct": float(change / previous * 100),
            "hist":       hist,
            "last_time":  hist.index[-1],
            "open":  float(hist["Open"].iloc[0]  if period == "1d" else hist["Open"].iloc[-1]),
            "high":  float(hist["High"].max()    if period == "1d" else hist["High"].iloc[-1]),
            "low":   float(hist["Low"].min()     if period == "1d" else hist["Low"].iloc[-1]),
            "source": "Yahoo Finance",
        }

    except Exception:
        pass

    # yfinance fallback
    ticker = yf.Ticker("^VIX")

    if period in ("1d", "5d"):
        fallback_interval = "5m" if period == "1d" else "15m"
        hist  = ticker.history(period=period, interval=fallback_interval)
        daily = ticker.history(period="5d",   interval="1d")

        if hist.empty or len(hist) < 2 or daily.empty or len(daily) < 2:
            return None

        price    = hist["Close"].dropna().iloc[-1]
        previous = daily["Close"].dropna().iloc[-2]
        change   = price - previous

        return {
            "price":      float(price),
            "previous":   float(previous),
            "change":     float(change),
            "change_pct": float(change / previous * 100),
            "hist":       hist,
            "last_time":  hist.index[-1],
            "open":  float(hist["Open"].dropna().iloc[0]),
            "high":  float(hist["High"].dropna().max()),
            "low":   float(hist["Low"].dropna().min()),
            "source": "yfinance fallback",
        }

    hist  = ticker.history(period=period, interval="1d")
    close = hist["Close"].dropna() if not hist.empty else pd.Series()

    if len(close) < 2:
        return None

    last     = close.iloc[-1]
    previous = close.iloc[-2]
    change   = last - previous

    return {
        "price":      float(last),
        "previous":   float(previous),
        "change":     float(change),
        "change_pct": float(change / previous * 100),
        "hist":       hist,
        "last_time":  hist.index[-1],
        "open":  float(hist["Open"].iloc[-1]),
        "high":  float(hist["High"].iloc[-1]),
        "low":   float(hist["Low"].iloc[-1]),
        "source": "yfinance fallback",
    }


@st.cache_data(ttl=3600)
def get_fear_greed_data():
    """
    恐懼貪婪指數：優先 CNN 官方 API，備援 GitHub CSV。
    """
    start_date = (datetime.now() - timedelta(days=370)).strftime("%Y-%m-%d")

    cnn_urls = [
        f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}",
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
    ]

    for url in cnn_urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept":  "application/json,text/plain,*/*",
                    "Referer": "https://edition.cnn.com/markets/fear-and-greed",
                    "Origin":  "https://edition.cnn.com",
                }
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))

            fear_greed = data.get("fear_and_greed", {})
            historical = data.get("fear_and_greed_historical", {})

            history_rows = sorted(
                [
                    {
                        "date":  datetime.fromtimestamp(int(item["x"]) / 1000).date(),
                        "score": safe_float(item.get("y")),
                    }
                    for item in historical.get("data", [])
                    if item.get("x") and safe_float(item.get("y")) is not None
                ],
                key=lambda r: r["date"]
            )

            score  = safe_float(fear_greed.get("score") or fear_greed.get("value"))
            rating = fear_greed.get("rating") or fear_greed.get("status") or fear_greed.get("classification")

            if score is None and history_rows:
                score  = history_rows[-1]["score"]
                rating = parse_fear_greed_rating(score)

            if score is not None:
                return build_fear_greed_result(score, rating, history_rows, "CNN API")

        except Exception:
            continue

    # GitHub CSV 備援
    fallback_url = "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/main/fear-greed.csv"
    try:
        req = urllib.request.Request(fallback_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw_csv = resp.read().decode("utf-8", errors="ignore")

        reader       = csv.DictReader(io.StringIO(raw_csv))
        history_rows = []
        latest_rating = None

        for row in reader:
            date_text  = row.get("Date") or row.get("date") or row.get("DATE")
            score_text = (
                row.get("Fear Greed") or row.get("Fear Greed Index")
                or row.get("fear_greed") or row.get("score") or row.get("Score")
            )
            rating_text  = row.get("Rating") or row.get("rating") or row.get("Classification")
            score_value  = safe_float(score_text)

            if not date_text or score_value is None:
                continue

            try:
                row_date = datetime.strptime(date_text[:10], "%Y-%m-%d").date()
            except Exception:
                continue

            history_rows.append({"date": row_date, "score": score_value})
            latest_rating = rating_text

        history_rows = sorted(history_rows, key=lambda r: r["date"])

        if history_rows:
            return build_fear_greed_result(
                history_rows[-1]["score"], latest_rating, history_rows, "GitHub fallback"
            )

    except Exception:
        pass

    return None


# =========================
# Chart Drawing Functions
# =========================

def _apply_warning_lines(fig, symbol):
    """將 WARNING_LINES 中對應的警戒線加入圖表。"""
    for line in WARNING_LINES.get(symbol, []):
        fig.add_hline(
            y=line["y"],
            line_color=line["color"],
            line_width=2,
            line_dash=line["dash"],
            annotation_text=line["text"],
            annotation_position=line["pos"],
            annotation_font_color=line["color"],
            annotation_bgcolor="rgba(255,255,255,0.75)"
        )


def draw_sparkline(df, positive=True):
    color = tw_color_positive(positive)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        mode="lines", line=dict(color=color, width=2), showlegend=False
    ))
    fig.update_layout(
        height=70, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def draw_line_chart(df, title, symbol, positive=True, height=250,
                    y_suffix="", bond_mode=False):
    """
    通用折線圖（帶警戒線、自動 Y 軸範圍）。
    bond_mode=True 時使用 royalblue 填色（公債殖利率用）。
    symbol 用於查詢 WARNING_LINES 與 SYMBOL_Y_RANGE。
    """
    color = "royalblue" if bond_mode else tw_color_positive(positive)

    close_min = df["Close"].min()
    close_max = df["Close"].max()
    padding   = (close_max - close_min) * 0.25 or close_max * 0.01

    y_min = close_min - padding
    y_max = close_max + padding

    # 固定 Y 軸範圍（DXY 等）
    if symbol in SYMBOL_Y_RANGE:
        forced_min, forced_max = SYMBOL_Y_RANGE[symbol]
        y_min = min(y_min, forced_min)
        y_max = max(y_max, forced_max)

    # 公債殖利率鉗制
    if bond_mode:
        y_min = min(y_min, BOND_Y_CLAMP[0])
        y_max = max(y_max, BOND_Y_CLAMP[1])

    fill_color = (
        "rgba(65, 105, 225, 0.16)" if bond_mode
        else ("rgba(220,0,0,0.10)" if positive else "rgba(0,150,120,0.12)")
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=fill_color,
        showlegend=False,
    ))

    _apply_warning_lines(fig, symbol)

    top_margin = 40 if title else 10
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)) if title else {},
        height=height,
        margin=dict(l=10, r=10, t=top_margin, b=10),
        yaxis=dict(
            ticksuffix=y_suffix,
            range=[y_min, y_max],
            tickfont=dict(size=10),
            gridcolor="rgba(180,180,180,0.25)",
        ),
        xaxis=dict(
            title="", tickfont=dict(size=10),
            gridcolor="rgba(180,180,180,0.25)"
        ),
        font=dict(size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def draw_yield_curve_chart(data):
    """
    繪製美國殖利率曲線圖：10Y（藍）與短端（橙）雙線，
    下方 spread 柱狀圖顯示利差（正常 = 金色；倒掛 = 紅色）。
    """
    if data is None:
        return None

    hist   = data["hist"]
    spread = hist["Spread"]

    spread_colors = [
        "rgba(218, 165, 32, 0.80)" if v >= 0 else "rgba(220, 38, 38, 0.75)"
        for v in spread
    ]

    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.62, 0.38],
        vertical_spacing=0.06,
    )

    # 上圖：10Y vs 短端
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Long"],
        mode="lines", line=dict(color="royalblue", width=2),
        name="10Y",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Short"],
        mode="lines", line=dict(color="darkorange", width=2),
        name="13W（短端）",
    ), row=1, col=1)

    # 下圖：利差柱狀
    fig.add_trace(go.Bar(
        x=spread.index, y=spread.values,
        marker_color=spread_colors,
        name="利差 (10Y - 13W)",
        showlegend=False,
    ), row=2, col=1)

    fig.add_hline(
        y=0, line_color="gray", line_width=1, line_dash="dash", row=2, col=1
    )

    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", x=0, y=1.02, font=dict(size=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    )
    fig.update_yaxes(
        ticksuffix="%", tickfont=dict(size=10),
        gridcolor="rgba(180,180,180,0.25)", row=1, col=1
    )
    fig.update_yaxes(
        title_text="利差%", tickfont=dict(size=9),
        gridcolor="rgba(180,180,180,0.25)", row=2, col=1
    )
    fig.update_xaxes(tickfont=dict(size=10), gridcolor="rgba(180,180,180,0.25)")

    return fig


def show_yield_curve_card(period="6mo"):
    data = get_yield_curve_data(period)

    with st.container(border=True):
        st.markdown(
            section_title_html(
                "📐 殖利率曲線（10Y - 13W）",
                "10年期與13週短端公債殖利率利差。利差為負（倒掛）代表短端利率高於長端，"
                "歷史上殖利率曲線倒掛往往是衰退的領先訊號（通常領先 6~18 個月）。",
                font_size=16
            ),
            unsafe_allow_html=True
        )

        if data is None:
            st.warning("殖利率曲線資料讀取失敗")
            return

        spread       = data["last_spread"]
        prev_spread  = data["prev_spread"]
        spread_chg   = spread - prev_spread
        inverted     = data["inverted"]

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("10Y 殖利率",  f"{data['last_long']:.3f}%")
        with col_b:
            st.metric("13W 殖利率",  f"{data['last_short']:.3f}%")
        with col_c:
            st.metric(
                "利差（10Y - 13W）",
                f"{spread:+.3f}%",
                delta=f"{spread_chg:+.3f}%",
                delta_color="normal"
            )

        if inverted:
            st.error("⚠️ 殖利率曲線倒掛中 — 短端利率高於長端，歷史衰退警訊")
        else:
            st.success("✅ 殖利率曲線正常 — 長端利率高於短端")

        st.caption(f"資料日 {format_date(data['last_time'])}")

        fig = draw_yield_curve_chart(data)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def draw_oil_spread_chart(spread_data):
    if spread_data is None or spread_data.empty:
        return None

    spread = spread_data["Spread"]
    colors = [
        "rgba(218, 165, 32, 0.85)" if v >= 0 else "rgba(220, 0, 0, 0.75)"
        for v in spread
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=spread.index, y=spread.values, marker_color=colors, showlegend=False))
    fig.add_hline(y=0, line_color="gray", line_width=1, line_dash="dash")
    fig.update_layout(
        title=dict(text="Brent - WTI 價差", font=dict(size=14)),
        height=250, margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(title="USD / bbl", tickfont=dict(size=10), gridcolor="rgba(180,180,180,0.25)"),
        xaxis=dict(title="", tickfont=dict(size=10), gridcolor="rgba(180,180,180,0.25)"),
        font=dict(size=11),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def draw_fear_greed_gauge(score):
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"valueformat": ".0f", "font": {"size": 42, "color": "#0f172a"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickfont": {"size": 10, "color": "#94a3b8"}},
            "bar":  {"color": "rgba(0,0,0,0)"},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [
                {"range": [0,  25],  "color": "rgba(220, 38,  38,  0.25)"},
                {"range": [25, 45],  "color": "rgba(245, 158, 11,  0.25)"},
                {"range": [45, 55],  "color": "rgba(148, 163, 184, 0.25)"},
                {"range": [55, 75],  "color": "rgba(34,  197, 94,  0.25)"},
                {"range": [75, 100], "color": "rgba(22,  163, 74,  0.35)"},
            ],
            "threshold": {"line": {"color": "#0f172a", "width": 3}, "thickness": 0.75, "value": score},
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        height=230, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def draw_vix_chart(hist, show_warning_lines=True):
    if hist is None or hist.empty:
        return None

    close    = hist["Close"]
    positive = close.iloc[-1] >= close.iloc[0]
    color    = tw_color_positive(positive)

    close_min = close.min()
    close_max = close.max()
    padding   = (close_max - close_min) * 0.25 or close_max * 0.01

    y_min = max(0, close_min - padding)
    y_max = close_max + padding

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=close,
        mode="lines", line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor="rgba(220,0,0,0.10)" if positive else "rgba(0,150,120,0.12)",
        showlegend=False,
    ))

    if show_warning_lines:
        for y_val, color_val, text_val in [(20, "orange", "VIX 20"), (30, "red", "VIX 30")]:
            fig.add_hline(
                y=y_val, line_color=color_val, line_width=1, line_dash="dash",
                annotation_text=text_val, annotation_position="right",
                annotation_font_color=color_val,
                annotation_bgcolor="rgba(255,255,255,0.75)"
            )
        y_max = max(y_max, 32)

    fig.update_layout(
        title=dict(text="VIX 指數走勢", font=dict(size=14)),
        height=250, margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(range=[y_min, y_max], tickfont=dict(size=10), gridcolor="rgba(180,180,180,0.25)"),
        xaxis=dict(title="", tickfont=dict(size=10), gridcolor="rgba(180,180,180,0.25)"),
        font=dict(size=11),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def draw_crypto_chart(hist, positive=True):
    if hist is None or hist.empty:
        return None

    color     = tw_color_positive(positive)
    close_min = hist["Close"].min()
    close_max = hist["Close"].max()
    padding   = (close_max - close_min) * 0.25 or close_max * 0.01

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        mode="lines", line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor="rgba(220,0,0,0.10)" if positive else "rgba(0,150,120,0.12)",
        showlegend=False,
    ))
    fig.update_layout(
        height=250, margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(range=[close_min - padding, close_max + padding],
                   tickfont=dict(size=10), gridcolor="rgba(180,180,180,0.25)"),
        xaxis=dict(title="", tickfont=dict(size=10), gridcolor="rgba(180,180,180,0.25)"),
        font=dict(size=11),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# =========================
# UI Components
# =========================

def show_market_card(name, symbol, data):
    with st.container(border=True):
        c_title, c_date = st.columns([3, 2])

        with c_title:
            st.markdown(f"### {name}")
            st.caption(symbol)

        with c_date:
            if data is not None:
                st.markdown(
                    f"<div style='text-align:right;color:gray;font-size:12px'>"
                    f"{format_date(data['last_time'])}</div>",
                    unsafe_allow_html=True
                )

        if data is None:
            st.error("資料讀取失敗")
            return

        positive = data["change_pct"] >= 0

        st.metric(
            label="",
            value=f"{data['price']:,.2f}",
            delta=f"{data['change_pct']:+.2f}% / {data['change']:+,.1f}",
            delta_color="inverse"
        )

        st.plotly_chart(
            draw_sparkline(data["hist"], positive),
            use_container_width=True,
            config={"displayModeBar": False}
        )


def show_simple_row(name, symbol):
    data = get_market_data(symbol)

    if data is None:
        st.warning(f"{name} 資料讀取失敗")
        return

    positive = data["change_pct"] >= 0
    color    = "red" if positive else "green"
    arrow    = "▲" if positive else "▼"

    st.markdown(
        f"<div class='market-row'>"
        f"<div class='market-name'>{name}</div>"
        f"<div class='market-value'>"
        f"<div class='market-price'>{data['price']:,.3f}</div>"
        f"<div class='market-delta' style='color:{color};'>{arrow} {data['change_pct']:+.2f}%</div>"
        f"</div></div>",
        unsafe_allow_html=True
    )


def show_commodity_chart_card(name, symbol):
    """
    商品走勢卡片（黃金、銅、天然氣等），與匯率卡片格式一致。
    """
    hist = get_currency_history(symbol, period="12mo")

    with st.container(border=True):
        st.markdown(
            section_title_html(
                f"📦 {name}",
                TOOLTIP_MAP.get(name, f"{name} 近一年走勢"),
                font_size=16
            ),
            unsafe_allow_html=True
        )

        if hist is None:
            st.warning(f"{name} 資料讀取失敗")
            return

        last  = hist["Close"].iloc[-1]
        prev  = hist["Close"].iloc[-2]
        change     = last - prev
        change_pct = change / prev * 100
        positive   = change >= 0

        st.metric(
            label="",
            value=f"{last:,.3f}",
            delta=f"{change:+.3f} ({change_pct:+.2f}%)",
            delta_color="inverse"
        )

        st.caption(
            f"開盤 {hist['Open'].iloc[-1]:,.3f}　"
            f"最高 {hist['High'].iloc[-1]:,.3f}　"
            f"最低 {hist['Low'].iloc[-1]:,.3f}　"
            f"資料日 {format_date(hist.index[-1])}"
        )

        st.plotly_chart(
            draw_line_chart(hist, f"{name} 走勢", symbol, positive),
            use_container_width=True,
            config={"displayModeBar": False}
        )


def show_currency_chart_card(name, symbol, period="12mo"):
    hist = get_currency_history(symbol, period)

    with st.container(border=True):
        title_icon = "🛢" if "原油" in name else "💱"
        st.markdown(
            section_title_html(
                f"{title_icon} {name}",
                TOOLTIP_MAP.get(name, ""),
                font_size=16
            ),
            unsafe_allow_html=True
        )

        if hist is None:
            st.warning(f"{name} 資料讀取失敗")
            return

        last  = hist["Close"].iloc[-1]
        prev  = hist["Close"].iloc[-2]
        change     = last - prev
        change_pct = change / prev * 100
        positive   = change >= 0

        st.metric(
            label="",
            value=f"{last:,.3f}",
            delta=f"{change:+.3f} ({change_pct:+.2f}%)",
            delta_color="inverse"
        )

        st.caption(
            f"開盤 {hist['Open'].iloc[-1]:,.3f}　"
            f"最高 {hist['High'].iloc[-1]:,.3f}　"
            f"最低 {hist['Low'].iloc[-1]:,.3f}　"
            f"資料日 {format_date(hist.index[-1])}"
        )

        st.plotly_chart(
            draw_line_chart(hist, f"{name} 走勢", symbol, positive),
            use_container_width=True,
            config={"displayModeBar": False}
        )


def show_oil_spread_card():
    spread_data = get_oil_spread_data()

    with st.container(border=True):
        st.markdown(
            section_title_html(
                "🛢 Brent - WTI 價差",
                "布蘭特原油與西德州原油的價差，可觀察全球供需、地緣政治、運輸瓶頸與美國原油相對強弱。",
                font_size=16
            ),
            unsafe_allow_html=True
        )

        if spread_data is None:
            st.warning("原油價差資料讀取失敗")
            return

        last   = spread_data["Spread"].iloc[-1]
        prev   = spread_data["Spread"].iloc[-2]
        change = last - prev

        st.metric(label="", value=f"{last:,.2f}", delta=f"{change:+.2f}", delta_color="normal")
        st.caption(
            f"Brent {spread_data['Brent'].iloc[-1]:,.2f}　"
            f"WTI {spread_data['WTI'].iloc[-1]:,.2f}　"
            f"資料日 {format_date(spread_data.index[-1])}"
        )

        fig = draw_oil_spread_chart(spread_data)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def show_fear_greed_card():
    data = get_fear_greed_data()

    with st.container(border=True):
        st.markdown(
            section_title_html(
                "CNN 恐懼與貪婪指數",
                "CNN Fear & Greed Index 以多項市場情緒指標衡量投資人偏恐懼或偏貪婪，通常可作為風險情緒參考。",
                font_size=16
            ),
            unsafe_allow_html=True
        )

        if data is None:
            st.warning("CNN 恐懼與貪婪指數資料讀取失敗")
            st.caption("若 CNN API 暫時阻擋連線，請稍後再刷新。")
            return

        score  = round(data["score"])
        rating = data["rating"]

        st.plotly_chart(draw_fear_greed_gauge(score), use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"<div style='text-align:center;font-size:18px;font-weight:700;color:#16a34a;margin-top:-28px'>"
            f"{rating}</div>",
            unsafe_allow_html=True
        )

        m1, m2, m3 = st.columns(3)
        with m1:
            st.caption("上週")
            st.markdown(f"**{round(data['previous_1_week']) if data.get('previous_1_week') is not None else '--'}**")
        with m2:
            st.caption("上月")
            st.markdown(f"**{round(data['previous_1_month']) if data.get('previous_1_month') is not None else '--'}**")
        with m3:
            st.caption("去年")
            st.markdown(f"**{round(data['previous_1_year']) if data.get('previous_1_year') is not None else '--'}**")

        st.caption(f"資料來源：{data.get('source', '--')}")


def show_vix_card(period="1d", selected_label="1天"):
    with st.container(border=True):
        vix_title_col, vix_period_col = st.columns([1, 1])

        with vix_title_col:
            st.markdown(
                section_title_html(
                    "VIX 恐慌指數",
                    "VIX 衡量市場對未來波動的預期，數值越高代表避險與恐慌情緒越強。20 以上需留意，30 以上通常代表高壓力市場。",
                    font_size=16
                ),
                unsafe_allow_html=True
            )

        with vix_period_col:
            selected_label = st.radio(
                "VIX 期間",
                list(VIX_PERIOD_OPTIONS.keys()),
                index=list(VIX_PERIOD_OPTIONS.keys()).index(selected_label),
                horizontal=True,
                label_visibility="collapsed",
                key="vix_period_selector"
            )
            period = VIX_PERIOD_OPTIONS[selected_label]

        data = get_vix_data(period)

        if data is None:
            st.warning("VIX 資料讀取失敗")
            return

        st.metric(
            label="",
            value=f"{data['price']:,.2f}",
            delta=f"{data['change']:+.2f} ({data['change_pct']:+.2f}%)",
            delta_color="inverse"
        )
        st.caption(
            f"開盤 {data['open']:,.2f}　最高 {data['high']:,.2f}　最低 {data['low']:,.2f}　資料日 {format_date(data['last_time'])}"
        )

        fig = draw_vix_chart(data["hist"], show_warning_lines=period in ("1mo", "3mo"))
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.caption(f"資料來源：{data.get('source', '--')}")


# =========================
# Market Summary & Alerts
# =========================

def _alert_card(level, title, body):
    """
    level: "danger" | "warning" | "neutral" | "positive"
    """
    icons = {"danger": "🔴", "warning": "🟡", "neutral": "⚪", "positive": "🟢"}
    icon  = icons.get(level, "⚪")
    return (
        f"<div class='alert-card alert-{level}'>"
        f"<div class='alert-title'>{icon} {title}</div>"
        f"{body}"
        f"</div>"
    )


def show_market_summary(market_results, vix_data, fg_data, bond_data,
                        dxy_hist, twd_hist, jpy_hist, oil_data):
    """
    彙整所有指標，產生市場總結與提醒區塊。
    """

    st.markdown(
        section_title_html(
            "📋 市場總結與提醒",
            "根據當前各項指標數值，自動歸納重要訊號與注意事項，供參考用。投資決策請自行判斷。",
            font_size=20
        ),
        unsafe_allow_html=True
    )

    alerts = []

    # ── 1. VIX 恐慌指數 ──────────────────────────────────────
    if vix_data is not None:
        vix_price = vix_data["price"]
        vix_chg   = vix_data["change_pct"]

        if vix_price >= 30:
            alerts.append(_alert_card(
                "danger", f"VIX 高恐慌 {vix_price:.2f}",
                f"VIX 超過 30，市場處於高壓力恐慌狀態。歷史上此區間往往伴隨劇烈波動，建議降低槓桿、注意避險。"
                f"（今日變動 {vix_chg:+.2f}%）"
            ))
        elif vix_price >= 20:
            alerts.append(_alert_card(
                "warning", f"VIX 偏高 {vix_price:.2f}",
                f"VIX 介於 20～30，市場情緒偏謹慎。短線不確定性升溫，建議留意倉位風險。"
                f"（今日變動 {vix_chg:+.2f}%）"
            ))
        else:
            alerts.append(_alert_card(
                "positive", f"VIX 正常 {vix_price:.2f}",
                f"VIX 低於 20，市場情緒相對穩定，波動預期處於正常區間。"
                f"（今日變動 {vix_chg:+.2f}%）"
            ))

    # ── 2. CNN 恐懼貪婪指數 ──────────────────────────────────
    if fg_data is not None:
        fg_score  = fg_data["score"]
        fg_rating = fg_data["rating"]

        if fg_score <= 25:
            alerts.append(_alert_card(
                "danger", f"市場極度恐懼（F&G = {round(fg_score)}）",
                f"CNN 恐懼貪婪指數處於「{fg_rating}」區間，可能代表市場過度悲觀，"
                f"歷史上有時是逆向進場的參考訊號，但須配合其他指標確認。"
            ))
        elif fg_score <= 45:
            alerts.append(_alert_card(
                "warning", f"市場偏恐懼（F&G = {round(fg_score)}）",
                f"CNN 恐懼貪婪指數為「{fg_rating}」，投資人情緒偏保守，風險偏好下降。"
            ))
        elif fg_score >= 75:
            alerts.append(_alert_card(
                "warning", f"市場極度貪婪（F&G = {round(fg_score)}）",
                f"CNN 恐懼貪婪指數處於「{fg_rating}」，市場可能過熱，"
                f"歷史上此區間需留意短線修正風險。"
            ))
        elif fg_score >= 55:
            alerts.append(_alert_card(
                "neutral", f"市場偏貪婪（F&G = {round(fg_score)}）",
                f"CNN 恐懼貪婪指數為「{fg_rating}」，整體情緒樂觀但尚未過熱。"
            ))
        else:
            alerts.append(_alert_card(
                "neutral", f"市場情緒中性（F&G = {round(fg_score)}）",
                f"CNN 恐懼貪婪指數為「{fg_rating}」，市場無明顯偏向。"
            ))

    # ── 3. 美國十年期公債殖利率 ──────────────────────────────
    if bond_data is not None:
        bond_price = bond_data["price"]
        bond_chg   = bond_data["change"]

        if bond_price >= 5.0:
            alerts.append(_alert_card(
                "danger", f"美債殖利率嚴重警戒 {bond_price:.3f}%",
                f"十年期美債殖利率突破 5%，對科技股與高估值股票估值壓力極大，企業融資成本顯著上升。"
                f"（今日變動 {bond_chg:+.3f}%）"
            ))
        elif bond_price >= 4.5:
            alerts.append(_alert_card(
                "warning", f"美債殖利率壓力區 {bond_price:.3f}%",
                f"十年期美債殖利率達到 4.5% 股市壓力警戒線，需留意對成長股與台股科技類股的估值衝擊。"
                f"（今日變動 {bond_chg:+.3f}%）"
            ))
        elif bond_price >= 4.3:
            alerts.append(_alert_card(
                "neutral", f"美債殖利率偏高 {bond_price:.3f}%",
                f"十年期美債殖利率處於 4.3%～4.5% 偏高區間，市場估值承壓但尚未觸及警戒線。"
                f"（今日變動 {bond_chg:+.3f}%）"
            ))
        else:
            alerts.append(_alert_card(
                "positive", f"美債殖利率正常 {bond_price:.3f}%",
                f"十年期美債殖利率低於 4.3%，對股市估值壓力相對可控。"
                f"（今日變動 {bond_chg:+.3f}%）"
            ))

    # ── 4. 美元指數 DXY ──────────────────────────────────────
    if dxy_hist is not None and len(dxy_hist) >= 2:
        dxy_last = dxy_hist["Close"].iloc[-1]
        dxy_prev = dxy_hist["Close"].iloc[-2]
        dxy_chg  = (dxy_last - dxy_prev) / dxy_prev * 100

        if dxy_last >= 105:
            alerts.append(_alert_card(
                "danger", f"美元指數強勢 DXY {dxy_last:.2f}",
                f"DXY 超過 105，美元強勢對新興市場資金外流壓力大，黃金與大宗商品通常承壓。台幣、日圓可能持續貶值。"
                f"（今日變動 {dxy_chg:+.2f}%）"
            ))
        elif dxy_last >= 100:
            alerts.append(_alert_card(
                "warning", f"美元指數突破 100 關卡 DXY {dxy_last:.2f}",
                f"DXY 超過 100 警戒線，需留意外資對台股與新興市場的匯率影響。"
                f"（今日變動 {dxy_chg:+.2f}%）"
            ))
        else:
            alerts.append(_alert_card(
                "positive", f"美元指數偏弱 DXY {dxy_last:.2f}",
                f"DXY 低於 100，美元相對走弱，有利新興市場資金流入與台幣升值動能。"
                f"（今日變動 {dxy_chg:+.2f}%）"
            ))

    # ── 5. USD/TWD 台幣匯率 ───────────────────────────────────
    if twd_hist is not None and len(twd_hist) >= 2:
        twd_last = twd_hist["Close"].iloc[-1]
        twd_prev = twd_hist["Close"].iloc[-2]
        twd_chg  = twd_last - twd_prev

        if twd_last >= 32:
            alerts.append(_alert_card(
                "danger", f"台幣貶值壓力 USD/TWD {twd_last:.3f}",
                f"USD/TWD 達到 32 壓力線，台幣顯著貶值，外資匯出壓力大，需留意對台股的負面影響。"
                f"（今日變動 {twd_chg:+.3f}）"
            ))
        elif twd_last >= 31:
            alerts.append(_alert_card(
                "warning", f"台幣偏弱 USD/TWD {twd_last:.3f}",
                f"USD/TWD 超過 31，台幣偏弱，需觀察是否持續走貶影響外資動向。"
                f"（今日變動 {twd_chg:+.3f}）"
            ))
        elif twd_last <= 29.2:
            alerts.append(_alert_card(
                "positive", f"台幣強勢 USD/TWD {twd_last:.3f}",
                f"USD/TWD 低於 29.2，台幣處於強勢區間，外資流入台股動能相對強勁。"
                f"（今日變動 {twd_chg:+.3f}）"
            ))
        else:
            alerts.append(_alert_card(
                "neutral", f"台幣匯率正常 USD/TWD {twd_last:.3f}",
                f"USD/TWD 處於 29.2～31 正常區間，匯率無異常壓力。"
                f"（今日變動 {twd_chg:+.3f}）"
            ))

    # ── 6. USD/JPY 日圓匯率 ──────────────────────────────────
    if jpy_hist is not None and len(jpy_hist) >= 2:
        jpy_last = jpy_hist["Close"].iloc[-1]
        jpy_prev = jpy_hist["Close"].iloc[-2]
        jpy_chg  = jpy_last - jpy_prev

        if jpy_last >= 160:
            alerts.append(_alert_card(
                "danger", f"日圓危機線 USD/JPY {jpy_last:.2f}",
                f"USD/JPY 超過 160 危機線，日圓嚴重貶值，日本央行干預風險極高，全球避險情緒可能急升。"
                f"（今日變動 {jpy_chg:+.2f}）"
            ))
        elif jpy_last >= 155:
            alerts.append(_alert_card(
                "warning", f"日圓警戒 USD/JPY {jpy_last:.2f}",
                f"USD/JPY 超過 155 警戒線，日圓貶值壓力增加，需留意日本央行政策動向與全球資金避險需求。"
                f"（今日變動 {jpy_chg:+.2f}）"
            ))
        else:
            alerts.append(_alert_card(
                "neutral", f"日圓匯率正常 USD/JPY {jpy_last:.2f}",
                f"USD/JPY 低於 155 警戒線，日圓無過度貶值疑慮。"
                f"（今日變動 {jpy_chg:+.2f}）"
            ))

    # ── 7. 全球股市整體強弱 ───────────────────────────────────
    valid = {k: v for k, v in market_results.items() if v is not None}
    if valid:
        up_count   = sum(1 for v in valid.values() if v["change_pct"] >= 0)
        down_count = len(valid) - up_count
        avg_chg    = sum(v["change_pct"] for v in valid.values()) / len(valid)

        if down_count >= 6:
            alerts.append(_alert_card(
                "danger", f"全球股市普跌（{down_count}/{len(valid)} 下跌）",
                f"監控的 {len(valid)} 個股市指數中，{down_count} 個下跌，平均漲跌幅 {avg_chg:+.2f}%。"
                f"全球風險偏好明顯走弱，建議謹慎操作。"
            ))
        elif down_count >= 4:
            alerts.append(_alert_card(
                "warning", f"全球股市偏弱（{down_count}/{len(valid)} 下跌）",
                f"監控的 {len(valid)} 個股市指數中，{down_count} 個下跌，平均漲跌幅 {avg_chg:+.2f}%。"
                f"市場偏空氣氛升溫。"
            ))
        elif up_count >= 6:
            alerts.append(_alert_card(
                "positive", f"全球股市普漲（{up_count}/{len(valid)} 上漲）",
                f"監控的 {len(valid)} 個股市指數中，{up_count} 個上漲，平均漲跌幅 {avg_chg:+.2f}%。"
                f"全球風險偏好強勁。"
            ))
        else:
            alerts.append(_alert_card(
                "neutral", f"全球股市分歧（{up_count} 漲 / {down_count} 跌）",
                f"監控的 {len(valid)} 個股市指數，平均漲跌幅 {avg_chg:+.2f}%，市場方向分歧。"
            ))

    # ── 8. 原油市場 ───────────────────────────────────────────
    if oil_data is not None:
        oil_price = oil_data["price"]
        oil_chg   = oil_data["change_pct"]

        if oil_price >= 90:
            alerts.append(_alert_card(
                "warning", f"油價警戒 WTI ${oil_price:.2f}",
                f"WTI 原油超過 90 美元警戒線，能源成本上升將推升通膨壓力，聯準會升息預期可能升溫，不利科技股與成長股。"
                f"（今日變動 {oil_chg:+.2f}%）"
            ))
        else:
            alerts.append(_alert_card(
                "neutral", f"油價正常 WTI ${oil_price:.2f}",
                f"WTI 原油低於 90 美元，能源成本對通膨壓力相對可控。"
                f"（今日變動 {oil_chg:+.2f}%）"
            ))

    # ── 輸出所有提醒 ──────────────────────────────────────────
    st.markdown("<div class='summary-grid'>", unsafe_allow_html=True)

    # 分兩欄輸出
    left_items  = alerts[::2]
    right_items = alerts[1::2]

    left_html  = "".join(left_items)
    right_html = "".join(right_items)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown(left_html, unsafe_allow_html=True)

    with col_r:
        st.markdown(right_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("⚠️ 以上分析僅供參考，不構成任何投資建議。所有決策請自行判斷並承擔風險。")


# =========================
# Header
# =========================

st.title("全球市場總覽")
st.caption("影響台股與台指期的重要全球指標")

col_time, col_btn = st.columns([5, 1])

with col_time:
    st.caption(f"🕒 頁面載入時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}　（每小時自動刷新）")

with col_btn:
    if st.button("刷新"):
        st.cache_data.clear()
        st.rerun()

st.divider()


# =========================
# Global Index
# =========================

global_index_title_col, global_index_period_col = st.columns([3, 2])

with global_index_title_col:
    st.markdown(
        section_title_html(
            "全球股市指數",
            "觀察全球主要股市漲跌與短線趨勢，可作為台股、台指期與風險情緒的參考指標",
            font_size=20
        ),
        unsafe_allow_html=True
    )

with global_index_period_col:
    selected_global_index_label = st.radio(
        "全球股市指數期間",
        list(GLOBAL_INDEX_PERIOD_OPTIONS.keys()),
        index=0, horizontal=True,
        label_visibility="collapsed",
        key="global_index_period_selector"
    )

global_index_period = GLOBAL_INDEX_PERIOD_OPTIONS[selected_global_index_label]

results = {name: get_market_data(symbol, chart_period=global_index_period) for name, symbol in WATCHLIST.items()}
valid_results = {k: v for k, v in results.items() if v is not None}

up_count   = sum(1 for v in valid_results.values() if v["change_pct"] >= 0)
down_count = sum(1 for v in valid_results.values() if v["change_pct"] <  0)

c1, c2, c3 = st.columns(3)
c1.metric("上漲市場", up_count)
c2.metric("下跌市場", down_count)
c3.metric("監控指數", len(valid_results))

cards = list(WATCHLIST.items())
for row_start in range(0, len(cards), 4):
    cols = st.columns(4)
    for col, (name, symbol) in zip(cols, cards[row_start:row_start + 4]):
        with col:
            show_market_card(name, symbol, results[name])


# =========================
# Market Sentiment
# =========================

st.divider()

sentiment_title_col, _ = st.columns([3, 2])
with sentiment_title_col:
    st.markdown(
        section_title_html(
            "市場情緒",
            "整合 CNN 恐懼與貪婪指數與 VIX 恐慌指數，觀察市場風險偏好與避險情緒。",
            font_size=20
        ),
        unsafe_allow_html=True
    )

# ── VIX 期間選擇提前到主流程（修正 radio 時序問題）──
selected_vix_label = st.session_state.get("vix_period_selector", "1天")

sentiment_col1, sentiment_col2 = st.columns([1, 1])

with sentiment_col1:
    show_fear_greed_card()

with sentiment_col2:
    show_vix_card(period="1d", selected_label="1天")


# =========================
# Bond / Yield Curve
# =========================

st.divider()

bond_col, yield_col = st.columns([1, 1])

with bond_col:
    with st.container(border=True):
        st.markdown(
            section_title_html(
                "🏛 美國十年期公債殖利率",
                "十年期美債殖利率可視為全球資產定價之錨。4.3%~4.5% 是股市估值壓力區；突破 5% 屬嚴重警戒，可能壓抑科技股與企業融資；低於 1.5% 多出現在衰退、寬鬆或危機時期。",
                font_size=16
            ),
            unsafe_allow_html=True
        )

        ten_year_data = get_bond_history("^TNX", period="6mo")

        if ten_year_data is None:
            st.warning("美債資料讀取失敗")
        else:
            st.metric(
                label="美國10年期公債殖利率",
                value=f"{ten_year_data['price']:.3f}%",
                delta=f"{ten_year_data['change']:+.3f}",
                delta_color="inverse"
            )
            st.caption(f"資料日 {format_date(ten_year_data['last_time'])}")

            bond_fig = draw_line_chart(
                ten_year_data["hist"], "", "^TNX",
                bond_mode=True, y_suffix="%", height=250
            )
            if bond_fig is not None:
                st.plotly_chart(bond_fig, use_container_width=True, config={"displayModeBar": False})

with yield_col:
    show_yield_curve_card(period="6mo")


# =========================
# Currency Trend
# =========================

st.divider()

currency_title_col, currency_period_col = st.columns([3, 2])

with currency_title_col:
    st.markdown(
        section_title_html(
            "💱 匯率走勢",
            "可切換 1 個月、3 個月、6 個月與 1 年區間，觀察美元、台幣與日圓的趨勢變化。",
            font_size=20
        ),
        unsafe_allow_html=True
    )

with currency_period_col:
    selected_period_label = st.radio(
        "匯率走勢期間",
        list(PERIOD_OPTIONS.keys()),
        index=3, horizontal=True,
        label_visibility="collapsed",
        key="currency_period_selector"
    )

currency_period = PERIOD_OPTIONS[selected_period_label]

fx_col1, fx_col2, fx_col3 = st.columns(3)

with fx_col1:
    show_currency_chart_card("美元指數 DXY",   "DX-Y.NYB", period=currency_period)

with fx_col2:
    show_currency_chart_card("USD/TWD 台幣匯率", "TWD=X",   period=currency_period)

with fx_col3:
    show_currency_chart_card("USD/JPY 日幣匯率", "JPY=X",   period=currency_period)


# =========================
# Oil Market
# =========================

st.divider()

st.markdown(
    section_title_html(
        "🛢 原油市場",
        "觀察 Brent、WTI 與兩者價差，可作為通膨、能源成本、地緣政治與景氣循環的參考。",
        font_size=20
    ),
    unsafe_allow_html=True
)

oil_col1, oil_col2, oil_col3 = st.columns(3)

with oil_col1:
    show_currency_chart_card("布蘭特原油 Brent", "BZ=F")

with oil_col2:
    show_currency_chart_card("西德州原油 WTI",   "CL=F")

with oil_col3:
    show_oil_spread_card()


# =========================
# Commodity Market
# =========================

st.divider()

st.markdown(
    section_title_html(
        "💎 商品市場",
        "觀察黃金、銅與天然氣走勢，可作為通膨壓力、景氣循環與避險需求的參考指標。黃金為重要避險資產，銅反映工業景氣，天然氣則是能源成本領先指標。",
        font_size=20
    ),
    unsafe_allow_html=True
)

comm_col1, comm_col2, comm_col3 = st.columns(3)

with comm_col1:
    show_commodity_chart_card("黃金", "GC=F")

with comm_col2:
    show_commodity_chart_card("銅", "HG=F")

with comm_col3:
    show_commodity_chart_card("天然氣", "NG=F")


# =========================
# Crypto Market
# =========================

st.divider()

st.markdown(
    section_title_html(
        "₿ 加密貨幣",
        "觀察 BTC、ETH、SOL 近一年走勢，可作為風險偏好、美元流動性與投機情緒的輔助指標。",
        font_size=20
    ),
    unsafe_allow_html=True
)

crypto_col1, crypto_col2, crypto_col3 = st.columns(3)

def _show_crypto_card(name, symbol):
    hist = get_currency_history(symbol, period="12mo")

    with st.container(border=True):
        st.markdown(
            section_title_html(
                f"₿ {name}",
                TOOLTIP_MAP.get(name, ""),
                font_size=16
            ),
            unsafe_allow_html=True
        )

        if hist is None:
            st.warning(f"{name} 資料讀取失敗")
            return

        last  = hist["Close"].iloc[-1]
        prev  = hist["Close"].iloc[-2]
        change     = last - prev
        change_pct = change / prev * 100
        positive   = change >= 0

        st.metric(
            label="",
            value=f"${last:,.0f}",
            delta=f"{change_pct:+.2f}%",
            delta_color="inverse"
        )
        st.caption(
            f"開盤 {hist['Open'].iloc[-1]:,.0f}　"
            f"最高 {hist['High'].iloc[-1]:,.0f}　"
            f"最低 {hist['Low'].iloc[-1]:,.0f}　"
            f"資料日 {format_date(hist.index[-1])}"
        )

        fig = draw_crypto_chart(hist, positive)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


with crypto_col1:
    _show_crypto_card("BTC Bitcoin",  "BTC-USD")

with crypto_col2:
    _show_crypto_card("ETH Ethereum", "ETH-USD")

with crypto_col3:
    _show_crypto_card("SOL Solana",   "SOL-USD")


# =========================
# Market Summary & Alerts
# =========================

st.divider()

# 收集各指標資料（多數已 cache，不會重複請求）
_vix_data   = get_vix_data("1d")
_fg_data    = get_fear_greed_data()
_bond_data  = get_bond_history("^TNX", period="6mo")
_dxy_hist   = get_currency_history("DX-Y.NYB", period="1mo")
_twd_hist   = get_currency_history("TWD=X",    period="1mo")
_jpy_hist   = get_currency_history("JPY=X",    period="1mo")
_oil_data   = get_market_data("CL=F")

show_market_summary(
    market_results=results,
    vix_data=_vix_data,
    fg_data=_fg_data,
    bond_data=_bond_data,
    dxy_hist=_dxy_hist,
    twd_hist=_twd_hist,
    jpy_hist=_jpy_hist,
    oil_data=_oil_data,
)