import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# 1. 頁面基本配置
st.set_page_config(
    page_title="個人資產儀表板 (桌面工作站)",
    layout="wide",
    page_icon="💼"
)

# 2. ⚡ 每 1.5 秒無感極速刷新
st_autorefresh(interval=1500, key="realtime_data_refresher")

API_BASE_URL = "http://127.0.0.1:8000"

WEEK_MAP = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}

# --- 🌈 視覺優化版卡片：全面置中 + 獨立文字配色 ---
def create_colorful_card(title, value_str, icon="", theme="blue", is_profit=False, num_val=None):
    if is_profit and num_val is not None:
        # 【損益卡片】深色背景 + 鮮豔紅綠字 + 紅綠外發光
        bg_gradient = "linear-gradient(135deg, #1e2128 0%, #13151a 100%)"
        title_color = "#a0a5b1"
        if num_val > 0:
            val_color = "#ff4b4b"  # 霓虹紅
            glow_color = "rgba(255, 75, 75, 0.6)"
            text_shadow = "0 0 10px rgba(255, 75, 75, 0.4)"
            title_shadow = "0 1px 3px rgba(0,0,0,0.3)"
        elif num_val < 0:
            val_color = "#00e676"  # 霓虹綠
            glow_color = "rgba(0, 230, 118, 0.6)"
            text_shadow = "0 0 10px rgba(0, 230, 118, 0.4)"
            title_shadow = "0 1px 3px rgba(0,0,0,0.3)"
        else:
            val_color = "#ffffff"
            glow_color = "rgba(255, 255, 255, 0.2)"
            text_shadow = "none"
            title_shadow = "none"
    else:
        # 【資產卡片】各主題專屬文字顏色搭配
        if theme == "purple":
            bg_gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            glow_color = "rgba(118, 75, 162, 0.6)"
            title_color = "#e0c3fc"       # 淺紫色標題
            val_color = "#fef08a"         # 亮黃色數值
            text_shadow = "0 2px 4px rgba(0,0,0,0.3)"
            title_shadow = "0 1px 3px rgba(0,0,0,0.3)"
        elif theme == "blue":
            bg_gradient = "linear-gradient(135deg, #2b5876 0%, #4e4376 100%)"
            glow_color = "rgba(78, 67, 118, 0.6)"
            title_color = "#bae6fd"       # 淺藍色標題
            val_color = "#a7f3d0"         # 薄荷綠數值
            text_shadow = "0 2px 4px rgba(0,0,0,0.3)"
            title_shadow = "0 1px 3px rgba(0,0,0,0.3)"
        elif theme == "gold":
            bg_gradient = "linear-gradient(135deg, #FF8008 0%, #FFC837 100%)"
            glow_color = "rgba(200, 128, 8, 0.6)"
            title_color = "#78350f"       # 深棕色標題 (因背景亮，改深色字)
            val_color = "#80caf0"         # 深鐵灰數值
            text_shadow = "0 2px 4px rgba(0,0,0,0.3)"          # 深色字不需要陰影
            title_shadow = "0 1px 3px rgba(0,0,0,0.3)"

    # 新增 align-items: center 與 text-align: center 讓內容完美置中
    html = f"""
    <div style="
        background: {bg_gradient};
        border-radius: 16px;
        padding: 20px 10px;
        box-shadow: 0 8px 20px {glow_color};
        height: 140px; 
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        position: relative;
        overflow: hidden;
        margin-bottom: 15px;
    ">
        <div style="position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center;">
            <p style="margin: 0; font-size: 1.05rem; color: {title_color}; font-weight: 600; text-shadow: {title_shadow};">{title}</p>
            <p style="margin: 8px 0 0 0; font-size: 1.7rem; font-weight: 800; letter-spacing: 0.5px; color: {val_color}; text-shadow: {text_shadow}; white-space: nowrap;">{value_str}</p>
        </div>
        <!-- 半透明浮水印 Icon (調整位置不擋字) -->
        <div style="
            position: absolute; 
            right: 0px; 
            bottom: -15px; 
            font-size: 5rem; 
            opacity: 0.12; 
            z-index: 0; 
            transform: rotate(-15deg);
            pointer-events: none;
            color: {val_color};
        ">
            {icon}
        </div>
    </div>
    """
    return html

st.title("💼 個人資產儀表板 (桌面工作站)")

# 預先抓取銀行餘額
bank_balance = 0.0
try:
    b_res = requests.get(f"{API_BASE_URL}/api/bank/summary", timeout=2)
    if b_res.status_code == 200:
        bank_balance = b_res.json().get("balance", 0.0)
except:
    pass

tab1, tab2, tab3 = st.tabs(["📊 即時資產現況", "📈 歷史損益與市值走勢", "🏦 銀行帳戶明細"])

