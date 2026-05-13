# -*- coding: utf-8 -*-
"""
stock.py

個股估值監控儀表板 stock.py

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

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(
    page_title="個股估值監控儀表板",
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

</style>
""",
    unsafe_allow_html=True,
)


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


def draw_pe_price_chart(stock: Dict, symbol: str):
    df = stock["hist_3y"]

    if df is None or df.empty or "PE" not in df.columns:
        st.info("目前無法產生近 3 年本益比與股價圖。")
        return

    fig = go.Figure()

    # 先畫股價，再畫 PE，避免股價線蓋住 PE 線
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            name="股價 TWD（右軸）",
            mode="lines",
            yaxis="y2",
            line=dict(color="#FF7A00", width=2.2),
            opacity=0.72,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["PE"],
            name="本益比 PE（左軸）",
            mode="lines",
            yaxis="y1",
            line=dict(color="#0057D9", width=3.0),
        )
    )

    fig.update_layout(
        title=f"{symbol} 近 3 年本益比（PE）與股價走勢",
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
            title=dict(text="本益比 PE", font=dict(color="#0057D9")),
            side="left",
            showgrid=True,
            tickfont=dict(color="#0057D9"),
        ),
        yaxis2=dict(
            title=dict(text="股價 TWD", font=dict(color="#FF7A00")),
            side="right",
            overlaying="y",
            showgrid=False,
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
        st.markdown(
            f"<div class='stock-title'>{symbol}｜{stock['name']}</div>",
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
        v4.metric("距合理價", f"{valuation['discount']:,.2f}%")

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

    draw_pe_price_chart(stock, symbol)

    st.markdown(
        "<div class='small-note'>說明：目前 PE = 目前股價 ÷ TTM EPS；Forward 推估股價 = 目前 PE × Forward EPS。若抓不到歷史 EPS，PE 圖會退回目前 TTM EPS 近似回推。</div>",
        unsafe_allow_html=True,
    )

    st.divider()



# =========================
# Main
# =========================

st.markdown("""
<div style="padding-top:8px;padding-bottom:2px;">
<h1 style="margin-bottom:0px;padding-bottom:0px;line-height:1.25;">
📈 個股估值監控儀表板
</h1>
</div>
""", unsafe_allow_html=True)

st.caption("Stock Valuation｜EPS × PE 合理股價監控")

page_mode = st.radio(
    "選擇監控頁面",
    [
        "市值排行前五",
        "股價排行前五",
        "自選股監測",
    ],
    horizontal=True,
    key="stock_page_mode",
)

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
    ("7769", "緯穎"),
    ("6223.TWO", "旺矽"),
    ("6669", "緯穎"),
]


def render_rank_page(title: str, stock_list: list[tuple[str, str]], key_prefix: str):
    st.markdown(f"## {title}")
    st.caption("點開個股區塊即可查看 EPS / PE 估值、Forward 推估股價與近 3 年 PE / 股價走勢。")

    for i, (symbol, name) in enumerate(stock_list, start=1):
        display_symbol = symbol.replace(".TWO", "").replace(".TW", "")
        with st.expander(f"{i}. {display_symbol}｜{name}", expanded=(i == 1)):
            render_stock_block(
                block_title=f"{i}. {display_symbol}｜{name}",
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

else:
    st.markdown("## 自選股監測")

    render_stock_block(
        block_title="固定監控 2330 台積電",
        symbol="2330",
        key_prefix="tsmc",
    )

    st.markdown("## 輸入股票代碼查詢")

    input_col, spacer = st.columns([0.25, 0.75])
    with input_col:
        custom_symbol = st.text_input(
            "股票代碼",
            value="2317",
            help="台股可輸入 2330、2317、2454，系統會自動補 .TW",
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
- **自選股監測**：保留原本的 2330 固定監控與自訂股票查詢。
- **TTM EPS 模式**：目前 PE = 目前股價 ÷ TTM EPS。
- **Forward EPS 模式**：預估股價 = 目前 PE × Forward EPS。
- **歷史 PE**：優先用歷史季度 EPS 建立 TTM EPS，再計算每日 PE。
- 若 yfinance 抓不到歷史 EPS，會退回「目前 TTM EPS 近似回推」。
- 合理 PE 預設使用近 3 年 PE 平均值。
- 本工具是估值輔助，不是買賣建議。
"""
    )
