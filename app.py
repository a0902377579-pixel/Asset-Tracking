import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ==========================================
# 1. 頁面基本配置與頂級美化 CSS
# ==========================================
st.set_page_config(
    page_title="個人旗艦資產工作站", 
    layout="wide", 
    page_icon="💎", 
    initial_sidebar_state="expanded"
)

st_autorefresh(interval=1200000, key="realtime_data_refresher")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* 強制 Tab 容器滿版並設定間距 */
    div[data-baseweb="tab-list"] { 
        display: flex !important;
        width: 100% !important;
        gap: 15px !important; 
        background-color: transparent !important;
        border-bottom: none !important;
    }
    
    /* 徹底隱藏選中時原生的醜陋底線 */
    div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {
        display: none !important;
        background-color: transparent !important;
    }
    
    /* 未選中的 Tab：完美 50px 膠囊狀 */
    button[data-baseweb="tab"] { 
        flex: 1 1 0 !important;
        background-color: #1e2128 !important; 
        border-radius: 50px !important;  
        padding: 12px 0px !important; 
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        margin: 0 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
    }
    
    /* 確保字體顏色與置中 */
    button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p {
        width: 100%;
        text-align: center;
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #a0a5b1 !important;
    }
    
    /* 被選中 (Active) 的 Tab：發光漸層 */
    button[data-baseweb="tab"][aria-selected="true"] { 
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%) !important; 
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 6px 15px rgba(52, 152, 219, 0.5) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p {
        color: white !important; 
        font-weight: bold !important; 
    }
    
    div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

WEEK_MAP = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
SPREADSHEET_NAME = "個人資產" 

# ==========================================
# 2. 核心資料讀取
# ==========================================
@st.cache_resource(ttl=600)
def get_gspread_client():
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_json"]), 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ 金鑰讀取失敗: {e}")
        return None

def load_sheet_data():
    client = get_gspread_client()
    if not client: return None, None
    try:
        sh = client.open(SPREADSHEET_NAME)
        def parse_num(v):
            if not v: return 0.0
            try: return float(str(v).replace('NT$', '').replace('$', '').replace(',', '').replace('%', '').strip())
            except: return 0.0

        s_rows = sh.worksheet("資產總覽").get_all_values()
        holdings, total_assets, total_cost, total_profit = [], 0.0, 0.0, 0.0
        
        if len(s_rows) > 1:
            price_map = {sr[7].strip(): parse_num(sr[8]) for sr in s_rows[1:] if len(sr) >= 10 and sr[7]}
            change_map = {sr[7].strip(): parse_num(str(sr[9]).replace('%', '')) for sr in s_rows[1:] if len(sr) >= 10 and sr[7]}
            
            for sr in s_rows[1:]:
                if len(sr) >= 6 and sr[0]:
                    name, shares, cost = sr[0].strip(), parse_num(sr[1]), parse_num(sr[2])
                    avg_cost, profit, m_val = parse_num(sr[3]), parse_num(sr[4]), parse_num(sr[5])
                    
                    if cost > 0 or m_val > 0:
                        total_cost += cost; total_assets += m_val; total_profit += profit
                        curr_price, chg_pct = 0.0, 0.0
                        for k, p in price_map.items():
                            if ("0050" in name and "0050" in k) or ("台積電" in name and "台積電" in k) or (name in k or k in name):
                                curr_price, chg_pct = p, change_map.get(k, 0.0)
                                break
                        if curr_price == 0.0 and shares > 0: curr_price = m_val / shares
                        holdings.append({"stock_name": name, "shares": shares, "avg_cost": avg_cost, "total_cost": cost, "current_price": curr_price, "market_value": m_val, "各股損益": profit, "change_pct": chg_pct})

        profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0

        ws_overview = sh.worksheet("每日損益追蹤")
        hist_data = [{"日期": r[0].strip(), "總累積成本": parse_num(r[5]), "總市值": parse_num(r[6]), "總投資損益": parse_num(r[7]), "0050每日損益": parse_num(r[12]), "台積電每日損益": parse_num(r[13])} for r in ws_overview.get_all_values()[1:] if len(r) >= 14 and str(r[0]).strip() != ""]
                
        return {"total_assets": total_assets, "total_cost": total_cost, "total_profit": total_profit, "profit_rate": profit_rate, "holdings": holdings}, hist_data
    except: return None, None