# ==========================================
# 分頁 1：即時資產現況
# ==========================================
with tab1:
    try:
        res = requests.get(f"{API_BASE_URL}/api/dashboard/overview", timeout=5)
        if res.status_code == 200:
            data = res.json()
            total_assets = data.get("total_assets", 0.0)
            total_cost = data.get("total_cost", 0.0)
            total_profit = data.get("total_profit", 0.0)
            profit_rate = data.get("profit_rate", 0.0)
            holdings = data.get("holdings", [])

            # --- 頂部 5 大卡片 ---
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(create_colorful_card("總市值", f"NT$ {total_assets:,.0f}", icon="💎", theme="purple"), unsafe_allow_html=True)
            with c2: st.markdown(create_colorful_card("總成本", f"NT$ {total_cost:,.0f}", icon="📥", theme="blue"), unsafe_allow_html=True)
            with c3: st.markdown(create_colorful_card("帳戶餘額", f"NT$ {bank_balance:,.0f}", icon="🏦", theme="gold"), unsafe_allow_html=True)
            
            profit_icon = "🔥" if total_profit > 0 else ("💧" if total_profit < 0 else "⚖️")
            with c4: st.markdown(create_colorful_card("即時總損益", f"{total_profit:+,.0f}", icon=profit_icon, is_profit=True, num_val=total_profit), unsafe_allow_html=True)
            with c5: st.markdown(create_colorful_card("總損益 (%)", f"{profit_rate:+.2f}%", icon="📈", is_profit=True, num_val=profit_rate), unsafe_allow_html=True)

            st.write("") 
            
            # --- 圖表區 ---
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                fig_pie = px.pie(
                    names=['股票總市值', '銀行帳戶餘額'], 
                    values=[total_assets, bank_balance],
                    title="📊 總資產配置比例",
                    hole=0.45,
                    color_discrete_sequence=['#4B8BBE', '#FFE873']
                )
                fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col_chart2:
                if holdings:
                    df_h = pd.DataFrame(holdings)
                    fig_bar = px.bar(
                        df_h, x="stock_name", y="market_value", 
                        title="📊 各持股市值佔比",
                        text_auto='.2s', color="stock_name",
                        labels={"stock_name": "股票名稱", "market_value": "市值"}
                    )
                    fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()
            st.subheader("📋 持股即時明細")

            if holdings:
                df_holdings = pd.DataFrame(holdings)
                df_holdings["總損益(%)"] = df_holdings.apply(
                    lambda x: (x["realtime_profit"] / x["total_cost"] * 100) if x["total_cost"] > 0 else 0.0, axis=1
                )

                df_holdings = df_holdings.rename(columns={
                    "stock_name": "股票名稱",
                    "shares": "總股數",
                    "avg_cost": "平均成本",
                    "total_cost": "總成本",
                    "current_price": "即時現價",
                    "market_value": "即時市值",
                    "realtime_profit": "即時總損益",
                    "change_pct": "即時漲跌幅(%)"
                })

                display_cols = ["股票名稱", "總股數", "平均成本", "總成本", "即時現價", "即時市值", "即時總損益", "總損益(%)", "即時漲跌幅(%)"]
                df_display = df_holdings[display_cols].copy()

                def color_tw_market(row):
                    styles = [''] * len(row)
                    for i, col in enumerate(row.index):
                        val = row[col]
                        if col in ["即時總損益", "總損益(%)", "即時漲跌幅(%)"]:
                            if pd.notna(val):
                                if val > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                                elif val < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
                        if col == "即時現價":
                            pct = row["即時漲跌幅(%)"]
                            if pd.notna(pct):
                                if pct > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                                elif pct < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
                    return styles

                format_dict = {
                    "總股數": "{:,.0f}",
                    "平均成本": "{:,.2f}",
                    "總成本": "{:,.0f}",
                    "即時現價": "{:,.2f}",
                    "即時市值": "{:,.0f}",
                    "即時總損益": "{:+,.0f}",
                    "總損益(%)": "{:+.2f}%",
                    "即時漲跌幅(%)": "{:+.2f}%"
                }

                styled_df = df_display.style.apply(color_tw_market, axis=1).format(format_dict)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                st.info("目前試算表中無持股資料。")
        else:
            st.warning("⚠️ 後端 API 回應異常，正在嘗試重新連線...")
    except Exception as e:
        st.error(f"連線至後端服務失敗: {e}")

