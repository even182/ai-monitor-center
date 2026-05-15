# -*- coding: utf-8 -*-
"""
stock.py

台股估值監控儀表板 stock.py

本版升級：
1. 歷史 PE 不再用「目前 TTM EPS」固定回推
2. 優先使用 yfinance earnings_dates 的歷史季度 EPS
3. 自動建立「歷史 TTM EPS」
4. 每日股價 ÷ 當時 TTM EPS = 真正接近歷史 PE 的走勢
5. 若抓不到歷史 EPS，才退回舊版近似法
6. 合理 PE = 近 3 年歷史 PE 平均值
7. TTM 模式：目前 PE = 目前股價 ÷ TTM EPS
8. Forward 模式：預估股價 = 目前 PE × Forward EPS

執行：
    pip install streamlit pandas numpy plotly yfinance
    streamlit run stock.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Tuple
from pathlib import Path
import json
import urllib.request

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(
    page_title="台股估值監控儀表板",
    page_icon="📈",
    layout="wide",
)


st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-size: 14px !important;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 1.5rem;
    max-width: 1500px;
}

h1 {
    font-size: 1.70rem !important;
    margin-bottom: 0.3rem !important;
}

h2 {
    font-size: 1.20rem !important;
    margin-top: 0.8rem !important;
    margin-bottom: 0.45rem !important;
}

h3 {
    font-size: 1.05rem !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.82rem !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.50rem !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.72rem !important;
}

.stNumberInput label, .stTextInput label, .stRadio label {
    font-size: 0.84rem !important;
}

.small-note {
    font-size: 0.80rem;
    color: #6b7280;
}

.stock-title {
    font-size: 1.18rem;
    font-weight: 700;
    margin-bottom: 0.7rem;
}

.source-note {
    font-size: 0.78rem;
    color: #6b7280;
    text-align: right;
}

.status-box {
    background: #e8f2ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 0.70rem 1rem;
    color: #075985;
    font-weight: 700;
}


.name-info-icon {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    margin-left: 4px;
    border-radius: 50%;
    background: #e2e8f0;
    color: #475569;
    font-size: 11px;
    font-weight: 800;
    cursor: help;
}

.name-info-icon::after {
    content: attr(data-tooltip);
    position: absolute;
    left: 50%;
    bottom: calc(100% + 8px);
    transform: translateX(-50%);
    min-width: 260px;
    max-width: 360px;
    padding: 8px 10px;
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.96);
    color: white;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.5;
    white-space: pre-line;
    text-align: left;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.18);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    z-index: 9999;
}

.name-info-icon:hover::after {
    opacity: 1;
    visibility: visible;
}

</style>
""",
    unsafe_allow_html=True,
)



TW_STOCK_NAMES = {
    "2330": "台積電",
    "2308": "台達電",
    "2454": "聯發科",
    "2317": "鴻海",
    "3711": "日月光投控",
    "5274": "信驊",
    "6515": "穎崴",
    "7769": "鴻勁",
    "6223": "旺矽",
    "6669": "緯穎",
    "2412": "中華電信",
    "2327": "國巨",
    "6510": "精測",
    "6683": "雍智",
    "3042": "晶技",
    "3221": "台嘉碩",
    "8182": "加高",
    "8289": "泰藝",
    "2484": "希華",
    "6174": "安碁",
    "6805": "富世達",
    "3653": "健策",
    "6285": "啟碁",
    "2313": "華通",
    "3105": "穩懋",
    "8086": "宏捷科",
    "2455": "全新",
    "5388": "中磊",
    "3596": "智易",
    "3491": "昇達科",
    "4979": "華星光",
    "3081": "聯亞",
    "3363": "上詮",
    "3450": "聯鈞",
    "3163": "波若威",
    "6442": "光聖",
    "3234": "光環",
    "2345": "智邦",
}


def normalize_stock_code_for_lookup(value) -> str:
    """
    將 Excel / 手動輸入的股票代碼標準化。
    例如：
    2327.0 -> 2327
    50 -> 0050
    2327.TW -> 2327
    5274.TWO -> 5274
    """
    if value is None:
        return ""

    code = str(value).strip().upper()
    code = code.replace(".TW", "").replace(".TWO", "")

    if code.endswith(".0"):
        code = code[:-2]

    # 移除常見空白與不可見字元
    code = code.replace("\u3000", "").replace(" ", "")

    if code.isdigit() and len(code) < 4:
        code = code.zfill(4)

    return code


