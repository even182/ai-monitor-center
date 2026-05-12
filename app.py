import streamlit as st

st.set_page_config(
    page_title="YuHui AI Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("YuHui AI Dashboard")

st.markdown("## 功能列表")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
### 📊 全球市場總覽
Global Market

監控全球股市、VIX、美元、黃金、加密貨幣。
""")

    st.markdown("""
### 📈 台股估值分析
Stock Valuation

使用 EPS / PE 自動估算合理股價。
""")

with col2:
    st.markdown("""
### 🧺 ETF 分析
ETF Monitor

監控 ETF 持股、績效與資金流向。
""")

    st.markdown("""
### 🎯 選擇權戰情室
Options Center

分析法人籌碼、PCR、結算策略。
""")

st.divider()

st.caption("AI Monitor Center")