def load_bank_data():
    client = get_gspread_client()
    if not client: return 58661.0, []
    try:
        sh = client.open(SPREADSHEET_NAME)
        try: b_val = float(str(sh.worksheet("資產總覽").get_all_values()[1][11]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 58661)
        except: b_val = 58661.0
        
        txs = [{"日期": r[0].strip(), "類型": r[1].strip(), "金額": float(str(r[2]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 0), "備註": r[3].strip()} for r in sh.worksheet("db_bank_ledger").get_all_values()[1:] if len(r) >= 4 and str(r[0]).strip() != ""]
        return b_val, txs
    except: return 58661.0, []

# ==========================================
# 3. 視覺化引擎與樣式函數
# ==========================================
C_LBL = "#FFD700"; C_VAL = "#00E5FF"; C_PCT = "#00E676"

def style_fig(fig, title):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=24, color="#FFD700"), x=0.01, y=0.95),
        font=dict(size=16, color="#e0e0e0"), template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="rgba(25, 30, 40, 0.95)", font_size=20, font_family="Arial, sans-serif", bordercolor="rgba(0, 229, 255, 0.8)"),
        margin=dict(l=20, r=20, t=85, b=30), hovermode="x unified",
        xaxis=dict(showgrid=False, zeroline=False, title="", tickformat="%Y-%m-%d", showspikes=True, spikemode="across", spikedash="dash", spikecolor="#FF00FF", spikethickness=2), 
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=True, zerolinecolor="rgba(255,255,255,0.1)", title="")
    )
    return fig

def add_zero_baseline(fig):
    fig.add_hline(y=0, line_dash="dash", line_color="#FFD700", line_width=2)
    return fig

def create_colorful_card(title, value_str, icon="", theme="blue", is_profit=False, num_val=None):
    if is_profit and num_val is not None:
        bg = "linear-gradient(135deg, #1e2128 0%, #13151a 100%)"
        if num_val > 0: text_c, glow_shadow = "#ff4b4b", "0 8px 20px rgba(255, 75, 75, 0.3)"
        elif num_val < 0: text_c, glow_shadow = "#09ab3b", "0 8px 20px rgba(9, 171, 59, 0.3)"
        else: text_c, glow_shadow = "#ffffff", "0 8px 20px rgba(255, 255, 255, 0.1)"
    else:
        if theme == "purple": bg, glow_shadow, text_c = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "0 8px 20px rgba(118, 75, 162, 0.5)", "#fef08a"
        elif theme == "blue": bg, glow_shadow, text_c = "linear-gradient(135deg, #2b5876 0%, #4e4376 100%)", "0 8px 20px rgba(78, 67, 118, 0.5)", "#a7f3d0"
        elif theme == "gold": bg, glow_shadow, text_c = "linear-gradient(135deg, #FF8008 0%, #FFC837 100%)", "0 8px 20px rgba(200, 128, 8, 0.4)", "#ffffff"
        else: bg, glow_shadow, text_c = "linear-gradient(135deg, #1e2128 0%, #13151a 100%)", "none", "#ffffff"
            
    return f"""
    <div style="background: {bg}; border-radius: 12px; padding: 20px; box-shadow: {glow_shadow}; border: 1px solid rgba(255,255,255,0.05); height: 130px; position: relative; overflow: hidden; margin-bottom: 15px;">
        <p style="margin: 0; font-size: 1.2rem; color: #d1d5db; font-weight: bold; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">{title}</p>
        <p style="margin: 5px 0 0 0; font-size: 2.3rem; font-weight: 900; color: {text_c}; text-shadow: 0 0 15px {text_c}50;">{value_str}</p>
        <div style="position: absolute; right: -15px; bottom: -25px; font-size: 6.5rem; opacity: 0.15; z-index: 0; transform: rotate(-15deg);">{icon}</div>
    </div>
    """

