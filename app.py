import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# 1. 頁面基本配置
st.set_page_config(
    page_title="個人資產儀表板 (雲端工作站)",
    layout="wide",
    page_icon="💼"
)

# 2. ⚡ 雲端自動刷新
st_autorefresh(interval=15000, key="realtime_data_refresher")

WEEK_MAP = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}

# ==========================================
# 3. 雲端 Google 試算表連線設定
# ==========================================
@st.cache_resource(ttl=600)
def get_gspread_client():
    try:
        creds_dict = dict(st.secrets["gcp_json"])
        creds = Credentials.from_service_account_info(
            creds_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google 金鑰讀取失敗，請檢查 Secrets 設定: {e}")
        return None

SPREADSHEET_NAME = "個人資產" 

def load_sheet_data():
    client = get_gspread_client()
    if not client:
        return None, None
    try:
        sh = client.open(SPREADSHEET_NAME)
        
        def parse_num(v):
            try: 
                return float(str(v).replace('NT$', '').replace('$', '').replace(',', '').replace('%', '').strip())
            except: 
                return 0.0

        # 1. 直接從「資產總覽」讀取正確的持股與成本數據
        ws_summary = sh.worksheet("資產總覽")
        s_rows = ws_summary.get_all_values()
        
        holdings = []
        total_assets = 0.0
        total_cost = 0.0
        total_profit = 0.0
        
        if len(s_rows) > 1:
            price_map = {}
            change_map = {}
            # 從 H~J 欄讀取收盤價與漲跌幅
            for sr in s_rows[1:]:
                if len(sr) >= 10 and sr[7]:
                    stock_key = sr[7].strip()
                    price_map[stock_key] = parse_num(sr[8])  # I欄: 即時收盤價
                    raw_chg = str(sr[9]).replace('%', '').strip()
                    change_map[stock_key] = parse_num(raw_chg) # J欄: 即時漲跌幅

            # 讀取左側 A~F 欄的持股明細
            for sr in s_rows[1:]:
                if len(sr) >= 6 and sr[0]:
                    name = sr[0].strip() # A欄: 股票名稱
                    shares = parse_num(sr[1])     # B欄: 總股數
                    cost = parse_num(sr[2])       # C欄: 總成本
                    avg_cost = parse_num(sr[3])   # D欄: 平均成本
                    profit = parse_num(sr[4])     # E欄: 即時總損益
                    m_val = parse_num(sr[5])      # F欄: 即時市值
                    
                    if cost > 0 or m_val > 0:
                        total_cost += cost
                        total_assets += m_val
                        total_profit += profit
                        
                        curr_price = 0.0
                        chg_pct = 0.0
                        
                        # 完美比對名稱 (支援 0050 與元大台灣50)
                        for k, p in price_map.items():
                            if ("0050" in name and "0050" in k) or ("台積電" in name and "台積電" in k) or (name in k or k in name):
                                curr_price = p
                                chg_pct = change_map.get(k, 0.0)
                                break
                        
                        if curr_price == 0.0 and shares > 0:
                            curr_price = m_val / shares

                        holdings.append({
                            "stock_name": name,
                            "shares": shares,
                            "avg_cost": avg_cost,
                            "total_cost": cost,
                            "current_price": curr_price,
                            "market_value": m_val,
                            "各股損益": profit,
                            "change_pct": chg_pct
                        })

        profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0

        # 2. 讀取「每日損益追蹤」取得歷史走勢圖數據
        ws_overview = sh.worksheet("每日損益追蹤")
        rows = ws_overview.get_all_values()
        hist_data = []
        if len(rows) > 1:
            for r in rows[1:]:
                if len(r) >= 14:
                    hist_data.append({
                        "日期": r[0], "總累積成本": parse_num(r[5]), "總市值": parse_num(r[6]), 
                        "總投資損益": parse_num(r[7]), "0050每日損益": parse_num(r[12]),
                        "台積電每日損益": parse_num(r[13])
                    })
        
        return {
            "total_assets": total_assets, "total_cost": total_cost, 
            "total_profit": total_profit, "profit_rate": profit_rate, "holdings": holdings
        }, hist_data
    except Exception as e:
        st.info(f"讀取試算表發生錯誤: {e}")
        return None, None

def load_bank_data():
    client = get_gspread_client()
    if not client:
        return 58661.0, []
    try:
        sh = client.open(SPREADSHEET_NAME)
        try:
            ws_summary = sh.worksheet("資產總覽")
            s_rows = ws_summary.get_all_values()
            if len(s_rows) > 1 and len(s_rows[1]) >= 12:
                b_val = float(str(s_rows[1][11]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 58661)
            else:
                b_val = 58661.0
        except:
            b_val = 58661.0

        ws_bank = sh.worksheet("db_bank_ledger")
        b_rows = ws_bank.get_all_values()
        txs = []
        if len(b_rows) > 1:
            for r in b_rows[1:]:
                if len(r) >= 4:
                    try:
                        amt = float(str(r[2]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 0)
                    except:
                        amt = 0.0
                    txs.append({"日期": r[0], "類型": r[1], "金額": amt, "備註": r[3]})
        
        return b_val, txs
    except Exception as e:
        return 58661.0, []

# --- 🌈 視覺優化版卡片 ---
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
            bg_gradient, glow_color = "linear-gradient(135deg, #FF8008 0%, #FFC837 100%)", "rgba(200, 128, 8, 0.6)"
            title_color, val_color = "#78350f", "#80caf0"
            text_shadow, title_shadow = "0 2px 4px rgba(0,0,0,0.3)", "0 1px 3px rgba(0,0,0,0.3)"

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

bank_balance, txs = load_bank_data()
dashboard_data, hist_data = load_sheet_data()

tab1, tab2, tab3 = st.tabs(["📊 即時資產現況", "📈 歷史損益與市值走勢", "🏦 銀行帳戶明細"])

# ==========================================
# 分頁 1：即時資產現況
# ==========================================
with tab1:
    if dashboard_data:
        total_assets = dashboard_data.get("total_assets", 0.0)
        total_cost = dashboard_data.get("total_cost", 0.0)
        total_profit = dashboard_data.get("total_profit", 0.0)
        profit_rate = dashboard_data.get("profit_rate", 0.0)
        holdings = dashboard_data.get("holdings", [])

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.markdown(create_colorful_card("總市值", f"NT$ {total_assets:,.0f}", icon="💎", theme="purple"), unsafe_allow_html=True)
        with c2: st.markdown(create_colorful_card("總成本", f"NT$ {total_cost:,.0f}", icon="📥", theme="blue"), unsafe_allow_html=True)
        with c3: st.markdown(create_colorful_card("帳戶餘額", f"NT$ {bank_balance:,.0f}", icon="🏦", theme="gold"), unsafe_allow_html=True)
        
        profit_icon = "🔥" if total_profit > 0 else ("💧" if total_profit < 0 else "⚖️")
        with c4: st.markdown(create_colorful_card("即時總損益", f"{total_profit:+,.0f}", icon=profit_icon, is_profit=True, num_val=total_profit), unsafe_allow_html=True)
        with c5: st.markdown(create_colorful_card("總損益 (%)", f"{profit_rate:+.2f}%", icon="📈", is_profit=True, num_val=profit_rate), unsafe_allow_html=True)

        st.write("") 
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            fig_pie = px.pie(
                names=['股票總市值', '銀行帳戶餘額'], values=[total_assets, bank_balance],
                title="📊 總資產配置比例", hole=0.45, color_discrete_sequence=['#4B8BBE', '#FFE873']
            )
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            if holdings:
                df_h = pd.DataFrame(holdings)
                fig_bar = px.bar(
                    df_h, x="stock_name", y="market_value", title="📊 各持股市值佔比",
                    text_auto='.2s', color="stock_name", labels={"stock_name": "股票名稱", "market_value": "市值"}
                )
                fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.subheader("📋 持股即時明細")
        if holdings:
            df_holdings = pd.DataFrame(holdings)
            df_holdings["各股損益(%)"] = df_holdings.apply(lambda x: (x["各股損益"] / x["total_cost"] * 100) if x["total_cost"] > 0 else 0.0, axis=1)
            
            df_holdings = df_holdings.rename(columns={
                "stock_name": "股票名稱", "shares": "總股數", "avg_cost": "平均成本", "total_cost": "總成本",
                "current_price": "即時現價", "market_value": "即時市值", "change_pct": "即時漲跌幅(%)"
            })
            
            display_cols = ["股票名稱", "總股數", "平均成本", "總成本", "即時現價", "即時市值", "各股損益", "即時漲跌幅(%)", "各股損益(%)"]
            df_display = df_holdings[display_cols].copy()

            def color_tw_market(row):
                styles = [''] * len(row)
                for i, col in enumerate(row.index):
                    val = row[col]
                    if col in ["各股損益", "各股損益(%)", "即時漲跌幅(%)"]:
                        if pd.notna(val) and isinstance(val, (int, float)):
                            if val > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                            elif val < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
                return styles

            format_dict = {
                "總股數": "{:,.0f}", "平均成本": "{:,.2f}", "總成本": "{:,.0f}",
                "即時現價": "{:,.2f}", "即時市值": "{:,.0f}", "各股損益": "{:+,.0f}",
                "即時漲跌幅(%)": "{:+.2f}%", "各股損益(%)": "{:+.2f}%"
            }
            styled_df = df_display.style.apply(color_tw_market, axis=1).format(format_dict)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("目前試算表中尚無資料。")

# ==========================================
# 分頁 2：歷史損益與市值走勢
# ==========================================
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
        
        def color_history(row):
            styles = [''] * len(row)
            for i, col in enumerate(row.index):
                val = row[col]
                if col in ["總投資損益", "0050每日損益", "台積電每日損益"]:
                    if pd.notna(val) and isinstance(val, (int, float)):
                        if val > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                        elif val < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
            return styles

        format_hist_dict = {
            "總累積成本": "{:,.0f}", "總市值": "{:,.0f}", "總投資損益": "{:+,.0f}",
            "0050每日損益": "{:+,.0f}", "台積電每日損益": "{:+,.0f}"
        }
        styled_hist = df_hist_display.style.apply(color_history, axis=1).format(format_hist_dict, na_rep="")
        st.dataframe(styled_hist, use_container_width=True, hide_index=True)
    else:
        st.info("目前暫無每日歷史結算記錄。")

# ==========================================
# 分頁 3：銀行帳戶明細與記帳表單
# ==========================================
with tab3:
    st.subheader("🏦 銀行帳戶資金流水")
    st.markdown(create_colorful_card("銀行帳戶活存總結餘", f"NT$ {bank_balance:,.0f}", icon="💰", theme="gold"), unsafe_allow_html=True)
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
                    try:
                        client = get_gspread_client()
                        sh = client.open(SPREADSHEET_NAME)
                        ws_bank = sh.worksheet("db_bank_ledger")
                        ws_bank.append_row([str(rec_date), rec_type, f"{amount:,.0f}", note])
                        st.success("紀錄成功寫入 Google 試算表！畫面將自動更新。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"寫入失敗: {e}")
                else:
                    st.warning("請輸入有效的金額。")

    with col_list:
        st.markdown("#### 📋 帳戶流水明細")
        if txs:
            df_bank = pd.DataFrame(txs)
            
            def color_bank(row):
                styles = [''] * len(row)
                for i, col in enumerate(row.index):
                    if col == "金額":
                        val = row[col]
                        if pd.notna(val) and isinstance(val, (int, float)):
                            if val > 0: styles[i] = 'color: #ff4b4b; font-weight: bold;'
                            elif val < 0: styles[i] = 'color: #09ab3b; font-weight: bold;'
                return styles

            styled_bank = pd.DataFrame(txs).style.apply(color_bank, axis=1).format({"金額": "{:+,.0f}"})
            st.dataframe(styled_bank, use_container_width=True, hide_index=True)
        else:
            st.info("尚無銀行紀錄。")