@st.cache_data(ttl=86400, show_spinner=False)
def load_stock_name_map() -> Dict[str, str]:
    """
    從 data/stock_name.xlsx 載入股票中文名稱。
    支援常見欄位：
    - 股票代號 / 證券代號 / 代號 / code / stock_code
    - 股票名稱 / 證券名稱 / 名稱 / name / stock_name

    若找不到欄位，預設使用前兩欄作為代號與名稱。
    """
    possible_paths = [
        Path.cwd() / "data" / "stock_name.xlsx",
        Path(__file__).resolve().parent.parent / "data" / "stock_name.xlsx",
        Path(__file__).resolve().parent / "data" / "stock_name.xlsx",
    ]

    file_path = None
    for p in possible_paths:
        if p.exists():
            file_path = p
            break

    if file_path is None:
        return {}

    try:
        df = pd.read_excel(file_path, dtype=str)
    except Exception:
        return {}

    if df is None or df.empty:
        return {}

    df.columns = [str(c).strip() for c in df.columns]

    code_candidates = [
        "股票代號", "證券代號", "代號", "股票代碼", "代碼",
        "code", "Code", "stock_code", "StockCode", "stock_id", "StockID",
    ]

    name_candidates = [
        "股票名稱", "證券名稱", "名稱", "公司名稱", "簡稱",
        "name", "Name", "stock_name", "StockName", "CompanyName",
    ]

    code_col = next((c for c in code_candidates if c in df.columns), None)
    name_col = next((c for c in name_candidates if c in df.columns), None)

    # 若欄位名稱不符合，預設前兩欄
    if code_col is None or name_col is None:
        if len(df.columns) >= 2:
            code_col = df.columns[0]
            name_col = df.columns[1]
        else:
            return {}

    result = {}

    for _, row in df.iterrows():
        code = normalize_stock_code_for_lookup(row.get(code_col))
        name = str(row.get(name_col, "")).strip()

        if not code or not name or name.lower() == "nan":
            continue

        result[code] = name

    return result


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_tw_stock_name(stock_code: str) -> str:
    """
    嘗試從台股公開資料抓中文股名。
    若失敗則回傳空字串，讓畫面使用 Yahoo 英文名。
    """
    code = normalize_stock_code_for_lookup(stock_code)

    # 1. 先查內建常用股票名稱
    if code in TW_STOCK_NAMES:
        return TW_STOCK_NAMES[code]

    # 2. 再查 data/stock_name.xlsx
    stock_name_map = load_stock_name_map()
    if code in stock_name_map:
        return stock_name_map[code]

    # 3. 最後才嘗試線上公開資料
    urls = [
        "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
        "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
    ]

    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json,text/plain,*/*",
                },
            )

            with urllib.request.urlopen(req, timeout=8) as response:
                raw = response.read().decode("utf-8", errors="ignore")

            rows = json.loads(raw)

            if not isinstance(rows, list):
                continue

            for row in rows:
                if not isinstance(row, dict):
                    continue

                values = {str(k): str(v).strip() for k, v in row.items()}

                # 找代碼欄位
                matched = False
                for key, value in values.items():
                    if value == code:
                        matched = True
                        break

                if not matched:
                    continue

                # 優先找常見名稱欄位
                for name_key in [
                    "Name",
                    "CompanyName",
                    "CompanyAbbreviation",
                    "SecuritiesCompanyName",
                    "SecuritiesCompanyAbbreviation",
                    "證券名稱",
                    "公司名稱",
                    "有價證券名稱",
                ]:
                    if name_key in values and values[name_key] and values[name_key] != code:
                        return values[name_key]

                # 模糊找名稱欄位
                for key, value in values.items():
                    key_lower = key.lower()
                    if (
                        ("name" in key_lower or "名稱" in key or "公司" in key)
                        and value
                        and value != code
                    ):
                        return value

        except Exception:
            continue

    return ""


def normalize_tw_symbol(symbol: str) -> str:
    symbol = str(symbol).strip().upper()
    if not symbol:
        return ""
    if "." in symbol:
        return symbol
    return f"{symbol}.TW"


def safe_float(value, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def get_period_label(mode: str) -> str:
    now = datetime.now()
    q = (now.month - 1) // 3 + 1
    if mode == "Forward":
        return f"{now.year} Q{q} Forward 12M"
    return f"{now.year} Q{q} TTM"


def clean_earnings_eps_table(earnings_dates: pd.DataFrame) -> pd.DataFrame:
    """
    從 yfinance earnings_dates 整理出季度 EPS。
    不同版本 yfinance 欄位名稱可能不同，所以用模糊方式找 EPS 欄位。
    """
    if earnings_dates is None or earnings_dates.empty:
        return pd.DataFrame(columns=["date", "eps"])

    df = earnings_dates.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            return pd.DataFrame(columns=["date", "eps"])

    eps_col = None
    candidates = [
        "Reported EPS",
        "ReportedEPS",
        "EPS Actual",
        "epsActual",
        "actualEPS",
        "Actual EPS",
    ]

    for col in candidates:
        if col in df.columns:
            eps_col = col
            break

    if eps_col is None:
        for col in df.columns:
            if "eps" in str(col).lower() and ("reported" in str(col).lower() or "actual" in str(col).lower()):
                eps_col = col
                break

    if eps_col is None:
        for col in df.columns:
            if "eps" in str(col).lower():
                eps_col = col
                break

    if eps_col is None:
        return pd.DataFrame(columns=["date", "eps"])

    out = pd.DataFrame({
        "date": pd.to_datetime(df.index).tz_localize(None),
        "eps": pd.to_numeric(df[eps_col], errors="coerce"),
    })

    out = out.dropna(subset=["date", "eps"])
    out = out[out["eps"] > 0]
    out = out.sort_values("date")
    out = out.drop_duplicates(subset=["date"], keep="last")

    return out


def build_daily_historical_pe(price_df: pd.DataFrame, eps_quarter_df: pd.DataFrame, current_ttm_eps: Optional[float]) -> Tuple[pd.DataFrame, str]:
    """
    用歷史季度 EPS 建立每日 TTM EPS，並計算每日 PE。

    若歷史 EPS 不足：
    fallback = 使用目前 TTM EPS 固定回推。
    """
    df = price_df.copy()
    df = df[["Close"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)

    method = "歷史季度 EPS"

    if eps_quarter_df is not None and len(eps_quarter_df) >= 4:
        eps_df = eps_quarter_df.copy().sort_values("date")
        eps_df["ttm_eps"] = eps_df["eps"].rolling(4).sum()
        eps_df = eps_df.dropna(subset=["ttm_eps"])

        if len(eps_df) >= 1:
            left = df.reset_index().rename(columns={"index": "date"})
            right = eps_df[["date", "ttm_eps"]].sort_values("date")

            merged = pd.merge_asof(
                left.sort_values("date"),
                right,
                on="date",
                direction="backward",
            )

            merged = merged.dropna(subset=["ttm_eps"])
            merged["PE"] = merged["Close"] / merged["ttm_eps"]
            merged = merged.replace([np.inf, -np.inf], np.nan).dropna(subset=["PE"])

            if not merged.empty:
                merged = merged.set_index("date")
                return merged[["Close", "ttm_eps", "PE"]], method

    method = "目前 TTM EPS 近似回推"

    if current_ttm_eps is not None and current_ttm_eps > 0:
        df["ttm_eps"] = current_ttm_eps
        df["PE"] = df["Close"] / current_ttm_eps
    else:
        df["ttm_eps"] = np.nan
        df["PE"] = np.nan

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["PE"])
    return df[["Close", "ttm_eps", "PE"]], method


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_stock_info(symbol: str) -> Dict:
    result = {
        "symbol": symbol,
        "name": symbol,
        "current_price": None,
        "trailing_eps": None,
        "forward_eps": None,
        "current_pe": None,
        "forward_pe": None,
        "hist_pe_low": None,
        "hist_pe_mid": None,
        "hist_pe_high": None,
        "hist_3y": pd.DataFrame(),
        "eps_quarter": pd.DataFrame(),
        "pe_method": "",
        "error": "",
    }

    if yf is None:
        result["error"] = "尚未安裝 yfinance，請先執行：pip install yfinance"
        return result

    try:
        ticker = yf.Ticker(symbol)

        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        result["name"] = info.get("longName") or info.get("shortName") or symbol
        result["trailing_eps"] = safe_float(info.get("trailingEps"))
        result["forward_eps"] = safe_float(info.get("forwardEps"))
        result["forward_pe"] = safe_float(info.get("forwardPE"))

        hist_5d = ticker.history(period="5d", auto_adjust=False)
        if hist_5d is not None and not hist_5d.empty:
            close = hist_5d["Close"].dropna()
            if not close.empty:
                result["current_price"] = float(close.iloc[-1])

        price = result["current_price"]
        ttm_eps = result["trailing_eps"]

        if price is not None and ttm_eps is not None and ttm_eps > 0:
            result["current_pe"] = price / ttm_eps
        else:
            result["current_pe"] = safe_float(info.get("trailingPE"))

        # 抓 3 年價格
        hist_price = ticker.history(period="3y", auto_adjust=False)

        # 抓歷史 EPS
        eps_quarter = pd.DataFrame(columns=["date", "eps"])
        try:
            ed = ticker.get_earnings_dates(limit=24)
            eps_quarter = clean_earnings_eps_table(ed)
        except Exception:
            eps_quarter = pd.DataFrame(columns=["date", "eps"])

        result["eps_quarter"] = eps_quarter

        if hist_price is not None and not hist_price.empty:
            hist_df, method = build_daily_historical_pe(hist_price, eps_quarter, ttm_eps)
            result["hist_3y"] = hist_df
            result["pe_method"] = method

            pe_series = hist_df["PE"].replace([np.inf, -np.inf], np.nan).dropna()

            if len(pe_series) >= 120:
                result["hist_pe_low"] = round(float(pe_series.quantile(0.20)), 2)
                result["hist_pe_mid"] = round(float(pe_series.mean()), 2)
                result["hist_pe_high"] = round(float(pe_series.quantile(0.80)), 2)

        if result["current_price"] is None:
            result["error"] = "無法抓取目前股價，請確認股票代號是否正確。"

    except Exception as e:
        result["error"] = f"資料抓取失敗：{e}"

    return result


def default_pe_values(stock: Dict) -> Tuple[float, float, float]:
    current_pe = stock["current_pe"]

    low = stock["hist_pe_low"]
    mid = stock["hist_pe_mid"]
    high = stock["hist_pe_high"]

    if mid is None or mid <= 0:
        mid = current_pe if current_pe is not None and current_pe > 0 else 22.0
    mid = float(mid)

    low = float(low if low is not None and low > 0 else mid * 0.8)
    high = float(high if high is not None and high > 0 else mid * 1.2)

    if low > mid:
        low = mid * 0.8

    if high < mid:
        high = mid * 1.2

    return round(low, 2), round(mid, 2), round(high, 2)


def calc_valuation(
    current_price: float,
    eps: float,
    low_pe: float,
    mid_pe: float,
    high_pe: float,
) -> Dict:
    conservative = eps * low_pe
    fair = eps * mid_pe
    optimistic = eps * high_pe

    discount = ((fair - current_price) / fair * 100) if fair > 0 else 0

    if current_price <= 0 or eps <= 0 or fair <= 0:
        status = "資料不足"
        action = "請確認股價、EPS、PE 是否正確"
    elif current_price < conservative:
        status = "明顯低估"
        action = "可深入研究，適合分批布局"
    elif current_price < fair:
        status = "合理偏低"
        action = "可觀察，分批買進較佳"
    elif current_price <= optimistic:
        status = "合理偏高"
        action = "續抱為主，不建議追高"
    else:
        status = "偏貴"
        action = "注意風險，等待拉回"

    return {
        "conservative": conservative,
        "fair": fair,
        "optimistic": optimistic,
        "discount": discount,
        "status": status,
        "action": action,
    }


def status_color(status: str) -> str:
    if status == "明顯低估":
        return "#0f9d58"
    if status == "合理偏低":
        return "#2563eb"
    if status == "合理偏高":
        return "#f59e0b"
    if status == "偏貴":
        return "#dc2626"
    return "#6b7280"


def draw_value_gauge(
    current_price: float,
    display_value: float,
    valuation: Dict,
    mode: str,
    period_label: str,
    current_pe: float,
):
    conservative = max(float(valuation["conservative"]), 0)
    fair = max(float(valuation["fair"]), conservative)
    optimistic = max(float(valuation["optimistic"]), fair)

    max_value = max(current_price, display_value, conservative, fair, optimistic, 1) * 1.15

    if mode == "Forward":
        title = "預估股價（目前本益比 × Forward EPS）"
        value_label = f"使用目前本益比 {current_pe:.2f}"
    else:
        title = "目前股價（TWD）"
        value_label = f"目前本益比 {current_pe:.2f}"

    fig = go.Figure()

    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=display_value,
            title={
                "text": f"{title}<br><span style='font-size:12px;color:#6b7280'>{period_label}</span>",
                "font": {"size": 16},
            },
            number={
                "font": {"size": 30, "color": status_color(valuation["status"])},
                "valueformat": ",.2f",
            },
            gauge={
                "shape": "angular",
                "axis": {
                    "range": [0, max_value],
                    "tickfont": {"size": 10},
                    "tickformat": ",.0f",
                },
                "bar": {
                    "color": "rgba(0,0,0,0)",
                    "thickness": 0.20,
                },
                "steps": [
                    {"range": [0, conservative], "color": "#dcfce7"},
                    {"range": [conservative, fair], "color": "#bbf7d0"},
                    {"range": [fair, optimistic], "color": "#fed7aa"},
                    {"range": [optimistic, max_value], "color": "#fecaca"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 5},
                    "thickness": 0.85,
                    "value": display_value,
                },
            },
        )
    )

    fig.add_annotation(
        x=0.5,
        y=-0.10,
        text=value_label,
        showarrow=False,
        font=dict(size=12, color="#374151"),
        xref="paper",
        yref="paper",
    )

    fig.update_layout(
        height=390,
        margin=dict(l=35, r=35, t=75, b=55),
        font=dict(size=11),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def draw_pe_price_chart(stock: Dict, symbol: str, fair_price: Optional[float] = None):
    df = stock["hist_3y"]

    if df is None or df.empty or "Close" not in df.columns:
        st.info("目前無法產生近 3 年股價圖。")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            name="股價 TWD",
            mode="lines",
            line=dict(color="#FF7A00", width=2.6),
        )
    )

    if fair_price is not None and fair_price > 0:
        fig.add_hline(
            y=fair_price,
            line_color="green",
            line_width=2,
            line_dash="dash",
            annotation_text=f"合理價 {fair_price:,.2f}",
            annotation_position="top left",
            annotation_font_color="green",
            annotation_bgcolor="rgba(255,255,255,0.85)",
        )

    optimistic_price = stock.get("optimistic_price")

    if optimistic_price is not None and optimistic_price > 0:
        fig.add_hline(
            y=optimistic_price,
            line_color="red",
            line_width=2,
            line_dash="dot",
            annotation_text=f"樂觀價 {optimistic_price:,.2f}",
            annotation_position="top left",
            annotation_font_color="red",
            annotation_bgcolor="rgba(255,255,255,0.85)",
        )

    fig.update_layout(
        title=f"{symbol} 近 3 年股價走勢",
        height=370,
        margin=dict(l=25, r=25, t=55, b=25),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        yaxis=dict(
            title=dict(text="股價 TWD", font=dict(color="#FF7A00")),
            side="left",
            showgrid=True,
            tickfont=dict(color="#FF7A00"),
        ),
        xaxis=dict(title=""),
        font=dict(size=11),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_stock_block(block_title: str, symbol: str, key_prefix: str):
    symbol = normalize_tw_symbol(symbol)
    stock = fetch_stock_info(symbol)

    st.markdown(f"## {block_title}")

    if stock["error"]:
        st.warning(stock["error"])

    current_price = float(stock["current_price"] or 0)
    trailing_eps = stock["trailing_eps"] or 10.0
    forward_eps = stock["forward_eps"] or trailing_eps
    current_pe = stock["current_pe"] or (current_price / trailing_eps if trailing_eps else 22.0)

    low_default, mid_default, high_default = default_pe_values(stock)

    left, right = st.columns([1.05, 1.15], gap="large")

    with left:
        display_symbol = symbol.replace(".TW", "").replace(".TWO", "")
        tw_name = fetch_tw_stock_name(display_symbol)

        if tw_name:
            title_text = f"{display_symbol}｜{tw_name}｜{stock['name']}"
        else:
            title_text = f"{display_symbol}｜{stock['name']}"

        st.markdown(
            f"<div class='stock-title'>{title_text}</div>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            mode_label = st.radio(
                "估值模式",
                ["TTM EPS（近12個月）", "Forward EPS（預估未來12個月）"],
                horizontal=True,
                key=f"{key_prefix}_mode",
            )

        mode = "Forward" if mode_label.startswith("Forward") else "TTM"
        period_label = get_period_label(mode)

        if mode == "Forward":
            selected_eps = float(forward_eps)
            eps_name = "Forward EPS"
            pe_name = "目前本益比（用 TTM EPS 算）"
        else:
            selected_eps = float(trailing_eps)
            eps_name = "TTM EPS"
            pe_name = "目前本益比（股價 ÷ TTM EPS）"

        eps_key = f"{key_prefix}_eps"
        mode_key = f"{key_prefix}_last_mode"

        if st.session_state.get(mode_key) != mode:
            st.session_state[eps_key] = selected_eps
            st.session_state[mode_key] = mode

        if eps_key not in st.session_state:
            st.session_state[eps_key] = selected_eps

        c1, c2, c3 = st.columns(3)
        c1.metric("目前股價", f"{current_price:,.2f}" if current_price else "無資料")
        c2.metric("使用 EPS", f"{selected_eps:,.2f}", eps_name)
        c3.metric(pe_name, f"{current_pe:,.2f}" if current_pe else "無資料")

        st.markdown(
            f"<div class='small-note'>估算時間：{period_label}。合理 PE 預設使用近 3 年 PE 均值；低/高 PE 參考近 3 年區間，可自行修改。</div>",
            unsafe_allow_html=True,
        )

        if mode == "Forward" and stock["forward_eps"] is None:
            st.warning("此股票目前抓不到 Forward EPS，暫時使用 TTM EPS，可手動調整。")

        with st.container(border=True):
            e_col, p1, p2, p3 = st.columns([1.05, 1, 1, 1])

            with e_col:
                eps_input = st.number_input(
                    f"估值用 EPS（{eps_name}）",
                    value=float(st.session_state[eps_key]),
                    step=0.1,
                    key=eps_key,
                )

            with p1:
                low_pe = st.number_input(
                    "低 PE（3年）",
                    min_value=0.0,
                    value=float(low_default),
                    step=0.5,
                    key=f"{key_prefix}_low_pe",
                )

            with p2:
                mid_pe = st.number_input(
                    "合理 PE（3年均值）",
                    min_value=0.0,
                    value=float(mid_default),
                    step=0.5,
                    key=f"{key_prefix}_mid_pe",
                )

            with p3:
                high_pe = st.number_input(
                    "高 PE（3年）",
                    min_value=0.0,
                    value=float(high_default),
                    step=0.5,
                    key=f"{key_prefix}_high_pe",
                )

        valuation = calc_valuation(
            current_price=current_price,
            eps=eps_input,
            low_pe=low_pe,
            mid_pe=mid_pe,
            high_pe=high_pe,
        )

        if mode == "Forward":
            display_value = current_pe * eps_input
        else:
            display_value = current_price

        v1, v2, v3, v4 = st.columns(4)
        v1.metric("保守價", f"{valuation['conservative']:,.2f}")
        v2.metric("合理價", f"{valuation['fair']:,.2f}")
        v3.metric("樂觀價", f"{valuation['optimistic']:,.2f}")

        discount_color = "red" if valuation["discount"] < 0 else "green"
        v4.markdown(
            f"""
            <div style="font-size:0.82rem;color:#334155;margin-bottom:2px;">距合理價</div>
            <div style="font-size:1.50rem;font-weight:600;color:{discount_color};line-height:1.25;">
                {valuation['discount']:,.2f}%
            </div>
            """,
            unsafe_allow_html=True,
        )

        if mode == "Forward":
            st.metric(
                "Forward 推估股價（目前 PE × Forward EPS）",
                f"{display_value:,.2f}",
                help="目前 PE = 目前股價 ÷ TTM EPS；Forward 推估股價 = 目前 PE × Forward EPS。",
            )

        st.markdown(
            f"<div class='status-box'>狀態：{valuation['status']}｜{valuation['action']}</div>",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            f"<div class='source-note'>資料來源：Yahoo Finance / yfinance<br>PE計算：{stock['pe_method']}</div>",
            unsafe_allow_html=True,
        )

        draw_value_gauge(
            current_price=current_price,
            display_value=display_value,
            valuation=valuation,
            mode=mode,
            period_label=period_label,
            current_pe=current_pe,
        )

    stock["optimistic_price"] = valuation["optimistic"]
    draw_pe_price_chart(stock, symbol, valuation["fair"])

    st.markdown(
        "<div class='small-note'>說明：目前 PE = 目前股價 ÷ TTM EPS；Forward 推估股價 = 目前 PE × Forward EPS；下方紅色虛線為合理價。</div>",
        unsafe_allow_html=True,
    )

    st.divider()



# =========================
# Main
# =========================

st.markdown("""
<div style="padding-top:8px;padding-bottom:2px;">
<h1 style="margin-bottom:0px;padding-bottom:0px;line-height:1.25;">
📈 台股估值監控儀表板
</h1>
</div>
""", unsafe_allow_html=True)

st.caption("Stock Valuation｜EPS × PE 合理股價監控")

page_mode = st.radio(
    "選擇監控頁面",
    [
        "市值排行前五",
        "股價排行前五",
        "AI 測試四大天王",
        "石英元件",
        "液冷散熱",
        "Starlink／低軌衛星",
        "光通訊/矽光子",
        "自選股監測",
    ],
    horizontal=True,
    key="stock_page_mode",
)

CONCEPT_STOCKS = {
    "AI 測試四大天王": [
        (
            "6510.TWO",
            "精測",
            """專門處理最難、最精密的 AI 晶片測試。
越高階的晶片，他們越有機會賺。""",
        ),
        (
            "6223.TWO",
            "旺矽",
            """做的是 AI 測試設備整合。
簡單講就是：幫客戶把整套測試流程一次搞定。""",
        ),
        (
            "6515",
            "穎崴",
            """主攻高速測試座。
很多高階 AI 晶片最後測試都需要它，尤其跟 NVIDIA 題材連動很深。""",
        ),
        (
            "6683.TWO",
            "雍智",
            """專做客製化 ASIC 測試。
現在很多美國大廠都在自己做 AI 晶片，這類需求反而越來越多。""",
        ),
    ],
    "石英元件": [
        (
            "3042",
            "晶技",
            """族群龍頭，切入AI與低軌衛星，屬於趨勢型公司""",
        ),
        (
            "3221.TWO",
            "台嘉碩",
            """射頻元件延伸到AI通訊鏈，題材開始被市場認同""",
        ),
        (
            "8182.TWO",
            "加高",
            """網通應用明確，近期走勢相對強勢""",
        ),
        (
            "8289.TWO",
            "泰藝",
            """高精度產品切入高速傳輸，屬於技術含量較高的一塊""",
        ),
        (
            "2484",
            "希華",
            """往上游長晶發展，強調成本控制與供應穩定""",
        ),
        (
            "6174.TWO",
            "安碁",
            """工控與物聯網應用，搭配產業循環回溫""",
        ),
    ],
    "液冷散熱": [
        (
            "2308",
            "台達電",
            """AI資料中心「電力＋液冷」雙核心。AI PSU 全球龍頭，切入 CDU、Sidecar、泵浦與整體熱管理，受惠 GB200/GB300 高功耗趨勢。
核心產品: PSU / CDU / 泵浦""",
        ),
        (
            "3017",
            "奇鋐",
            """液冷散熱主升段核心股。具水冷板、CDU、機櫃整合能力，深度綁定 NVIDIA 與 AI 伺服器供應鏈。
核心產品: 水冷板 / CDU""",
        ),
        (
            "3324.TWO",
            "雙鴻",
            """從傳統散熱升級液冷模組龍頭。強項為冷板、分歧管與高客製化散熱方案，AI 液冷營收快速成長。
核心產品: 冷板 / 分歧管""",
        ),
        (
            "6805",
            "富世達",
            """AI 液冷快接頭（QD）核心受惠股。高技術門檻與認證優勢，受惠 GB300 與高密度液冷滲透率提升。
核心產品: 快接頭 QD""",
        ),
        (
            "3653",
            "健策",
            """高階散熱與封裝技術代表。MCL 微通道與均熱片技術切入高功耗 GPU 散熱，具高毛利與高門檻優勢。
核心產品: MCL / 均熱片""",
        ),
    ],
    "Starlink／低軌衛星": [
        (
            "6285",
            "啟碁",
            """Starlink 地面終端與天線模組核心供應商。
受惠低軌衛星、企業專網與衛星直連手機（Direct-to-Cell）長線趨勢。""",
        ),
        (
            "2313",
            "華通",
            """Starlink／低軌衛星 PCB 核心受惠股。
高頻高速板與衛星板技術門檻高，為台股 LEO 最具代表性的 PCB 廠。""",
        ),
        (
            "3105.TWO",
            "穩懋",
            """GaAs 射頻晶圓龍頭。
受惠低軌衛星 Ku／Ka 高頻通訊需求，長線連動 6G、衛星與 AI 通訊基建。""",
        ),
        (
            "8086.TWO",
            "宏捷科",
            """RF 功率放大器（PA）受惠股。
具高頻通訊與低軌衛星題材，受惠衛星射頻需求提升。""",
        ),
        (
            "3042",
            "晶技",
            """高頻石英元件核心廠。
低軌衛星、高速傳輸與 AI 網通皆需高精度頻率控制。""",
        ),
        (
            "3221.TWO",
            "台嘉碩",
            """高頻石英與 RF 元件供應商。
受惠衛星通訊、高速傳輸與高頻網通升級。""",
        ),
        (
            "2455",
            "全新",
            """光通訊與 RF 高頻材料廠。
受惠高速光通訊、衛星與 AI 網路升級趨勢。""",
        ),
        (
            "5388",
            "中磊",
            """衛星地面設備與網通設備供應商。
受惠偏遠地區寬頻與企業衛星網路建置。""",
        ),
        (
            "3596",
            "智易",
            """衛星寬頻 CPE／Gateway 題材股。
具網通設備與衛星地面終端成長潛力。""",
        ),
        (
            "3491.TWO",
            "昇達科",
            """高頻微波與毫米波通訊廠。
低軌衛星與軍工通訊題材強，波動性也較高。""",
        ),
    ],
    "光通訊/矽光子": [
        (
            "4979.TWO",
            "華星光",
            """AI 光模組核心人氣股。受惠 800G／1.6T 高速傳輸升級，為 AI 資料中心光通訊主流受惠股。
定位: 光模組核心""",
        ),
        (
            "3081.TWO",
            "聯亞",
            """矽光子與 InP 磊晶核心廠。掌握高速雷射光源技術，受惠 CPO 與下一代 AI 光互連。
定位: 矽光子核心""",
        ),
        (
            "3363.TWO",
            "上詮",
            """MPO 光纖連接器龍頭。受惠 CPO、AI 高速交換器與光纖佈線升級。
定位: CPO 核心""",
        ),
        (
            "3450",
            "聯鈞",
            """高速光模組與雷射封裝廠。受惠 AI Data Center 高頻寬需求與光模組升級。
定位: 高速光模組""",
        ),
        (
            "3163.TWO",
            "波若威",
            """光纖被動元件與高速傳輸核心供應商。受惠 AI 資料中心光纖需求成長。
定位: 光纖元件""",
        ),
        (
            "6442",
            "光聖",
            """光纖連接與高速傳輸元件廠。受惠 AI 高速傳輸與雲端資料中心建置。
定位: 高速傳輸元件""",
        ),
        (
            "3234.TWO",
            "光環",
            """光通訊雷射元件廠。受惠高速光模組與 AI 光通訊升級趨勢。
定位: 光纖高速連接""",
        ),
        (
            "2345",
            "智邦",
            """AI 高速交換器龍頭。受惠 800G／1.6T 交換器升級與大型 AI 資料中心建置。
定位: AI 高速交換器""",
        ),
    ]
}


MARKET_CAP_TOP5 = [
    ("2330", "台積電"),
    ("2308", "台達電"),
    ("2454", "聯發科"),
    ("2317", "鴻海"),
    ("3711", "日月光投控"),
]

PRICE_TOP5 = [
    ("5274.TWO", "信驊"),
    ("6515", "穎崴"),
    ("7769", "鴻勁"),
    ("6223.TWO", "旺矽"),
    ("6669", "緯穎"),
]



def html_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def stock_display_label(symbol: str, name: str, note: str = "") -> str:
    display_symbol = symbol.replace(".TWO", "").replace(".TW", "")
    if note:
        tooltip = html_escape(note)
        return (
            f"{display_symbol}｜{name}"
            f"<span class='name-info-icon' data-tooltip=\"{tooltip}\">i</span>"
        )
    return f"{display_symbol}｜{name}"


def render_rank_page(title: str, stock_list: list, key_prefix: str):
    st.markdown(f"## {title}")
    st.caption("點開個股區塊即可查看 EPS / PE 估值、Forward 推估股價與近 3 年股價走勢。")

    for i, item in enumerate(stock_list, start=1):
        if len(item) >= 3:
            symbol, name, note = item[0], item[1], item[2]
        else:
            symbol, name = item[0], item[1]
            note = ""

        display_symbol = symbol.replace(".TWO", "").replace(".TW", "")
        label_html = stock_display_label(symbol, name, note)
        plain_title = f"{i}. {display_symbol}｜{name}"

        with st.expander(plain_title, expanded=True):
            if note:
                st.markdown(
                    f"<div style='font-size:1.05rem;font-weight:700;margin-bottom:0.6rem;'>{i}. {label_html}</div>",
                    unsafe_allow_html=True,
                )

            render_stock_block(
                block_title=plain_title,
                symbol=symbol,
                key_prefix=f"{key_prefix}_{symbol}",
            )


if page_mode == "市值排行前五":
    render_rank_page(
        title="市值排行前五",
        stock_list=MARKET_CAP_TOP5,
        key_prefix="market_cap",
    )

elif page_mode == "股價排行前五":
    render_rank_page(
        title="股價排行前五",
        stock_list=PRICE_TOP5,
        key_prefix="price_rank",
    )

elif page_mode == "AI 測試四大天王":
    render_rank_page(
        title="AI 測試四大天王",
        stock_list=CONCEPT_STOCKS.get("AI 測試四大天王", []),
        key_prefix="concept_ai_test",
    )

elif page_mode == "石英元件":
    render_rank_page(
        title="石英元件",
        stock_list=CONCEPT_STOCKS.get("石英元件", []),
        key_prefix="concept_quartz",
    )

elif page_mode == "液冷散熱":
    render_rank_page(
        title="液冷散熱",
        stock_list=CONCEPT_STOCKS.get("液冷散熱", []),
        key_prefix="concept_liquid",
    )

elif page_mode == "Starlink／低軌衛星":
    render_rank_page(
        title="Starlink／低軌衛星",
        stock_list=CONCEPT_STOCKS.get("Starlink／低軌衛星", []),
        key_prefix="concept_starlink",
    )

elif page_mode == "光通訊/矽光子":
    render_rank_page(
        title="光通訊/矽光子",
        stock_list=CONCEPT_STOCKS.get("光通訊/矽光子", []),
        key_prefix="concept_optical",
    )

else:
    st.markdown("## 自選股監測")

    input_col, spacer = st.columns([0.25, 0.75])
    with input_col:
        custom_symbol = st.text_input(
            "股票代碼",
            value="2412",
            help="台股可輸入 2330、2412、2454，系統會自動補 .TW",
        )

    if custom_symbol:
        render_stock_block(
            block_title=f"查詢結果：{normalize_tw_symbol(custom_symbol)}",
            symbol=custom_symbol,
            key_prefix="custom",
        )

with st.expander("使用提醒"):
    st.markdown(
        """
- **市值排行前五**：2330、2308、2454、2317、3711。
- **股價排行前五**：5274、6515、7796、6223、6669。
- **AI 測試四大天王 / 石英元件 / 液冷散熱 / Starlink／低軌衛星**：概念股監控清單，中文名稱旁的 i 可查看個股註解。
- **自選股監測**：輸入股票代碼查詢個股估值。
- **TTM EPS 模式**：目前 PE = 目前股價 ÷ TTM EPS。
- **Forward EPS 模式**：預估股價 = 目前 PE × Forward EPS。
- **歷史 PE**：優先用歷史季度 EPS 建立 TTM EPS，再計算每日 PE。
- 若 yfinance 抓不到歷史 EPS，會退回「目前 TTM EPS 近似回推」。
- 合理 PE 預設使用近 3 年 PE 平均值。
- 本工具是估值輔助，不是買賣建議。
"""
    )
