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
def get_fred_data(api_key):
    pdr.pdr_override()
    tickers = {
        'cpi': 'CPIAUCSL',      # 美國 CPI 年增率等或指數
        'rate': 'GS10',         # 10年期公債殖利率
        'unemp': 'UNRATE',      # 美國失業率
        'fed': 'FEDFUNDS',      # 聯邦基金利率
        'dgs2': 'DGS2',         # 2年期公債殖利率
        'dgs10': 'DGS10'        # 10年期公債殖利率 (用於倒掛計算)
    }
    data = pd.DataFrame()
    for key, ticker in tickers.items():
        data[key] = pdr.DataReader(ticker, 'fred', start='2020-01-01', api_key=api_key)
    return data

try:
    df_fred = get_fred_data(fred_key)
    latest_cpi = df_fred['cpi'].dropna().iloc[-1]
    latest_rate = df_fred['rate'].dropna().iloc[-1]
    latest_unemp = df_fred['unemp'].dropna().iloc[-1]
    latest_fed = df_fred['fed'].dropna().iloc[-1]
except Exception as e:
    st.error(f"數據讀取失敗，請確認 FRED API Key 是否正確。錯誤訊息：{e}")
    st.stop()

# 建立分頁
tab1, tab2, tab3 = st.tabs(["🇺🇸 美國總體經濟指標", "🥇 黃金與全球市場", "📉 美債殖利率倒掛警示"])

with tab1:
    st.subheader("🇺🇸 美國總體經濟指標概覽")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("美國 10年期公債殖利率", f"{latest_rate:.2f}%")
    col2.metric("美國失業率", f"{latest_unemp:.2f}%")
    col3.metric("聯邦基金利率", f"{latest_fed:.2f}%")
    
    st.markdown("---")
    st.subheader("📊 總經指標走勢圖")
    fig_cpi = px.line(df_fred['rate'], title="美國 10 年期公債殖利率走勢")
    st.plotly_chart(fig_cpi, use_container_width=True)

    # AI 月報專區
    st.markdown("### 🤖 AI 總體經濟月報")
    if st.button("產生 AI 總體經濟摘要"):
        if not gemini_key:
            st.error("請先設定 GEMINI_API_KEY 才能使用 AI 分析功能！")
        else:
            try:
                client = genai.Client(api_key=gemini_key)
                prompt = f"""
                你是一位專業的總經經濟分析師。請根據以下最新的美國總體經濟數據，撰寫一份約 200 字的繁體中文總體經濟短評：
                - 10年期美債殖利率：{latest_rate:.2f}%
                - 美國失業率：{latest_unemp:.2f}%
                - 聯邦基金利率：{latest_fed:.2f}%
                """
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                )
                st.success("分析完成！")
                st.write(response.text)
            except Exception as e:
                st.error(f"生成摘要時發生錯誤：{e}")

with tab2:
    st.subheader("🥇 黃金與市場資產走勢")
    st.markdown("追蹤全球避險資產黃金期貨 (`GC=F`) 近期走勢：")
    
    @st.cache_data
    def get_gold_data():
        gold = yf.download("GC=F", period="1y")
        return gold
    
    df_gold = get_gold_data()
    if not df_gold.empty:
        fig_gold = px.line(df_gold['Close'], title="黃金期貨近一年走勢 (Gold Futures)")
        st.plotly_chart(fig_gold, use_container_width=True)
    else:
        st.warning("無法載入黃金數據")

with tab3:
    st.subheader("📉 美債殖利率曲線倒掛警示 (10Y - 2Y Spread)")
    st.markdown("當 10 年期公債殖利率減去 2 年期公債殖利率小於 0 時，通常代表殖利率曲線倒掛，歷史上常被視為經濟衰退的前瞻指標。")
    
    df_spread = pd.DataFrame()
    df_spread['Spread'] = df_fred['dgs10'] - df_fred['dgs2']
    df_spread = df_spread.dropna()
    
    latest_spread = df_spread['Spread'].iloc[-1]
    
    if latest_spread < 0:
        st.error(f"⚠️ 目前 10Y-2Y 利差為 **{latest_spread:.2f}%**：已發生殖利率倒掛，需留意經濟衰退風險！")
    else:
        st.success(f"✅ 目前 10Y-2Y 利差為 **{latest_spread:.2f}%**：殖利率曲線正常，無倒掛現象。")
        
    fig_spread = px.line(df_spread['Spread'], title="美國 10 年期與 2 年期公債殖利率利差 (10Y - 2Y)")
    fig_spread.add_hline(y=0, line_dash="dash", line_color="red")
    st.plotly_chart(fig_spread, use_container_width=True)