# ==========================================
# 分頁 2：歷史損益與市值走勢
# ==========================================
with tab2:
    st.subheader("📈 歷史市值與累積損益走勢")
    try:
        res = requests.get(f"{API_BASE_URL}/api/dashboard/history", timeout=10)
        if res.status_code == 200:
            hist_data = res.json().get("history", [])
            if hist_data:
                df_hist = pd.DataFrame(hist_data)
                
                df_hist["真實日期"] = pd.to_datetime(df_hist["日期"])
                df_hist["星期"] = df_hist["真實日期"].dt.weekday.map(WEEK_MAP)
                df_hist["日期"] = df_hist["真實日期"].dt.strftime('%Y-%m-%d') + " (" + df_hist["星期"] + ")"
                df_hist = df_hist.sort_values("真實日期")
                
                fig_line = px.line(
                    df_hist, x="真實日期", y=["總市值", "總累積成本"], 
                    title="📈 總市值與投資成本走勢", markers=True
                )
                fig_line.update_layout(xaxis_title="日期", yaxis_title="金額", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_line, use_container_width=True)

                df_hist["獲利狀態"] = df_hist["總投資損益"].apply(lambda x: "賺錢" if x > 0 else ("賠錢" if x < 0 else "持平"))
                fig_bar = px.bar(
                    df_hist, x="真實日期", y="總投資損益", 
                    title="📊 每日結算總損益",
                    color="獲利狀態",
                    color_discrete_map={"賺錢": "#ff4b4b", "賠錢": "#09ab3b", "持平": "gray"}
                )
                fig_bar.update_layout(xaxis_title="日期", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()
                st.subheader("📜 歷史結算數據列表")
                
                df_hist_display = df_hist.drop(columns=["獲利狀態", "真實日期", "星期"]).copy()
                df_hist_display = df_hist_display[::-1]

                def color_history(row):
                    styles = [''] * len(row)
                    for i, col in enumerate(row.index):
                        val = row[col]
                        if col in ["總投資損益", "0050每日損益", "台積電每日損益"]:
                            if pd.notna(val) and isinstance(val, (int, float)):
                                if val > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                                elif val < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
                        elif col == "與前天損益比較%":
                            if isinstance(val, str) and '%' in val:
                                try:
                                    num = float(val.replace('%', ''))
                                    if num > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                                    elif num < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
                                except: pass
                    return styles

                format_hist_dict = {
                    "總累積成本": "{:,.0f}",
                    "總市值": "{:,.0f}",
                    "總投資損益": "{:+,.0f}",
                    "0050每日損益": "{:+,.0f}",
                    "台積電每日損益": "{:+,.0f}"
                }

                styled_hist = df_hist_display.style.apply(color_history, axis=1).format(format_hist_dict, na_rep="")
                st.dataframe(styled_hist, use_container_width=True, hide_index=True)
            else:
                st.info("目前暫無每日歷史結算記錄。")
        else:
            st.warning("無法載入歷史損益記錄。")
    except Exception as e:
        st.error(f"讀取歷史走勢失敗: {e}")

# ==========================================
# 分頁 3：銀行帳戶明細
# ==========================================
with tab3:
    st.subheader("🏦 銀行帳戶資金流水")
    try:
        res = requests.get(f"{API_BASE_URL}/api/bank/summary", timeout=10)
        if res.status_code == 200:
            bank_data = res.json()
            balance = bank_data.get("balance", 0.0)
            txs = bank_data.get("transactions", [])

            # 套用與第一頁相同的卡片風格
            st.markdown(create_colorful_card("銀行帳戶活存總結餘", f"NT$ {balance:,.0f}", icon="💰", theme="gold"), unsafe_allow_html=True)
            st.divider()

            col_form, col_list = st.columns([1, 2])

            with col_form:
                st.markdown("#### ✍️ 記帳 / 資金異動")
                with st.form("bank_record_form"):
                    rec_date = st.date_input("日期")
                    rec_type = st.selectbox("異動類型", ["現金", "跨行轉", "轉帳投", "委代入", "證券款", "電匯", "交割扣款"])
                    amount = st.number_input("金額 (元) 【扣款請直接輸入負數】", value=0.0, step=100.0)
                    note = st.text_input("備註說明")
                    submitted = st.form_submit_button("寫入試算表")

                    if submitted:
                        if amount != 0:
                            payload = {
                                "date": str(rec_date),
                                "record_type": rec_type,
                                "amount": amount,
                                "note": note
                            }
                            post_res = requests.post(f"{API_BASE_URL}/api/bank/record", json=payload)
                            if post_res.status_code == 200:
                                st.success("紀錄成功寫入！稍後畫面將自動更新。")
                            else:
                                st.error("寫入失敗，請確認後端連線。")
                        else:
                            st.warning("請輸入有效的金額。")

            with col_list:
                st.markdown("#### 📋 帳戶流水明細")
                if txs:
                    df_bank = pd.DataFrame(txs)
                    
                    df_bank["真實日期"] = pd.to_datetime(df_bank["日期"])
                    df_bank["星期"] = df_bank["真實日期"].dt.weekday.map(WEEK_MAP)
                    df_bank["日期"] = df_bank["真實日期"].dt.strftime('%Y-%m-%d') + " (" + df_bank["星期"] + ")"
                    df_bank = df_bank.drop(columns=["真實日期", "星期"])

                    def color_bank(row):
                        styles = [''] * len(row)
                        for i, col in enumerate(row.index):
                            if col == "金額":
                                val = row[col]
                                if pd.notna(val) and isinstance(val, (int, float)):
                                    if val > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                                    elif val < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
                        return styles

                    styled_bank = df_bank.style.apply(color_bank, axis=1).format({"金額": "{:+,.0f}"})
                    st.dataframe(styled_bank, use_container_width=True, hide_index=True)
                else:
                    st.info("尚無銀行紀錄。")
        else:
            st.warning("無法讀取銀行資金明細。")
    except Exception as e:
        st.error(f"讀取銀行資料失敗: {e}")