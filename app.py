import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
import json
import requests
from datetime import datetime

# ==========================================
# 1. 頁面基本配置與自動刷新
# ==========================================
st.set_page_config(page_title="個人資產儀表板 (雲端版)", layout="wide", page_icon="💼")
st_autorefresh(interval=15000, key="realtime_data_refresher") # 雲端建議每15秒刷新一次即可，避免資源耗盡

WEEK_MAP = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}

# ==========================================
# 2. 雲端連線 Google 試算表 (使用 Secrets)
# ==========================================
@st.cache_resource(ttl=600)
def get_gspread_client():
    try:
        creds_dict = json.loads(st.secrets["gcp_json"])
        creds = Credentials.from_service_account_info(
            creds_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google 金鑰讀取失敗，請檢查 Secrets 設定: {e}")
        return None

# ==========================================
# 3. UI 卡片設計 (保持您最愛的炫彩置中版)
# ==========================================
def create_colorful_card(title, value_str, icon="", theme="blue", is_profit=False, num_val=None):
    if is_profit and num_val is not None:
        bg_gradient = "linear-gradient(135deg, #1e2128 0%, #13151a 100%)"
        title_color = "#a0a5b1"
        if num_val > 0:
            val_color, glow_color = "#ff4b4b", "rgba(255, 75, 75, 0.6)"
            text_shadow, title_shadow = "0 0 10px rgba(255, 75, 75, 0.4)", "0 1px 3px rgba(0,0,0,0.3)"
        elif num_val < 0:
            val_color, glow_color = "#00e676", "rgba(0, 230, 118, 0.6)"
            text_shadow, title_shadow = "0 0 10px rgba(0, 230, 118, 0.4)", "0 1px 3px rgba(0,0,0,0.3)"
        else:
            val_color, glow_color = "#ffffff", "rgba(255, 255, 255, 0.2)"
            text_shadow, title_shadow = "none", "none"
    else:
        if theme == "purple":
            bg_gradient, glow_color = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "rgba(118, 75, 162, 0.6)"
            title_color, val_color = "#e0c3fc", "#fef08a"
            text_shadow, title_shadow = "0 2px 4px rgba(0,0,0,0.3)", "0 1px 3px rgba(0,0,0,0.3)"
        elif theme == "blue":
            bg_gradient, glow_color = "linear-gradient(135deg, #2b5876 0%, #4e4376 100%)", "rgba(78, 67, 118, 0.6)"
            title_color, val_color = "#bae6fd", "#a7f3d0"
            text_shadow, title_shadow = "0 2px 4px rgba(0,0,0,0.3)", "0 1px 3px rgba(0,0,0,0.3)"
        elif theme == "gold":
            bg_gradient, glow_color = "linear-gradient(135deg, #FF8008 0%, #FFC837 100%)", "rgba(255, 128, 8, 0.6)"
            title_color, val_color = "#78350f", "#0f172a"
            text_shadow, title_shadow = "none", "none"

    html = f"""
    <div style="
        background: {bg_gradient}; border-radius: 16px; padding: 20px 10px;
        box-shadow: 0 8px 20px {glow_color}; height: 140px; display: flex;
        flex-direction: column; justify-content: center; align-items: center; text-align: center;
        position: relative; overflow: hidden; margin-bottom: 15px;
    ">
        <div style="position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center;">
            <p style="margin: 0; font-size: 1.05rem; color: {title_color}; font-weight: 600; text-shadow: {title_shadow};">{title}</p>
            <p style="margin: 8px 0 0 0; font-size: 1.7rem; font-weight: 800; letter-spacing: 0.5px; color: {val_color}; text-shadow: {text_shadow}; white-space: nowrap;">{value_str}</p>
        </div>
        <div style="position: absolute; right: 0px; bottom: -15px; font-size: 5rem; opacity: 0.12; z-index: 0; transform: rotate(-15deg); pointer-events: none; color: {val_color};">
            {icon}
        </div>
    </div>
    """
    return html

st.title("💼 個人資產儀表板 (雲端工作站) ☁️")

# ==========================================
# 4. 讀取資料
# ==========================================
client = get_gspread_client()
db_name = "db_daily_stock_prices"  # 您的試算表名稱

def parse_num(val):
    if not val: return 0.0
    try: return float(str(val).replace('NT$', '').replace('$', '').replace(',', '').replace('%', '').strip())
    except: return 0.0

total_assets, total_cost, total_profit, profit_rate = 0.0, 0.0, 0.0, 0.0
bank_balance = 58661  # 預設銀行餘額，可由試算表讀取覆蓋
hist_data = []

if client:
    try:
        sh = client.open(db_name)
        sheet = sh.worksheet("每日損益追蹤")
        rows = sheet.get_all_values()
        
        if len(rows) > 1:
            headers = rows[0]
            last_row = rows[-1]
            total_cost = parse_num(last_row[5])       # 總累積成本
            total_assets = parse_num(last_row[6])     # 總市值
            total_profit = parse_num(last_row[7])     # 總投資損益
            profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0
            
            # 建立歷史紀錄
            for r in rows[1:]:
                if len(r) >= 10:
                    hist_data.append({
                        "日期": r[0], "總累積成本": parse_num(r[5]), "總市值": parse_num(r[6]), 
                        "總投資損益": parse_num(r[7]), "0050每日損益": parse_num(r[12]) if len(r)>12 else 0,
                        "台積電每日損益": parse_num(r[13]) if len(r)>13 else 0
                    })
    except Exception as e:
        st.warning("讀取試算表資料時發生問題，請確認表格名稱。")

# ==========================================
# 5. 渲染分頁
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 即時資產現況", "📈 歷史損益與市值走勢", "🏦 銀行帳戶明細"])

with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(create_colorful_card("總市值", f"NT$ {total_assets:,.0f}", icon="💎", theme="purple"), unsafe_allow_html=True)
    with c2: st.markdown(create_colorful_card("總成本", f"NT$ {total_cost:,.0f}", icon="📥", theme="blue"), unsafe_allow_html=True)
    with c3: st.markdown(create_colorful_card("帳戶餘額", f"NT$ {bank_balance:,.0f}", icon="🏦", theme="gold"), unsafe_allow_html=True)
    profit_icon = "🔥" if total_profit > 0 else ("💧" if total_profit < 0 else "⚖️")
    with c4: st.markdown(create_colorful_card("即時總損益", f"{total_profit:+,.0f}", icon=profit_icon, is_profit=True, num_val=total_profit), unsafe_allow_html=True)
    with c5: st.markdown(create_colorful_card("總損益 (%)", f"{profit_rate:+.2f}%", icon="📈", is_profit=True, num_val=profit_rate), unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_pie = px.pie(
            names=['股票總市值', '銀行帳戶餘額'], values=[total_assets, bank_balance],
            title="📊 總資產配置比例", hole=0.45, color_discrete_sequence=['#4B8BBE', '#FFE873']
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_chart2:
        # 簡易持股比例圓餅圖取代條形圖，方便雲端顯示
        fig_pie2 = px.pie(
            names=['元大台灣0050', '台積電'], values=[190000, 120000], # 示意數值，可串接試算表
            title="📊 各持股市值佔比", hole=0.45, color_discrete_sequence=['#0068c9', '#83c9ff']
        )
        fig_pie2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie2, use_container_width=True)

with tab2:
    st.subheader("📈 歷史市值與累積損益走勢")
    if hist_data:
        df_hist = pd.DataFrame(hist_data)
        df_hist["真實日期"] = pd.to_datetime(df_hist["日期"])
        df_hist["星期"] = df_hist["真實日期"].dt.weekday.map(WEEK_MAP)
        df_hist["日期"] = df_hist["真實日期"].dt.strftime('%Y-%m-%d') + " (" + df_hist["星期"] + ")"
        df_hist = df_hist.sort_values("真實日期")
        
        fig_line = px.line(df_hist, x="真實日期", y=["總市值", "總累積成本"], title="📈 總市值與投資成本走勢", markers=True)
        fig_line.update_layout(xaxis_title="日期", yaxis_title="金額", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_line, use_container_width=True)

        st.divider()
        st.subheader("📜 歷史結算數據列表")
        df_hist_display = df_hist.drop(columns=["真實日期", "星期"]).copy()[::-1]
        st.dataframe(df_hist_display, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("🏦 銀行帳戶資金流水")
    st.markdown(create_colorful_card("銀行帳戶活存總結餘", f"NT$ {bank_balance:,.0f}", icon="💰", theme="gold"), unsafe_allow_html=True)
    st.info("雲端版本已部署成功！銀行流水與記帳功能可透過直接編輯 Google 試算表來同步。")
