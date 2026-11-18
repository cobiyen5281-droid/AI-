import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from pandas_datareader import data as pdr
from google import genai

st.set_page_config(page_title="全球總體經濟與金融指標即時儀表板", page_icon="🌐", layout="wide")

st.title("🌐 全球總體經濟與金融指標即時儀表板")
st.markdown("結合總體經濟數據、金融市場與 AI 智慧分析的綜合儀表板")

# 側邊欄 API Key 輸入
st.sidebar.header("設定與金鑰")
if "FRED_API_KEY" in st.secrets:
    fred_key = st.secrets["FRED_API_KEY"]
    st.sidebar.success("已自動讀取 FRED API Key！")
else:
    fred_key = st.sidebar.text_input("請輸入您的 FRED API Key:", type="password")

if "GEMINI_API_KEY" in st.secrets:
    gemini_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_key = st.sidebar.text_input("請輸入您的 GEMINI API Key:", type="password")

if not fred_key:
    st.info("👈 請在左側輸入您的 FRED API Key 以開啟儀表板。")
    st.stop()

# 抓取 FRED 數據
@st.cache_data
def get_fred_data():
    tickers = {
        'cpi': 'CPIAUCSL',      # 美國 CPI 指數
        'rate': 'GS10',         # 10年期公債殖利率
        'unemp': 'UNRATE',      # 美國失業率
        'fed': 'FEDFUNDS',      # 聯邦基金利率
        'dgs2': 'DGS2',         # 2年期公債殖利率
        'dgs10': 'DGS10'        # 10年期公債殖利率 (用於倒掛計算)
    }
    data = pd.DataFrame()
    for key, ticker in tickers.items():
        data[key] = pdr.DataReader(ticker, 'fred', start='2020-01-01')
    return data

try:
    df_fred = get_fred_data()
    # 計算 CPI 年增率 (YoY %)
    df_fred['cpi_yoy'] = df_fred['cpi'].pct_change(periods=12) * 100
    
    latest_cpi_yoy = df_fred['cpi_yoy'].dropna().iloc[-1]
    latest_rate = df_fred['rate'].dropna().iloc[-1]
    latest_unemp = df_fred['unemp'].dropna().iloc[-1]
    latest_fed = df_fred['fed'].dropna().iloc[-1]
except Exception as e:
    st.error(f"數據讀取失敗，請稍後再試。錯誤訊息：{e}")
    st.stop()

# 建立多個專業分頁
tab1, tab2, tab3 = st.tabs([
    "🇺🇸 美國總體經濟指標", 
    "🥇 黃金與全球市場", 
    "📉 美債殖利率倒掛警示"
])

with tab1:
    st.subheader("🇺🇸 美國總體經濟指標概覽")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("美國 CPI 年增率", f"{latest_cpi_yoy:.2f}%")
    col2.metric("10年期公債殖利率", f"{latest_rate:.2f}%")
    col3.metric("美國失業率", f"{latest_unemp:.2f}%")
    col4.metric("聯邦基金利率", f"{latest_fed:.2f}%")
    
    st.markdown("---")
    st.subheader("📊 總經指標歷史走勢圖")
    
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig_cpi = px.line(df_fred['cpi_yoy'].dropna(), title="美國 CPI 年增率走勢 (%)")
        st.plotly_chart(fig_cpi, use_container_width=True)
    with chart_col2:
        fig_unemp = px.line(df_fred['unemp'].dropna(), title="美國失業率走勢 (%)")
        st.plotly_chart(fig_unemp, use_container_width=True)

    # AI 月報專區
    st.markdown("---")
    st.markdown("### 🤖 AI 總體經濟月報")
    if st.button("產生 AI 總體經濟摘要"):
        if not gemini_key:
            st.error("請先設定 GEMINI_API_KEY 才能使用 AI 分析功能！")
        else:
            import time
            with st.spinner("正在呼叫 AI 分析最新總經數據，若遇伺服器忙碌將自動重試..."):
                prompt = f"""
                你是一位專業的總體經濟分析師。請根據以下最新的美國總體經濟數據，撰寫一份約 200 字的繁體中文總體經濟短評，分析目前的通膨、就業與利率環境：
                - 美國 CPI 年增率：{latest_cpi_yoy:.2f}%
                - 10年期美債殖利率：{latest_rate:.2f}%
                - 美國失業率：{latest_unemp:.2f}%
                - 聯邦基金利率：{latest_fed:.2f}%
                """
                
                success = False
                response = None
                last_error = None
                
                # 自動重試 3 次，每次間隔 2 秒
                for attempt in range(3):
                    try:
                        client = genai.Client(api_key=gemini_key)
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=prompt,
                        )
                        success = True
                        break
                    except Exception as e:
                        last_error = e
                        if "503" in str(e) and attempt < 2:
                            time.sleep(2)  # 稍微等待 2 秒後自動重試
                            continue
                        else:
                            break
                
                if success:
                    st.success("分析完成！")
                    st.write(response.text)
                else:
                    st.error(f"伺服器目前流量過大 (503)，自動重試後仍無法連線，請稍後再點擊一次按鈕。詳細錯誤：{last_error}")

with tab2:
    st.subheader("🥇 黃金與全球避險資產走勢")
    st.markdown("追蹤全球避險資產黃金期貨 (`GC=F`) 近一年走勢：")
    
    @st.cache_data
    def get_gold_data():
        gold = yf.download("GC=F", period="1y")
        # 處理新版 yfinance 多層欄位索引問題
        if isinstance(gold.columns, pd.MultiIndex):
            gold.columns = gold.columns.get_level_values(0)
        return gold
    
    df_gold = get_gold_data()
    if not df_gold.empty and 'Close' in df_gold.columns:
        latest_gold = df_gold['Close'].iloc[-1]
        st.metric("最新黃金期貨價格 (USD)", f"${latest_gold:,.2f}")
        fig_gold = px.line(df_gold['Close'], title="黃金期貨近一年走勢 (Gold Futures)")
        st.plotly_chart(fig_gold, use_container_width=True)
    else:
        st.warning("暫時無法載入黃金數據，請稍後重新整理。")

with tab3:
    st.subheader("📉 美債殖利率曲線倒掛警示 (10Y - 2Y Spread)")
    st.markdown("當 **10 年期公債殖利率** 減去 **2 年期公債殖利率** 小於 0 時，代表殖利率曲線倒掛，歷史上常被視為經濟衰退的前瞻預警指標。")
    
    df_spread = pd.DataFrame()
    df_spread['Spread'] = df_fred['dgs10'] - df_fred['dgs2']
    df_spread = df_spread.dropna()
    
    latest_spread = df_spread['Spread'].iloc[-1]
    
    if latest_spread < 0:
        st.error(f"⚠️ 目前 10Y-2Y 利差為 **{latest_spread:.2f}%**：已發生殖利率倒掛，需留意潛在經濟衰退風險！")
    else:
        st.success(f"✅ 目前 10Y-2Y 利差為 **{latest_spread:.2f}%**：殖利率曲線維持正斜率，目前無倒掛現象。")
        
    fig_spread = px.line(df_spread['Spread'], title="美國 10 年期與 2 年期公債殖利率利差 (10Y - 2Y %)")
    fig_spread.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="倒掛警戒線 (0%)")
    st.plotly_chart(fig_spread, use_container_width=True)