def style_profit_loss(s):
    return ['color: #ff4b4b; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else ('color: #09ab3b; font-weight: bold;' if isinstance(v, (int, float)) and v < 0 else '') for v in s]

# ==========================================
# 4. 資料全域預處理
# ==========================================
bank_balance, txs = load_bank_data()
dashboard_data, hist_data = load_sheet_data()

df_h, df_hist, df_txs = None, None, None

stock_price_dict = {"元大台灣0050": 0.0, "台積電": 0.0}
stock_options = ["元大台灣0050", "台積電", "其他 (手動輸入新股)"]

if dashboard_data and dashboard_data.get("holdings"):
    df_h = pd.DataFrame(dashboard_data["holdings"])
    df_h["各股損益(%)"] = df_h.apply(lambda x: (x["各股損益"]/x["total_cost"]*100) if x["total_cost"]>0 else 0, axis=1)
    
    for h in dashboard_data["holdings"]:
        name = h["stock_name"]
        if name not in stock_options:
            stock_options.insert(0, name)
        stock_price_dict[name] = h["current_price"]

if hist_data:
    df_hist = pd.DataFrame(hist_data)
    df_hist["真實日期"] = pd.to_datetime(df_hist["日期"], errors='coerce')
    df_hist = df_hist.dropna(subset=["真實日期"]).sort_values("真實日期")
    df_hist["星期"] = df_hist["真實日期"].dt.weekday.map(WEEK_MAP)
    df_hist["日期_顯示"] = df_hist["真實日期"].dt.strftime('%Y/%m/%d') + " (" + df_hist["星期"] + ")"
    
    df_hist["ROI(%)"] = (df_hist["總投資損益"] / df_hist["總累積成本"]) * 100
    df_hist["單日損益變化"] = df_hist["總投資損益"].diff().fillna(0)
    df_hist["單日漲跌幅(%)"] = (df_hist["單日損益變化"] / df_hist["總累積成本"].shift(1) * 100).fillna(0)
    df_hist["最高市值"] = df_hist["總市值"].cummax()
    df_hist["市值回撤"] = df_hist["總市值"] - df_hist["最高市值"]
    df_hist["20日均線"] = df_hist["總市值"].rolling(window=20, min_periods=1).mean()

if txs:
    df_txs = pd.DataFrame(txs)
    df_txs['日期_dt'] = pd.to_datetime(df_txs['日期'], errors='coerce')
    df_txs = df_txs.dropna(subset=['日期_dt']).sort_values('日期_dt')
    df_txs['星期'] = df_txs['日期_dt'].dt.weekday.map(WEEK_MAP)
    df_txs['日期_顯示'] = df_txs['日期_dt'].dt.strftime('%Y/%m/%d') + " (" + df_txs['星期'] + ")"
    df_txs['流向'] = df_txs['金額'].apply(lambda x: '流出 (支出/買股)' if x < 0 else '流入 (存錢/賣股)')
    df_txs['金額絕對值'] = df_txs['金額'].abs()
    df_txs['累計淨現金流'] = df_txs['金額'].cumsum()

# ==========================================
# 5. 側邊欄：控制中心與聯動輸入表單
# ==========================================
if "stock_selector" not in st.session_state:
    st.session_state.stock_selector = stock_options[0]
if "s_price" not in st.session_state:
    st.session_state.s_price = float(stock_price_dict.get(stock_options[0], 0.0))
if "s_shares" not in st.session_state:
    st.session_state.s_shares = 0
if "s_fee" not in st.session_state:
    st.session_state.s_fee = 0.0

def on_stock_change():
    sel = st.session_state.stock_selector
    if sel != "其他 (手動輸入新股)":
        st.session_state.s_price = float(stock_price_dict.get(sel, 0.0))
    else:
        st.session_state.s_price = 0.0
    calc_fee()

def calc_fee():
    shares = st.session_state.s_shares
    price = st.session_state.s_price
    name = st.session_state.stock_selector
    if name == "其他 (手動輸入新股)":
        name = st.session_state.get("s_name_input", "")
        
    if shares == 0 or price == 0.0:
        st.session_state.s_fee = 0.0
        return
        
    cost = abs(shares) * price
    broker_fee = max(20, int(cost * 0.001425 * 0.6))
    tax = 0
    if shares < 0: 
        tax_rate = 0.001 if "00" in name else 0.003
        tax = int(cost * tax_rate)
    st.session_state.s_fee = float(broker_fee + tax)

with st.sidebar:
    st.title("⚙️ 異動控制中心")
    st.info("💡 輸入後自動換算手續費，送出後即時更新。")
    
    tab_bank, tab_stock = st.tabs(["🏦 銀行金流", "📈 股票交易"])
    
    with tab_bank:
        st.markdown("### 新增銀行金流")
        with st.form("bank_record_form"):
            # ✨ 日期防呆：鎖定只能選今天以前 (包含今天)
            rec_date = st.date_input("入帳日期", value=datetime.date.today(), max_value=datetime.date.today())
            rec_type = st.selectbox("異動類型", ["現金", "跨行轉", "轉帳投", "委代入", "證券款", "電匯", "交割扣款"])
            amount = st.number_input("金額 (元) 【扣款請輸入負數】", value=0.0, step=100.0)
            note = st.text_input("備註說明")
            
            if st.form_submit_button("寫入金流紀錄", use_container_width=True):
                if amount != 0:
                    try:
                        fmt_date = rec_date.strftime('%Y/%m/%d')
                        sh = get_gspread_client().open(SPREADSHEET_NAME)
                        sh.worksheet("db_bank_ledger").append_row([fmt_date, rec_type, amount, note], value_input_option="USER_ENTERED")
                        st.success("紀錄成功寫入！")
                        st.rerun()
                    except Exception as e: st.error(f"寫入失敗: {e}")
                else: st.warning("請輸入有效金額。")
                
    with tab_stock:
        st.markdown("### 新增股票交易")
        
        selected_stock = st.selectbox("選擇操作標的", stock_options, key="stock_selector", on_change=on_stock_change)
        
        if selected_stock == "其他 (手動輸入新股)":
            st.text_input("輸入新股票名稱", key="s_name_input", on_change=calc_fee)
            
        # ✨ 日期防呆：鎖定只能選今天以前 (包含今天)
        s_date = st.date_input("交易日期", value=datetime.date.today(), max_value=datetime.date.today())
        
        st.number_input("股數 (買入為正，賣出為負)", step=1, key="s_shares", on_change=calc_fee)
        st.number_input("成交單價", step=0.1, key="s_price", on_change=calc_fee)
        st.number_input("手續費/稅金 (已自動試算中信費率)", step=1.0, key="s_fee")
        
        # ✨ 新增：動態交割總額提示框 (讓使用者安心核對)
        current_shares = st.session_state.s_shares
        current_price = st.session_state.s_price
        current_fee = st.session_state.s_fee
        if current_shares > 0:
            est_total = (current_shares * current_price) + current_fee
            st.info(f"💵 **預估交割扣款:** NT$ {est_total:,.0f}")
        elif current_shares < 0:
            est_total = abs(current_shares * current_price) - current_fee
            st.info(f"💰 **預估交割入帳:** NT$ {est_total:,.0f}")
        else:
            st.info("💡 預估交割總額: NT$ 0")
        
        if st.button("寫入股票紀錄", use_container_width=True):
            shares = st.session_state.s_shares
            price = st.session_state.s_price
            name = st.session_state.get("s_name_input", "") if selected_stock == "其他 (手動輸入新股)" else selected_stock
            
            if shares != 0 and price > 0 and name.strip() != "":
                try:
                    s_date_fmt = s_date.strftime('%Y/%m/%d')
                    total_amt = (shares * price) + st.session_state.s_fee
                    sh = get_gspread_client().open(SPREADSHEET_NAME)
                    sh.worksheet("db_stock_transactions").append_row([s_date_fmt, name, shares, price, st.session_state.s_fee, total_amt], value_input_option="USER_ENTERED")
                    st.success("股票紀錄成功寫入！")
                    st.rerun()
                except Exception as e: st.error(f"寫入失敗: {e}")
            else: st.warning("請確認股數、價格與股票名稱填寫正確。")

# ==========================================
# 主畫面開始
# ==========================================
st.title("💼 個人旗艦資產工作站 ☁️")
st.markdown("##### 🚀 終極數據戰情室 | 全方位投資決策系統")

tab1, tab2 = st.tabs(["📊 總覽儀表板 (含報表與明細)", "🌌 終極數據戰情室 (21種圖表)"])

# ------------------------------------------
# 分頁 1：總覽儀表板
# ------------------------------------------
with tab1:
    if dashboard_data:
        d = dashboard_data
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(create_colorful_card("總市值", f"NT$ {d['total_assets']:,.0f}", "💎", "purple"), unsafe_allow_html=True)
        c2.markdown(create_colorful_card("總投入成本", f"NT$ {d['total_cost']:,.0f}", "📥", "blue"), unsafe_allow_html=True)
        c3.markdown(create_colorful_card("銀行活存餘額", f"NT$ {bank_balance:,.0f}", "🏦", "gold"), unsafe_allow_html=True)
        c4.markdown(create_colorful_card("帳面總損益", f"{d['total_profit']:+,.0f}", "🔥", is_profit=True, num_val=d['total_profit']), unsafe_allow_html=True)
        c5.markdown(create_colorful_card("總獲利率 (%)", f"{d['profit_rate']:+.2f}%", "📈", is_profit=True, num_val=d['profit_rate']), unsafe_allow_html=True)

        if df_h is not None:
            st.subheader("📋 投資組合即時明細")
            df_display = df_h.rename(columns={
                "stock_name":"股票名稱", "shares":"總股數", "avg_cost":"平均成本", 
                "total_cost":"總成本", "current_price":"即時現價", "market_value":"即時市值", "change_pct":"即時漲跌幅(%)"
            })[["股票名稱", "總股數", "平均成本", "總成本", "即時現價", "即時市值", "各股損益", "即時漲跌幅(%)", "各股損益(%)"]]
            
            styled_df = df_display.style.apply(style_profit_loss, subset=["即時現價", "各股損益", "即時漲跌幅(%)", "各股損益(%)"]) \
                                        .format({"總股數": "{:,.0f}", "平均成本": "{:,.2f}", "總成本": "{:,.0f}", "即時現價": "{:,.2f}", 
                                                 "即時市值": "{:,.0f}", "各股損益": "{:+,.0f}", "即時漲跌幅(%)": "{:+.2f}%", "各股損益(%)": "{:+.2f}%"})
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.divider()
    
    col_hist, col_bank = st.columns(2)
    
    with col_hist:
        st.subheader("📜 歷史每日結算報表")
        if df_hist is not None:
            df_hist_filtered = df_hist[df_hist['星期'].isin(['一', '二', '三', '四', '五'])].copy()
            df_hist_filtered['日期'] = df_hist_filtered['日期_顯示']
            df_hist_display = df_hist_filtered.drop(columns=["單日損益變化", "單日漲跌幅(%)", "最高市值", "市值回撤", "20日均線", "真實日期", "日期_顯示", "星期"], errors='ignore')[::-1]
            
            styled_hist = df_hist_display.style.apply(style_profit_loss, subset=["總投資損益", "0050每日損益", "台積電每日損益", "ROI(%)"]) \
                            .format({"總累積成本": "{:,.0f}", "總市值": "{:,.0f}", "總投資損益": "{:+,.0f}", "0050每日損益": "{:+,.0f}", "台積電每日損益": "{:+,.0f}", "ROI(%)": "{:+.2f}%"})
            st.dataframe(styled_hist, use_container_width=True, hide_index=True)
        else:
            st.info("目前暫無歷史紀錄。")
            
    with col_bank:
        st.subheader("🏦 銀行帳戶資金流水明細")
        if df_txs is not None:
            df_bank_display = df_txs[::-1][["日期_顯示", "類型", "金額", "備註"]].copy().rename(columns={"日期_顯示": "日期"})
            # ✨ 透過 CSS 強制把「類型」欄位置右對齊，讓表格更工整
            styled_bank = df_bank_display.style.apply(style_profit_loss, subset=["金額"])\
                            .format({"金額": "{:+,.0f}"})\
                            .set_properties(subset=['類型'], **{'text-align': 'right'})
            st.dataframe(styled_bank, use_container_width=True, hide_index=True)
        else:
            st.info("尚無銀行紀錄。")

# ------------------------------------------
# 分頁 2：🌌 終極數據戰情室 (21 張圖表)
# ------------------------------------------
with tab2:
    if df_h is not None:
        st.markdown("### 🔍 展區一：資產版圖與持股透視")
        c2_1, c2_2, c2_3 = st.columns(3)
        with c2_1:
            fig1 = px.pie(names=['股票總市值', '銀行帳戶餘額'], values=[dashboard_data["total_assets"], bank_balance], hole=0.5, color_discrete_sequence=['#3498db', '#f1c40f'])
            fig1.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>金額: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent}}</b></span><extra></extra>", textinfo='label+percent')
            st.plotly_chart(style_fig(fig1, "1. 總資產水庫配置"), use_container_width=True)
            
        with c2_2:
            fig2 = px.pie(df_h, names='stock_name', values='market_value', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig2.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>市值: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent}}</b></span><extra></extra>", textinfo='label+percent')
            st.plotly_chart(style_fig(fig2, "2. 個股市值佔比"), use_container_width=True)

        with c2_3:
            fig3 = px.pie(df_h, names='stock_name', values='total_cost', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>投入成本: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent}}</b></span><extra></extra>", textinfo='label+percent')
            st.plotly_chart(style_fig(fig3, "3. 投入本金佈局佔比"), use_container_width=True)

        c2_4, c2_5, c2_6 = st.columns(3)
        with c2_4:
            fig4 = px.treemap(df_h, path=['stock_name'], values='market_value', color='各股損益(%)', color_continuous_scale=['#09ab3b', '#222222', '#ff4b4b'], color_continuous_midpoint=0)
            fig4.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>市值: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>帳面損益: %{{color:+.2f}}%</b></span><extra></extra>", textfont=dict(size=18, color="white"))
            st.plotly_chart(style_fig(fig4, "4. 股票熱力圖 (面積=市值, 色=賺賠)"), use_container_width=True)

        with c2_5:
            fig5 = go.Figure(go.Waterfall(
                orientation="v", measure=["relative"]*len(df_h) + ["total"],
                x=df_h['stock_name'].tolist() + ["淨損益總計"], y=df_h['各股損益'].tolist() + [dashboard_data["total_profit"]],
                decreasing={"marker":{"color":"#09ab3b"}}, increasing={"marker":{"color":"#ff4b4b"}}, totals={"marker":{"color":"#3498db"}}
            ))
            fig5.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{x}}</b></span><br><span style='color:{C_VAL}'><b>損益金額: NT$ %{{y:+,.0f}}</b></span><extra></extra>", texttemplate="%{y:+,.0s}", textposition="outside")
            st.plotly_chart(style_fig(fig5, "5. 各股獲利貢獻瀑布圖"), use_container_width=True)

        with c2_6:
            fig6 = go.Figure(data=[
                go.Bar(name='總投入成本', x=df_h['stock_name'], y=df_h['total_cost'], marker_color='#9b59b6'),
                go.Bar(name='當前總市值', x=df_h['stock_name'], y=df_h['market_value'], marker_color='#f1c40f')
            ])
            fig6.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{x}}</b></span><br><span style='color:{C_VAL}'><b>金額: NT$ %{{y:,.0f}}</b></span><extra></extra>")
            fig6.update_layout(barmode='group')
            st.plotly_chart(style_fig(fig6, "6. 個股成本 vs 現值對比"), use_container_width=True)

    st.divider()
    st.markdown("### 📈 展區二：時間維度與趨勢擴張")
    if df_hist is not None:
        df_hist['繪圖日期'] = df_hist['真實日期'].dt.strftime('%Y/%m/%d')
        
        c2_7, c2_8 = st.columns(2)
        with c2_7:
            fig7 = go.Figure()
            fig7.add_trace(go.Scatter(
                x=df_hist['繪圖日期'], y=df_hist['總投資損益'].clip(lower=0), customdata=df_hist['總投資損益'],
                mode='lines', fill='tozeroy', line=dict(color='#ff4b4b', width=2), name="獲利"
            ))
            fig7.add_trace(go.Scatter(
                x=df_hist['繪圖日期'], y=df_hist['總投資損益'].clip(upper=0), customdata=df_hist['總投資損益'],
                mode='lines', fill='tozeroy', line=dict(color='#09ab3b', width=2), name="虧損"
            ))
            fig7 = style_fig(fig7, "7. 總投資累積損益面積圖 (紅漲綠跌)")
            fig7 = add_zero_baseline(fig7) 
            fig7.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>累積損益: NT$ %{{customdata:+,.0f}}</b></span><extra></extra>")
            fig7.update_layout(showlegend=False)
            st.plotly_chart(fig7, use_container_width=True)
            
        with c2_8:
            fig8 = go.Figure()
            fig8.add_trace(go.Scatter(x=df_hist['繪圖日期'], y=df_hist['總市值'], mode='lines', name='總市值', line=dict(color='#2ecc71', width=3)))
            fig8.add_trace(go.Scatter(x=df_hist['繪圖日期'], y=df_hist['20日均線'], mode='lines', name='20日均線', line=dict(color='#f39c12', width=2, dash='dot')))
            fig8.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{data.name}}</b></span><br><span style='color:{C_VAL}'><b>金額: NT$ %{{y:,.0f}}</b></span><extra></extra>")
            st.plotly_chart(style_fig(fig8, "8. 總市值與 20 日均線乖離"), use_container_width=True)

        c2_9, c2_10 = st.columns(2)
        with c2_9:
            fig9 = go.Figure(go.Scatter(x=df_hist['繪圖日期'], y=df_hist['ROI(%)'], mode='lines+markers', line=dict(color='#9b59b6', width=2)))
            fig9 = style_fig(fig9, "9. 投資報酬率 (ROI) 走勢")
            fig9 = add_zero_baseline(fig9) 
            fig9.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_PCT}'><b>投資報酬率: %{{y:+.2f}}%</b></span><extra></extra>")
            st.plotly_chart(fig9, use_container_width=True)

        with c2_10:
            fig10 = go.Figure()
            fig10.add_trace(go.Bar(x=df_hist['繪圖日期'], y=df_hist['0050每日損益'], name='0050', marker_color='#3498db'))
            fig10.add_trace(go.Bar(x=df_hist['繪圖日期'], y=df_hist['台積電每日損益'], name='台積電', marker_color='#e74c3c'))
            fig10.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{data.name}}</b></span><br><span style='color:{C_VAL}'><b>部位損益: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            fig10.update_layout(barmode='relative')
            st.plotly_chart(style_fig(fig10, "10. 每日損益部位貢獻疊加"), use_container_width=True)
            
        c2_11, c2_12 = st.columns(2)
        with c2_11:
            fig11 = go.Figure()
            fig11.add_trace(go.Scatter(x=df_hist['繪圖日期'], y=df_hist['0050每日損益'].cumsum(), mode='lines', name='0050 累計', line=dict(color='#3498db')))
            fig11.add_trace(go.Scatter(x=df_hist['繪圖日期'], y=df_hist['台積電每日損益'].cumsum(), mode='lines', name='台積電 累計', line=dict(color='#e74c3c')))
            fig11.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{data.name}}</b></span><br><span style='color:{C_VAL}'><b>累計貢獻: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            st.plotly_chart(style_fig(fig11, "11. 雙引擎累計獲利賽跑"), use_container_width=True)

        with c2_12:
            fig12 = px.scatter(df_hist, x="總累積成本", y="總市值", color="ROI(%)", color_continuous_scale="Turbo", size_max=10)
            fig12 = style_fig(fig12, "12. 資產擴張散點回歸圖 (虛線=損益兩平)")
            fig12.add_shape(type="line", x0=df_hist["總累積成本"].min(), y0=df_hist["總累積成本"].min(), x1=df_hist["總累積成本"].max(), y1=df_hist["總累積成本"].max(), line=dict(color="#FFD700", width=2, dash="dash"))
            fig12.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>總成本: NT$ %{{x:,.0f}}</b></span><br><span style='color:{C_VAL}'><b>總市值: NT$ %{{y:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>ROI: %{{marker.color:+.2f}}%</b></span><extra></extra>", marker=dict(size=8, opacity=0.8))
            st.plotly_chart(fig12, use_container_width=True)

        st.divider()
        st.markdown("### ⚠️ 展區三：風險回撤與規律矩陣")
        c2_13, c2_14, c2_15 = st.columns(3)
        with c2_13:
            vol_colors = ['#ff4b4b' if val > 0 else '#09ab3b' for val in df_hist['單日損益變化']]
            fig13 = go.Figure(go.Bar(x=df_hist['繪圖日期'], y=df_hist['單日損益變化'], marker_color=vol_colors))
            fig13 = style_fig(fig13, "13. 單日總損益震盪圖")
            fig13 = add_zero_baseline(fig13) 
            fig13.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>單日波動金額: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            st.plotly_chart(fig13, use_container_width=True)
            
        with c2_14:
            fig14 = px.histogram(df_hist, x="單日損益變化", nbins=20, color_discrete_sequence=['#3498db'])
            fig14 = style_fig(fig14, "14. 盈虧分佈直方圖 (鐘型頻率)")
            fig14.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>損益區間: NT$ %{{x:,.0f}}</b></span><br><span style='color:{C_VAL}'><b>發生次數: %{{y}} 次</b></span><extra></extra>")
            fig14.update_layout(hovermode="closest")
            st.plotly_chart(fig14, use_container_width=True)
            
        with c2_15:
            fig15 = go.Figure(go.Scatter(x=df_hist['繪圖日期'], y=df_hist['市值回撤'], fill='tozeroy', mode='lines', line=dict(color='#e67e22', width=2)))
            fig15 = style_fig(fig15, "15. 歷史最大回撤 (Drawdown)")
            fig15 = add_zero_baseline(fig15) 
            fig15.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>高點回撤金額: NT$ %{{y:,.0f}}</b></span><extra></extra>")
            st.plotly_chart(fig15, use_container_width=True)

        c2_16, c2_17, c2_18 = st.columns(3)
        with c2_16:
            fig16 = go.Figure(go.Scatter(x=df_hist['繪圖日期'], y=df_hist['單日漲跌幅(%)'], mode='lines', line=dict(color='#1abc9c', width=2)))
            fig16 = style_fig(fig16, "16. 單日總資產漲跌幅 (%) 走勢")
            fig16 = add_zero_baseline(fig16) 
            fig16.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_PCT}'><b>單日漲跌幅: %{{y:+.2f}}%</b></span><extra></extra>")
            st.plotly_chart(fig16, use_container_width=True)

        with c2_17:
            win_days, lose_days = len(df_hist[df_hist['單日損益變化'] > 0]), len(df_hist[df_hist['單日損益變化'] < 0])
            fig17 = px.pie(names=['上漲天數', '下跌天數'], values=[win_days, lose_days], hole=0.6, color_discrete_sequence=['#ff4b4b', '#09ab3b'])
            fig17.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>天數: %{{value}} 天</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent}}</b></span><extra></extra>", textinfo='label+percent')
            st.plotly_chart(style_fig(fig17, "17. 歷史操作日勝率"), use_container_width=True)

        with c2_18:
            dow_avg = df_hist.groupby("星期")["單日損益變化"].mean().reindex(['一', '二', '三', '四', '五']).reset_index()
            fig18 = go.Figure(go.Bar(x=dow_avg['星期'], y=dow_avg['單日損益變化'], marker_color=['#ff4b4b' if v>0 else '#09ab3b' for v in dow_avg['單日損益變化']]))
            fig18 = style_fig(fig18, "18. 星期別平均波動分析")
            fig18.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>星期%{{x}}</b></span><br><span style='color:{C_VAL}'><b>平均損益: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            fig18.update_layout(hovermode="closest")
            st.plotly_chart(fig18, use_container_width=True)

    st.divider()
    st.markdown("### 🏦 展區四：現金流動脈分析")
    if df_txs is not None:
        df_txs['繪圖日期'] = df_txs['日期_dt'].dt.strftime('%Y/%m/%d')
        c2_19, c2_20, c2_21 = st.columns(3)
        with c2_19:
            fig19 = px.sunburst(df_txs, path=['流向', '類型'], values='金額絕對值', color='流向', color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig19.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>累積金額: NT$ %{{value:,.0f}}</b></span><extra></extra>")
            st.plotly_chart(style_fig(fig19, "19. 銀行金流樹狀結構"), use_container_width=True)
            
        with c2_20:
            fig20 = px.bar(df_txs, x="繪圖日期", y="金額", color="流向", color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig20 = style_fig(fig20, "20. 單筆資金進出分布")
            fig20.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>異動金額: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            fig20.update_layout(showlegend=False, hovermode="closest")
            st.plotly_chart(fig20, use_container_width=True)
            
        with c2_21:
            fig21 = go.Figure(go.Scatter(x=df_txs['繪圖日期'], y=df_txs['累計淨現金流'], mode='lines+markers', line=dict(color='#9b59b6', width=3)))
            fig21 = style_fig(fig21, "21. 累計淨現金流走勢")
            fig21 = add_zero_baseline(fig21)
            fig21.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>累計淨金流: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            st.plotly_chart(fig21, use_container_width=True)
    else:
        st.info("💡 尚未有足夠的銀行明細來生成金流圖表，請至左側控制中心新增紀錄。")
