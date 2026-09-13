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
    
    /* 🔥 終極無縫流光引擎：改為平滑來回掃描，徹底消除週期結束時的頓挫感！ */
    @keyframes sweep-light { 
        0% { background-position: 100% 100%; } 
        50% { background-position: 0% 0%; } 
        100% { background-position: 100% 100%; } 
    }

    /* --- 頂部 Tab 樣式 --- */
    div[data-baseweb="tab-list"] { 
        display: flex !important;
        width: 100% !important;
        gap: 15px !important; 
        background-color: transparent !important;
        border-bottom: none !important;
    }
    
    div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {
        display: none !important;
        background-color: transparent !important;
    }
    
    button[data-baseweb="tab"] { 
        flex: 1 1 0 !important;
        background-color: #1e2128 !important; 
        border-radius: 50px !important;  
        padding: 12px 0px !important; 
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        margin: 0 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
    }
    
    button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p {
        width: 100%;
        text-align: center;
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #a0a5b1 !important;
    }
    
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

    /* =========================================
       科技感動態切換按鈕
       ========================================= */
    div[data-testid="stRadio"] div[role="radiogroup"] label input[type="radio"] + div {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child:not([data-testid="stMarkdownContainer"]) {
        display: none !important;
    }
    
    div[data-testid="stRadio"] > div { 
        gap: 10px; 
        background: #111318 !important; 
        padding: 6px 10px; 
        border-radius: 50px; 
        display: inline-flex; 
        border: 1px solid rgba(255,255,255,0.05); 
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.5);
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] label { 
        padding: 8px 32px !important; 
        border-radius: 50px !important; 
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; 
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: transparent !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.05) !important;
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked),
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(div[aria-checked="true"]) { 
        background: linear-gradient(135deg, #0a1128 0%, #0a1128 40%, #1c5276 50%, #0a1128 60%, #0a1128 100%) !important; 
        background-size: 300% 300% !important;
        background-repeat: no-repeat !important;
        animation: sweep-light 4s ease-in-out infinite !important;
        box-shadow: 0 8px 20px rgba(28, 82, 118, 0.5) !important; 
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] label p { 
        color: #7f8ca6 !important; 
        font-weight: 600 !important;
        font-size: 16px !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p,
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(div[aria-checked="true"]) p { 
        color: #ffffff !important; 
        font-weight: 900 !important; 
        text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
    }

    /* =========================================
       魔法：強制把第3頁 Plotly 圖表包成動態光波大框框
       ========================================= */
    div[data-testid="stElementContainer"]:has(#future-chart-bg) + div[data-testid="stElementContainer"] {
        background: linear-gradient(135deg, #0a1128 0%, #0a1128 40%, #1c5276 50%, #0a1128 60%, #0a1128 100%) !important;
        background-size: 300% 300% !important;
        background-repeat: no-repeat !important;
        animation: sweep-light 5s ease-in-out infinite !important;
        border-radius: 12px !important;
        padding: 25px !important;
        box-shadow: 0 8px 20px rgba(28, 82, 118, 0.5) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        margin-top: 15px !important;
        margin-bottom: 30px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }
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

@st.cache_data(ttl=600, show_spinner=False)
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

@st.cache_data(ttl=600, show_spinner=False)
def load_bank_data():
    client = get_gspread_client()
    if not client: return 58661.0, []
    try:
        sh = client.open(SPREADSHEET_NAME)
        try: b_val = float(str(sh.worksheet("資產總覽").get_all_values()[1][11]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 58661)
        except: b_val = 58661.0
        
        txs = [{"日期": r[0].strip(), "類型": r[1].strip(), "金額": float(str(r[2]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 0)} for r in sh.worksheet("db_bank_ledger").get_all_values()[1:] if len(r) >= 3 and str(r[0]).strip() != ""]
        return b_val, txs
    except: return 58661.0, []

@st.cache_data(ttl=600, show_spinner=False)
def load_stock_transactions():
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open(SPREADSHEET_NAME)
        rows = sh.worksheet("db_stock_transactions").get_all_values()
        if len(rows) > 1:
            df = pd.DataFrame(rows[1:])
            if df.shape[1] >= 6:
                df = df[[0, 1, 2, 5]].rename(columns={0: '日期', 1: '標的', 2: '股數', 5: '單筆總價'})
                df['日期_dt'] = pd.to_datetime(df['日期'], errors='coerce')
                df['股數'] = pd.to_numeric(df['股數'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df['單筆總價'] = pd.to_numeric(df['單筆總價'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df['YYYY-MM-DD'] = df['日期_dt'].dt.strftime('%Y-%m-%d')
                df['YYYY-MM'] = df['日期_dt'].dt.strftime('%Y-%m')
                return df
    except:
        pass
    return pd.DataFrame()

# ==========================================
# 3. 視覺化引擎與樣式函數
# ==========================================
C_LBL = "#FFD700"  
C_VAL = "#00E5FF"  
C_PCT = "#00E676"  

def add_zero_baseline(fig):
    fig.add_hline(y=0, line_dash="dash", line_color="#FFD700", line_width=2)
    return fig

def style_fig(fig, title, height=500):
    fig.update_layout(
        height=height,
        title=dict(text=f"<b>{title}</b>", font=dict(size=22, color="#FFD700"), x=0.01, y=0.95),
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="rgba(25, 30, 40, 0.95)", font=dict(size=16, family="Arial, sans-serif", color="#ffffff"), bordercolor="rgba(0, 229, 255, 0.8)", namelength=-1),
        margin=dict(l=40, r=40, t=85, b=60),  
        hovermode="x unified",
        xaxis=dict(
            automargin=True,
            showgrid=False, zeroline=False, title="", tickformat="%Y-%m-%d", 
            showspikes=True, spikemode="across", spikedash="dash", spikecolor="#FF00FF", spikethickness=2,
            tickangle=-45 
        ), 
        yaxis=dict(
            automargin=True,
            showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=True, zerolinecolor="rgba(255,255,255,0.1)", title=""
        )
    )
    return fig

def render_styled_chart(fig, chart_id, bg_gradient):
    fig.update_layout(
        # 移除字體顏色硬綁定，讓系統自動判斷深淺色
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=70, b=60) 
    )
    st.markdown(f'''
    <div id="{chart_id}"></div>
    <style>
        div[data-testid="stElementContainer"]:has(#{chart_id}) + div[data-testid="stElementContainer"] {{
            background: {bg_gradient} !important;
            background-size: 300% 300% !important; 
            background-repeat: no-repeat !important; /* 確保不出現拼貼縫隙 */
            animation: sweep-light 6s ease-in-out infinite !important; /* 共用平滑折返引擎 */
            border-radius: 12px !important;
            padding: 20px !important;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            margin-bottom: 25px !important;
            box-sizing: border-box !important;
            overflow: hidden !important; 
        }}
    </style>
    ''', unsafe_allow_html=True)
    # 移除 theme=None，讓 Streamlit 根據淺/深色模式自動切換黑白字體
    st.plotly_chart(fig, use_container_width=True)

# 🔥 21 種高階漸層，完美 135deg (左上至右下) 與 0% 40% 50% 60% 100% 配方
chart_gradients = [
    "linear-gradient(135deg, #141e30 0%, #141e30 40%, #243b55 50%, #141e30 60%, #141e30 100%)", # 1 深海藍
    "linear-gradient(135deg, #0f2027 0%, #0f2027 40%, #2c5364 50%, #0f2027 60%, #0f2027 100%)", # 2 幽黑綠
    "linear-gradient(135deg, #0f0c29 0%, #0f0c29 40%, #24243e 50%, #0f0c29 60%, #0f0c29 100%)", # 3 賽博紫
    "linear-gradient(135deg, #2b5876 0%, #2b5876 40%, #4e4376 50%, #2b5876 60%, #2b5876 100%)", # 4 星雲藍
    "linear-gradient(135deg, #16222A 0%, #16222A 40%, #3A6073 50%, #16222A 60%, #16222A 100%)", # 5 迷霧灰
    "linear-gradient(135deg, #232526 0%, #232526 40%, #414345 50%, #232526 60%, #232526 100%)", # 6 碳纖黑
    "linear-gradient(135deg, #1A2980 0%, #1A2980 40%, #135A59 50%, #1A2980 60%, #1A2980 100%)", # 7 皇室青
    "linear-gradient(135deg, #4B1248 0%, #4B1248 40%, #8E4C33 50%, #4B1248 60%, #4B1248 100%)", # 8 暗夜銅
    "linear-gradient(135deg, #114357 0%, #114357 40%, #844c66 50%, #114357 60%, #114357 100%)", # 9 晚霞紫
    "linear-gradient(135deg, #1d1f20 0%, #1d1f20 40%, #2c3e50 50%, #1d1f20 60%, #1d1f20 100%)", # 10 曜石板
    "linear-gradient(135deg, #13151a 0%, #13151a 40%, #2c3e50 50%, #13151a 60%, #13151a 100%)", # 11 午夜黑
    "linear-gradient(135deg, #00467F 0%, #00467F 40%, #426B3D 50%, #00467F 60%, #00467F 100%)", # 12 森林藍
    "linear-gradient(135deg, #1D2B64 0%, #1D2B64 40%, #734657 50%, #1D2B64 60%, #1D2B64 100%)", # 13 絳紫靛
    "linear-gradient(135deg, #191654 0%, #191654 40%, #217361 50%, #191654 60%, #191654 100%)", # 14 翡翠黑
    "linear-gradient(135deg, #314755 0%, #314755 40%, #195878 50%, #314755 60%, #314755 100%)", # 15 沉靜洋
    "linear-gradient(135deg, #3A5573 0%, #3A5573 40%, #3B6A69 50%, #3A5573 60%, #3A5573 100%)", # 16 海藻丹
    "linear-gradient(135deg, #4B0000 0%, #4B0000 40%, #42271D 50%, #4B0000 60%, #4B0000 100%)", # 17 鐵鏽紅
    "linear-gradient(135deg, #0A5E4E 0%, #0A5E4E 40%, #826E21 50%, #0A5E4E 60%, #0A5E4E 100%)", # 18 琥珀綠
    "linear-gradient(135deg, #1A471C 0%, #1A471C 40%, #42461A 50%, #1A471C 60%, #1A471C 100%)", # 19 墨光苔
    "linear-gradient(135deg, #26555C 0%, #26555C 40%, #3F4B4D 50%, #26555C 60%, #26555C 100%)", # 20 鐵鈦灰
    "linear-gradient(135deg, #4A0213 0%, #4A0213 40%, #4A3029 50%, #4A0213 60%, #4A0213 100%)"  # 21 酒桶木
]

def create_colorful_card(title, value_str, icon="", theme="blue", is_profit=False, num_val=None):
    if is_profit and num_val is not None:
        bg = "linear-gradient(135deg, #16181d 0%, #16181d 40%, #34425a 50%, #16181d 60%, #16181d 100%)"
        if num_val > 0: text_c, glow_shadow = "#ff4b4b", "0 8px 20px rgba(255, 75, 75, 0.4)"
        elif num_val < 0: text_c, glow_shadow = "#09ab3b", "0 8px 20px rgba(9, 171, 59, 0.4)"
        else: text_c, glow_shadow = "#ffffff", "0 8px 20px rgba(255, 255, 255, 0.1)"
    else:
        if theme == "purple": bg, glow_shadow, text_c = "linear-gradient(135deg, #667eea 0%, #667eea 40%, #9b59b6 50%, #667eea 60%, #667eea 100%)", "0 8px 20px rgba(118, 75, 162, 0.5)", "#fef08a"
        elif theme == "blue": bg, glow_shadow, text_c = "linear-gradient(135deg, #0a1128 0%, #0a1128 40%, #1c5276 50%, #0a1128 60%, #0a1128 100%)", "0 8px 20px rgba(28, 82, 118, 0.5)", "#a7f3d0"
        elif theme == "gold": bg, glow_shadow, text_c = "linear-gradient(135deg, #FF8008 0%, #FF8008 40%, #FFC837 50%, #FF8008 60%, #FF8008 100%)", "0 8px 20px rgba(200, 128, 8, 0.4)", "#ffffff"
        else: bg, glow_shadow, text_c = "linear-gradient(135deg, #1e2128 0%, #1e2128 40%, #3a4a5a 50%, #1e2128 60%, #1e2128 100%)", "none", "#ffffff"
            
    return f"""
    <div style="background: {bg}; background-size: 300% 300%; background-repeat: no-repeat; animation: sweep-light 4s ease-in-out infinite; border-radius: 12px; padding: 15px; box-shadow: {glow_shadow}; border: 1px solid rgba(255,255,255,0.05); min-height: 120px; height: 100%; display: flex; flex-direction: column; justify-content: center; position: relative; overflow: hidden; margin-bottom: 15px;">
        <p style="margin: 0; font-size: 1.1rem; color: #d1d5db; font-weight: bold; text-shadow: 0 1px 2px rgba(0,0,0,0.5); position: relative; z-index: 1;">{title}</p>
        <p style="margin: 5px 0 0 0; font-size: clamp(1.4rem, 2vw, 2.3rem); font-weight: 900; color: {text_c}; text-shadow: 0 0 15px {text_c}50; line-height: 1.2; word-wrap: break-word; position: relative; z-index: 1;">{value_str}</p>
        <div style="position: absolute; right: -15px; bottom: -25px; font-size: 6.5rem; opacity: 0.15; z-index: 0; transform: rotate(-15deg); pointer-events: none;">{icon}</div>
    </div>
    """

def style_profit_loss(s):
    return ['color: #ff4b4b; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else ('color: #09ab3b; font-weight: bold;' if isinstance(v, (int, float)) and v < 0 else '') for v in s]

def style_portfolio_row(row):
    styles = [''] * len(row)
    for i, col in enumerate(row.index):
        if col in ['各股損益', '各股損益(%)']:
            styles[i] = 'color: #ff4b4b; font-weight: bold;' if row[col] > 0 else ('color: #09ab3b; font-weight: bold;' if row[col] < 0 else '')
        elif col in ['即時現價', '即時漲跌幅(%)']:
            chg = row['即時漲跌幅(%)']
            styles[i] = 'color: #ff4b4b; font-weight: bold;' if chg > 0 else ('color: #09ab3b; font-weight: bold;' if chg < 0 else '')
    return styles

# ==========================================
# 4. 資料全域預處理
# ==========================================
bank_balance, txs = load_bank_data()
dashboard_data, hist_data = load_sheet_data()
df_st = load_stock_transactions()

df_h, df_hist, df_txs = None, None, None

stock_price_dict = {"元大台灣0050": 0.0, "台積電": 0.0}
stock_options = ["元大台灣0050", "台積電", "其他 (手動輸入新股)"]

if dashboard_data and dashboard_data.get("holdings"):
    df_h = pd.DataFrame(dashboard_data["holdings"])
    df_h["各股損益(%)"] = df_h.apply(lambda x: (x["各股損益"]/x["total_cost"]*100) if x["total_cost"]>0 else 0, axis=1).astype(float).round(2)
    df_h["各股損益_str"] = df_h["各股損益(%)"].apply(lambda x: f"{x:+.2f}")
    
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
    df_hist["日期_顯示"] = df_hist["真實日期"].dt.strftime('%Y/%m/%d') + "(" + df_hist["星期"] + ")"
    
    df_hist["總損益(%)"] = ((df_hist["總投資損益"] / df_hist["總累積成本"]) * 100).fillna(0).astype(float).round(2)
    df_hist["單日損益變化"] = df_hist["總投資損益"].diff().fillna(0).astype(float)
    df_hist["單日漲跌幅(%)"] = ((df_hist["單日損益變化"] / df_hist["總累積成本"].shift(1)) * 100).fillna(0).astype(float).round(2)
    
    df_hist["總損益_str"] = df_hist["總損益(%)"].apply(lambda x: f"{x:+.2f}")
    df_hist["單日漲跌幅_str"] = df_hist["單日漲跌幅(%)"].apply(lambda x: f"{x:+.2f}")

    df_hist["最高市值"] = df_hist["總市值"].cummax()
    df_hist["市值回撤"] = df_hist["總市值"] - df_hist["最高市值"]
    df_hist["20日均線"] = df_hist["總市值"].rolling(window=20, min_periods=1).mean()
    df_hist["0050累計"] = df_hist["0050每日損益"].cumsum()
    df_hist["台積電累計"] = df_hist["台積電每日損益"].cumsum()

if txs:
    df_txs = pd.DataFrame(txs)
    df_txs['日期_dt'] = pd.to_datetime(df_txs['日期'], errors='coerce')
    df_txs = df_txs.dropna(subset=['日期_dt']).sort_values('日期_dt')
    df_txs['星期'] = df_txs['日期_dt'].dt.weekday.map(WEEK_MAP)
    df_txs['日期_顯示'] = df_txs['日期_dt'].dt.strftime('%Y/%m/%d') + "(" + df_txs['星期'] + ")"
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
    
    if st.button("🔄 強制同步最新試算表資料", use_container_width=True):
        load_sheet_data.clear()
        load_bank_data.clear()
        load_stock_transactions.clear()
        st.rerun()
    
    st.divider()
    
    tab_bank, tab_stock = st.tabs(["🏦 銀行金流", "📈 股票交易"])
    
    with tab_bank:
        st.markdown("### 新增銀行金流")
        
        if "bank_confirm" not in st.session_state:
            st.session_state.bank_confirm = False

        is_locked = st.session_state.bank_confirm

        rec_date = st.date_input("入帳日期", value=datetime.date.today(), max_value=datetime.date.today(), key="bank_date", disabled=is_locked)
        rec_type = st.selectbox("異動類型", ["現金", "跨行轉", "轉帳提", "委代入", "證券款", "電匯", "定期定額"], key="bank_type", disabled=is_locked)
        amount = st.number_input("金額 (系統將自動判斷正負)", min_value=0.0, step=100.0, key="bank_amount", disabled=is_locked)
        
        is_zero = (amount == 0)
        
        action_container = st.empty()

        if not st.session_state.bank_confirm:
            if action_container.button("寫入金流紀錄", use_container_width=True, disabled=is_zero, key="bank_submit_btn"):
                st.session_state.bank_confirm = True
                st.rerun()
        else:
            action_container.warning(f"⚠️ 請問確定要寫入此筆銀行金流嗎？\n\n- **日期**: {rec_date.strftime('%Y/%m/%d')}\n- **類型**: {rec_type}\n- **金額**: {amount:,.0f}")
            c_yes, c_no = action_container.columns(2)
            with c_yes:
                if st.button("✅ 確認寫入", use_container_width=True, key="bank_yes"):
                    try:
                        fmt_date = rec_date.strftime('%Y/%m/%d')
                        final_amount = amount if rec_type in ["現金", "跨行轉", "委代入", "電匯"] else -amount
                            
                        sh = get_gspread_client().open(SPREADSHEET_NAME)
                        sh.worksheet("db_bank_ledger").append_row([fmt_date, rec_type, final_amount], value_input_option="USER_ENTERED")
                        
                        load_bank_data.clear()
                        load_sheet_data.clear()
                        load_stock_transactions.clear()
                        st.session_state.bank_confirm = False
                        st.success("紀錄成功寫入！")
                        st.rerun()
                    except Exception as e: 
                        st.error(f"寫入失敗: {e}")
            with c_no:
                if st.button("❌ 取消", use_container_width=True, key="bank_no"):
                    st.session_state.bank_confirm = False
                    st.rerun()
                
    with tab_stock:
        st.markdown("### 新增股票交易")
        
        if "stock_confirm" not in st.session_state:
            st.session_state.stock_confirm = False

        is_stock_locked = st.session_state.stock_confirm

        selected_stock = st.selectbox("選擇操作標的", stock_options, key="stock_selector", on_change=on_stock_change, disabled=is_stock_locked)
        
        if selected_stock == "其他 (手動輸入新股)":
            st.text_input("輸入新股票名稱", key="s_name_input", on_change=calc_fee, disabled=is_stock_locked)
            
        s_date = st.date_input("交易日期", value=datetime.date.today(), max_value=datetime.date.today(), disabled=is_stock_locked)
        
        st.number_input("股數 (買入為正，賣出為負)", step=1, key="s_shares", on_change=calc_fee, disabled=is_stock_locked)
        st.number_input("成交單價", step=0.1, key="s_price", on_change=calc_fee, disabled=is_stock_locked)
        st.number_input("手續費/稅金 (已自動試算中信費率)", step=1.0, key="s_fee", disabled=is_stock_locked)
        
        current_shares = st.session_state.s_shares
        current_price = st.session_state.s_price
        current_fee = st.session_state.s_fee
        
        st.markdown("""
        <style>
            .est-box { padding: 12px 15px; border-radius: 8px; font-weight: 900; white-space: nowrap; font-size: 16px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .est-blue { background-color: #74b9ff !important; border-left: 6px solid #0984e3 !important; color: #0c2461 !important; }
            .est-green { background-color: #55efc4 !important; border-left: 6px solid #00b894 !important; color: #004d40 !important; }
            .est-gray { background-color: #dfe6e9 !important; border-left: 6px solid #636e72 !important; color: #2d3436 !important; }
            .est-blue *, .est-green *, .est-gray * { color: inherit !important; }
        </style>
        """, unsafe_allow_html=True)
        
        if current_shares > 0:
            est_total = round((current_shares * current_price) + current_fee)
            st.markdown(f'<div class="est-box est-blue">💵 預估扣款: NT$ {est_total:,.0f}</div>', unsafe_allow_html=True)
        elif current_shares < 0:
            est_total = round(abs(current_shares * current_price) - current_fee)
            st.markdown(f'<div class="est-box est-green">💰 預估入帳: NT$ {est_total:,.0f}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="est-box est-gray">💡 預估交割: NT$ 0</div>', unsafe_allow_html=True)
        
        name_check = st.session_state.get("s_name_input", "") if selected_stock == "其他 (手動輸入新股)" else selected_stock
        is_stock_zero = (current_shares == 0 or not name_check.strip())
        
        stock_action_container = st.empty()

        if not st.session_state.stock_confirm:
            if stock_action_container.button("寫入股票紀錄", use_container_width=True, disabled=is_stock_zero):
                st.session_state.stock_confirm = True
                st.rerun()

        if st.session_state.stock_confirm:
            total_amt_check = round((current_shares * current_price) + st.session_state.s_fee)
            
            stock_action_container.warning(f"⚠️ 請問確定要寫入此筆股票交易嗎？\n\n- **日期**: {s_date.strftime('%Y/%m/%d')}\n- **標的**: {name_check}\n- **股數**: {current_shares:,}\n- **單價**: {current_price}\n- **金額**: NT$ {total_amt_check:,.0f}")
            sc_yes, sc_no = stock_action_container.columns(2)
            with sc_yes:
                if st.button("✅ 確認寫入股票", use_container_width=True, key="stock_yes"):
                    try:
                        s_date_fmt = s_date.strftime('%Y/%m/%d')
                        total_amt = round((current_shares * current_price) + st.session_state.s_fee)
                        sh = get_gspread_client().open(SPREADSHEET_NAME)
                        sh.worksheet("db_stock_transactions").append_row([s_date_fmt, name_check, current_shares, current_price, st.session_state.s_fee, total_amt], value_input_option="USER_ENTERED")
                        
                        load_sheet_data.clear()
                        load_bank_data.clear()
                        load_stock_transactions.clear()
                        st.session_state.stock_confirm = False
                        st.success("股票紀錄成功寫入！")
                        st.rerun()
                    except Exception as e: 
                        st.error(f"寫入失敗: {e}")
            with sc_no:
                if st.button("❌ 取消寫入", use_container_width=True, key="stock_no"):
                    st.session_state.stock_confirm = False
                    st.rerun()

# ==========================================
# 主畫面開始
# ==========================================
st.title("💼 個人旗艦資產工作站 ☁️")
st.markdown("##### 🚀 終極數據戰情室 | 全方位投資決策系統")

tab1, tab2, tab3 = st.tabs(["📊 總覽儀表板 (含報表與明細)", "🌌 終極數據戰情室 (21種圖表)", "🎯 定期定額與願景"])

# ------------------------------------------
# 分頁 1：總覽儀表板
# ------------------------------------------
with tab1:
    if dashboard_data:
        d = dashboard_data
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(create_colorful_card("總市值", f"NT$ {d['total_assets']:,.0f}", "💎", "purple"), unsafe_allow_html=True)
        c2.markdown(create_colorful_card("總投入成本", f"NT$ {d['total_cost']:,.0f}", "📥", "purple"), unsafe_allow_html=True)
        c3.markdown(create_colorful_card("銀行活存餘額", f"NT$ {bank_balance:,.0f}", "🏦", "gold"), unsafe_allow_html=True)
        c4.markdown(create_colorful_card("帳面總損益", f"{d['total_profit']:+,.0f}", "🔥", is_profit=True, num_val=d['total_profit']), unsafe_allow_html=True)
        c5.markdown(create_colorful_card("總損益 (%)", f"{d['profit_rate']:+.2f}%", "📈", is_profit=True, num_val=d['profit_rate']), unsafe_allow_html=True)

        if df_h is not None:
            st.subheader("📋 投資組合即時明細")
            df_display = df_h.rename(columns={
                "stock_name":"股票名稱", "shares":"總股數", "avg_cost":"平均成本", 
                "total_cost":"總成本", "current_price":"即時現價", "market_value":"即時市值", "change_pct":"即時漲跌幅(%)"
            })[["股票名稱", "總股數", "平均成本", "總成本", "即時現價", "即時市值", "各股損益", "即時漲跌幅(%)", "各股損益(%)"]]
            
            styled_df = df_display.style.apply(style_portfolio_row, axis=1) \
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
            df_hist_display = df_hist_filtered.drop(columns=["單日損益變化", "單日漲跌幅(%)", "最高市值", "市值回撤", "20日均線", "真實日期", "日期_顯示", "星期", "0050累計", "台積電累計", "總損益_str", "單日漲跌幅_str"], errors='ignore')[::-1]
            
            styled_hist = df_hist_display.style.apply(style_profit_loss, subset=["總投資損益", "0050每日損益", "台積電每日損益", "總損益(%)"]) \
                            .format({"總累積成本": "{:,.0f}", "總市值": "{:,.0f}", "總投資損益": "{:+,.0f}", "0050每日損益": "{:+,.0f}", "台積電每日損益": "{:+,.0f}", "總損益(%)": "{:+.2f}%"})
            st.dataframe(styled_hist, use_container_width=True, hide_index=True)
        else:
            st.info("目前暫無歷史紀錄。")
            
    with col_bank:
        st.subheader("🏦 銀行帳戶資金流水明細")
        if df_txs is not None:
            df_bank_display = df_txs[::-1][["日期_顯示", "類型", "金額"]].copy().rename(columns={"日期_顯示": "日期"})
            styled_bank = df_bank_display.style.apply(style_profit_loss, subset=["金額"])\
                            .format({"金額": "{:+,.0f}"})
            
            st.dataframe(
                styled_bank, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "類型": st.column_config.TextColumn("類型", alignment="right")
                }
            )
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
            fig1.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>金額: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent:.2%}}</b></span><extra></extra>", texttemplate="<b>%{label}</b><br><b>%{percent:.2%}</b>", textposition='inside', insidetextorientation='horizontal', textfont=dict(color='#ffffff', size=16, weight='bold'))
            render_styled_chart(style_fig(fig1, "1. 總資產水庫配置"), "chart_1", chart_gradients[0])
            
        with c2_2:
            fig2 = px.pie(df_h, names='stock_name', values='market_value', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig2.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>市值: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent:.2%}}</b></span><extra></extra>", texttemplate="<b>%{label}</b><br><b>%{percent:.2%}</b>", textposition='inside', insidetextorientation='horizontal', textfont=dict(color='#ffffff', size=16, weight='bold'))
            render_styled_chart(style_fig(fig2, "2. 個股市值佔比"), "chart_2", chart_gradients[1])

        with c2_3:
            fig3 = px.pie(df_h, names='stock_name', values='total_cost', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>投入成本: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent:.2%}}</b></span><extra></extra>", texttemplate="<b>%{label}</b><br><b>%{percent:.2%}</b>", textposition='inside', insidetextorientation='horizontal', textfont=dict(color='#ffffff', size=16, weight='bold'))
            render_styled_chart(style_fig(fig3, "3. 投入本金佈局佔比"), "chart_3", chart_gradients[2])

        c2_4, c2_5, c2_6 = st.columns(3)
        with c2_4:
            fig4 = px.treemap(df_h, path=['stock_name'], values='market_value', color='各股損益(%)', color_continuous_scale=['#09ab3b', '#222222', '#ff4b4b'], color_continuous_midpoint=0, custom_data=['各股損益_str'])
            fig4.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>市值: NT$ %{{value:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>帳面損益: %{{customdata[0]}}%</b></span><extra></extra>", textfont=dict(size=18, color="white"))
            fig4.update_layout(coloraxis_colorbar=dict(tickformat=".2f"))  
            render_styled_chart(style_fig(fig4, "4. 股票熱力圖 (面積=市值, 色=賺賠)"), "chart_4", chart_gradients[3])

        with c2_5:
            fig5 = go.Figure(go.Waterfall(
                orientation="v", measure=["relative"]*len(df_h) + ["total"],
                x=df_h['stock_name'].tolist() + ["淨損益總計"], y=df_h['各股損益'].tolist() + [dashboard_data["total_profit"]],
                decreasing={"marker":{"color":"#09ab3b"}}, increasing={"marker":{"color":"#ff4b4b"}}, totals={"marker":{"color":"#3498db"}}
            ))
            fig5.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{x}}</b></span><br><span style='color:{C_VAL}'><b>損益金額: NT$ %{{y:+,.0f}}</b></span><extra></extra>", texttemplate="%{y:+,.0s}", textposition="outside")
            render_styled_chart(style_fig(fig5, "5. 各股獲利貢獻瀑布圖"), "chart_5", chart_gradients[4])

        with c2_6:
            fig6 = go.Figure(data=[
                go.Bar(name='總投入成本', x=df_h['stock_name'], y=df_h['total_cost'], marker_color='#9b59b6'),
                go.Bar(name='當前總市值', x=df_h['stock_name'], y=df_h['market_value'], marker_color='#f1c40f')
            ])
            fig6.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{x}}</b></span><br><span style='color:{C_VAL}'><b>金額: NT$ %{{y:,.0f}}</b></span><extra></extra>")
            fig6.update_layout(barmode='group')
            render_styled_chart(style_fig(fig6, "6. 個股成本 vs 現值對比"), "chart_6", chart_gradients[5])

    st.divider()
    st.markdown("### 📈 展區二：時間維度與趨勢擴張")
    if df_hist is not None:
        df_hist_plot = df_hist[df_hist['星期'].isin(['一', '二', '三', '四', '五'])].copy()
        df_hist_plot['繪圖日期'] = df_hist_plot['日期_顯示']
        
        c2_7, c2_8 = st.columns(2)
        with c2_7:
            fig7 = go.Figure()
            fig7.add_trace(go.Scatter(
                x=df_hist_plot['繪圖日期'], y=df_hist_plot['總投資損益'].clip(lower=0),
                mode='lines', fill='tozeroy', line=dict(color='#ff4b4b', width=2), 
                hoverinfo='skip', showlegend=False
            ))
            fig7.add_trace(go.Scatter(
                x=df_hist_plot['繪圖日期'], y=df_hist_plot['總投資損益'].clip(upper=0),
                mode='lines', fill='tozeroy', line=dict(color='#09ab3b', width=2), 
                hoverinfo='skip', showlegend=False
            ))
            
            c7_vals = [f"{v:+,.0f}" for v in df_hist_plot['總投資損益']]
            c7_colors = ['#ff4b4b' if v >= 0 else '#09ab3b' for v in df_hist_plot['總投資損益']]
            
            fig7.add_trace(go.Bar(
                x=df_hist_plot['繪圖日期'], 
                y=[0] * len(df_hist_plot), 
                customdata=np.column_stack((c7_vals, c7_colors)),
                marker_color=c7_colors, 
                name="", 
                hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:%{{customdata[1]}}'><b>累積損益: NT$ %{{customdata[0]}}</b></span><extra></extra>"
            ))
            
            fig7.update_xaxes(type='category')
            fig7 = add_zero_baseline(fig7) 
            fig7.update_layout(showlegend=False)
            render_styled_chart(style_fig(fig7, "7. 總投資累積損益面積圖 (紅漲綠跌)"), "chart_7", chart_gradients[6])
            
        with c2_8:
            fig8 = go.Figure()
            fig8.add_trace(go.Scatter(x=df_hist_plot['繪圖日期'], y=df_hist_plot['總市值'], mode='lines', name='總市值', line=dict(color='#2ecc71', width=3)))
            fig8.add_trace(go.Scatter(x=df_hist_plot['繪圖日期'], y=df_hist_plot['20日均線'], mode='lines', name='20日均線', line=dict(color='#f39c12', width=2, dash='dot')))
            fig8.update_xaxes(type='category')
            fig8.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{data.name}}</b></span><br><span style='color:{C_VAL}'><b>金額: NT$ %{{y:,.0f}}</b></span><extra></extra>")
            render_styled_chart(style_fig(fig8, "8. 總市值與 20 日均線乖離"), "chart_8", chart_gradients[7])

        c2_9, c2_10 = st.columns(2)
        with c2_9:
            fig9 = go.Figure(go.Scatter(
                x=df_hist_plot['繪圖日期'], y=df_hist_plot['總損益(%)'], 
                customdata=df_hist_plot['總損益_str'], 
                mode='lines+markers', line=dict(color='#9b59b6', width=2)
            ))
            fig9.update_xaxes(type='category')
            fig9 = add_zero_baseline(fig9) 
            fig9.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_PCT}'><b>總損益: %{{customdata}}%</b></span><extra></extra>")
            fig9.update_yaxes(tickformat=".2f")  
            render_styled_chart(style_fig(fig9, "9. 總損益 (%) 走勢"), "chart_9", chart_gradients[8])

        with c2_10:
            fig10 = go.Figure()
            fig10.add_trace(go.Bar(x=df_hist_plot['繪圖日期'], y=df_hist_plot['0050每日損益'], name='0050', marker_color='#3498db'))
            fig10.add_trace(go.Bar(x=df_hist_plot['繪圖日期'], y=df_hist_plot['台積電每日損益'], name='台積電', marker_color='#e74c3c'))
            fig10.update_xaxes(type='category')
            fig10.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{data.name}}</b></span><br><span style='color:{C_VAL}'><b>部位損益: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            fig10.update_layout(barmode='relative')
            render_styled_chart(style_fig(fig10, "10. 每日損益部位貢獻疊加"), "chart_10", chart_gradients[9])
            
        c2_11, c2_12 = st.columns(2)
        with c2_11:
            fig11 = go.Figure()
            fig11.add_trace(go.Scatter(x=df_hist_plot['繪圖日期'], y=df_hist_plot['0050累計'], mode='lines', name='0050 累計', line=dict(color='#3498db')))
            fig11.add_trace(go.Scatter(x=df_hist_plot['繪圖日期'], y=df_hist_plot['台積電累計'], mode='lines', name='台積電 累計', line=dict(color='#e74c3c')))
            fig11.update_xaxes(type='category')
            fig11.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{data.name}}</b></span><br><span style='color:{C_VAL}'><b>累計貢獻: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            render_styled_chart(style_fig(fig11, "11. 雙引擎累計獲利賽跑"), "chart_11", chart_gradients[10])

        with c2_12:
            fig12 = px.scatter(df_hist_plot, x="總累積成本", y="總市值", color="總損益(%)", color_continuous_scale="Turbo", size_max=10, custom_data=['總損益_str', '繪圖日期'])
            fig12.add_shape(type="line", x0=df_hist_plot["總累積成本"].min(), y0=df_hist_plot["總累積成本"].min(), x1=df_hist_plot["總累積成本"].max(), y1=df_hist_plot["總累積成本"].max(), line=dict(color="#FFD700", width=2, dash="dash"))
            fig12.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{customdata[1]}}</b></span><br><span style='color:{C_LBL}'><b>總成本: NT$ %{{x:,.0f}}</b></span><br><span style='color:{C_VAL}'><b>總市值: NT$ %{{y:,.0f}}</b></span><br><span style='color:{C_PCT}'><b>總損益: %{{customdata[0]}}%</b></span><extra></extra>", marker=dict(size=8, opacity=0.8))
            fig12.update_layout(coloraxis_colorbar=dict(tickformat=".2f"), hovermode="closest") 
            render_styled_chart(style_fig(fig12, "12. 資產擴張散點回歸圖 (虛線=損益兩平)"), "chart_12", chart_gradients[11])

        st.divider()
        st.markdown("### ⚠️ 展區三：風險回撤與規律矩陣")
        c2_13, c2_14, c2_15 = st.columns(3)
        with c2_13:
            vol_colors = ['#ff4b4b' if val > 0 else '#09ab3b' for val in df_hist_plot['單日損益變化']]
            fig13 = go.Figure(go.Bar(x=df_hist_plot['繪圖日期'], y=df_hist_plot['單日損益變化'], marker_color=vol_colors))
            fig13.update_xaxes(type='category')
            fig13 = add_zero_baseline(fig13) 
            fig13.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>單日波動金額: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            render_styled_chart(style_fig(fig13, "13. 單日總損益震盪圖"), "chart_13", chart_gradients[12])
            
        with c2_14:
            fig14 = px.histogram(df_hist_plot, x="單日損益變化", nbins=20, color_discrete_sequence=['#3498db'])
            fig14.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>損益區間: NT$ %{{x:,.0f}}</b></span><br><span style='color:{C_VAL}'><b>發生次數: %{{y}} 次</b></span><extra></extra>")
            fig14.update_layout(hovermode="closest")
            render_styled_chart(style_fig(fig14, "14. 盈虧分佈直方圖 (鐘型頻率)"), "chart_14", chart_gradients[13])
            
        with c2_15:
            fig15 = go.Figure(go.Scatter(x=df_hist_plot['繪圖日期'], y=df_hist_plot['市值回撤'], fill='tozeroy', mode='lines', line=dict(color='#e67e22', width=2)))
            fig15.update_xaxes(type='category')
            fig15 = add_zero_baseline(fig15) 
            fig15.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>高點回撤金額: NT$ %{{y:,.0f}}</b></span><extra></extra>")
            render_styled_chart(style_fig(fig15, "15. 歷史最大回撤 (Drawdown)"), "chart_15", chart_gradients[14])

        c2_16, c2_17, c2_18 = st.columns(3)
        with c2_16:
            fig16 = go.Figure(go.Scatter(
                x=df_hist_plot['繪圖日期'], y=df_hist_plot['單日漲跌幅(%)'], 
                customdata=df_hist_plot['單日漲跌幅_str'], 
                mode='lines', line=dict(color='#1abc9c', width=2)
            ))
            fig16.update_xaxes(type='category')
            fig16 = add_zero_baseline(fig16) 
            fig16.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_PCT}'><b>單日漲跌幅: %{{customdata}}%</b></span><extra></extra>")
            fig16.update_yaxes(tickformat=".2f")  
            render_styled_chart(style_fig(fig16, "16. 單日總資產漲跌幅 (%) 走勢"), "chart_16", chart_gradients[15])

        with c2_17:
            win_days, lose_days = len(df_hist_plot[df_hist_plot['單日損益變化'] > 0]), len(df_hist_plot[df_hist_plot['單日損益變化'] < 0])
            fig17 = px.pie(names=['上漲天數', '下跌天數'], values=[win_days, lose_days], hole=0.6, color_discrete_sequence=['#ff4b4b', '#09ab3b'])
            fig17.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>天數: %{{value}} 天</b></span><br><span style='color:{C_PCT}'><b>佔比: %{{percent:.2%}}</b></span><extra></extra>", texttemplate="<b>%{label}</b><br><b>%{percent:.2%}</b>", textposition='inside', textfont=dict(color='#ffffff', size=16, weight='bold'))
            render_styled_chart(style_fig(fig17, "17. 歷史操作日勝率"), "chart_17", chart_gradients[16])

        with c2_18:
            dow_avg = df_hist_plot.groupby("星期")["單日損益變化"].mean().round(0).reindex(['一', '二', '三', '四', '五']).reset_index()
            fig18 = go.Figure(go.Bar(x=dow_avg['星期'], y=dow_avg['單日損益變化'], marker_color=['#ff4b4b' if v>0 else '#09ab3b' for v in dow_avg['單日損益變化']]))
            fig18.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>星期%{{x}}</b></span><br><span style='color:{C_VAL}'><b>平均損益: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            fig18.update_layout(hovermode="closest")
            render_styled_chart(style_fig(fig18, "18. 星期別平均波動分析"), "chart_18", chart_gradients[17])

    st.divider()
    st.markdown("### 🏦 展區四：現金流動脈分析")
    if df_txs is not None:
        df_txs_plot = df_txs.copy()
        df_txs_plot['繪圖日期'] = df_txs_plot['日期_顯示']
        
        c2_19, c2_20, c2_21 = st.columns(3)
        with c2_19:
            fig19 = px.sunburst(df_txs_plot, path=['流向', '類型'], values='金額絕對值', color='流向', color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig19.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{C_VAL}'><b>累積金額: NT$ %{{value:,.0f}}</b></span><extra></extra>", textfont=dict(color='#ffffff', size=14, weight='bold'))
            render_styled_chart(style_fig(fig19, "19. 銀行金流樹狀結構"), "chart_19", chart_gradients[18])
            
        with c2_20:
            fig20 = px.bar(df_txs_plot, x="繪圖日期", y="金額", color="流向", color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig20.update_xaxes(type='category')
            fig20.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>異動金額: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            fig20.update_layout(showlegend=False, hovermode="closest")
            render_styled_chart(style_fig(fig20, "20. 單筆資金進出分布"), "chart_20", chart_gradients[19])
            
        with c2_21:
            fig21 = go.Figure(go.Scatter(x=df_txs_plot['繪圖日期'], y=df_txs_plot['累計淨現金流'], mode='lines+markers', line=dict(color='#9b59b6', width=3)))
            fig21.update_xaxes(type='category')
            fig21 = add_zero_baseline(fig21)
            fig21.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>日期: %{{x}}</b></span><br><span style='color:{C_VAL}'><b>累計淨金流: NT$ %{{y:+,.0f}}</b></span><extra></extra>")
            render_styled_chart(style_fig(fig21, "21. 累計淨現金流走勢"), "chart_21", chart_gradients[20])

# ------------------------------------------
# 分頁 3：🎯 定期定額與願景
# ------------------------------------------
with tab3:
    # 1. 預先獨立計算 0050 與 台積電 的基底狀態
    current_0050_value = 0
    current_0050_shares = 0
    current_0050_cost = 0
    
    current_tsmc_value = 0
    current_tsmc_cost = 0
    
    if df_h is not None:
        stock_0050 = df_h[df_h['stock_name'].str.contains('0050', na=False)]
        if not stock_0050.empty:
            current_0050_value = stock_0050['market_value'].sum()
            current_0050_shares = stock_0050['shares'].sum()
            current_0050_cost = stock_0050['total_cost'].sum()
            
        stock_tsmc = df_h[df_h['stock_name'].str.contains('台積電', na=False)]
        if not stock_tsmc.empty:
            current_tsmc_value = stock_tsmc['market_value'].sum()
            current_tsmc_cost = stock_tsmc['total_cost'].sum()
            
    avg_cost_0050 = (current_0050_cost / current_0050_shares) if current_0050_shares > 0 else 0
    market_price_0050 = (current_0050_value / current_0050_shares) if current_0050_shares > 0 else 0

    # ==========================================
    # 🎯 區塊一：10 年 120 期紀律矩陣
    # ==========================================
    st.markdown("### 🏆 紀律印記：定期定額 10 年軌跡")
    
    sip_records = []
    real_sip_avg = 6000  
    
    if df_txs is not None and not df_txs.empty:
        df_sip = df_txs[df_txs['類型'] == '定期定額'].copy()
        if not df_sip.empty:
            real_sip_avg = int(df_sip['金額'].abs().mean())
            
            df_sip = df_sip.sort_values('日期_dt')
            df_sip['YYYY-MM'] = df_sip['日期_dt'].dt.strftime('%Y-%m')
            df_sip['YYYY-MM-DD'] = df_sip['日期_dt'].dt.strftime('%Y-%m-%d')
            df_sip = df_sip.drop_duplicates(subset=['YYYY-MM'], keep='last')
            sip_records = df_sip.to_dict('records')

    html_blocks = []
    for i in range(120):
        if i < len(sip_records):
            rec = sip_records[i]
            amt = abs(rec['金額'])
            date_str = rec['日期_dt'].strftime('%Y/%m/%d')
            
            shares = 0
            if df_st is not None and not df_st.empty:
                match = df_st[(df_st['YYYY-MM-DD'] == rec['YYYY-MM-DD']) & (df_st['標的'].str.contains('0050', na=False)) & (df_st['股數'] > 0)]
                if not match.empty:
                    if len(match) == 1:
                        shares = int(match['股數'].iloc[0])
                    else:
                        match = match.copy()
                        match['diff'] = (match['單筆總價'] - amt).abs()
                        best_match = match.sort_values('diff').iloc[0]
                        shares = int(best_match['股數'])
            
            if shares == 0:
                shares = int(amt / market_price_0050) if market_price_0050 > 0 else 0
            
            html_blocks.append(
                f'<div style="display: flex; flex-direction: column; align-items: center; width: 100%;">'
                f'<div style="width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #09ab3b, #00b894); color: white; display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 0 10px rgba(9, 171, 59, 0.5);">✓</div>'
                f'<div style="font-size: 11px; font-weight: bold; color: #a7f3d0; margin-top: 6px; white-space: nowrap;">{date_str}</div>'
                f'<div style="font-size: 11px; color: #d1d5db; white-space: nowrap;">{shares} 股</div>'
                f'</div>'
            )
        else:
            html_blocks.append(
                f'<div style="display: flex; flex-direction: column; align-items: center; width: 100%;">'
                f'<div style="width: 38px; height: 38px; border-radius: 50%; border: 2px dashed rgba(255,255,255,0.4); display: flex; align-items: center; justify-content: center;"></div>'
                f'<div style="font-size: 11px; font-weight: bold; color: rgba(255,255,255,0.8); margin-top: 6px; white-space: nowrap;">#{i+1}</div>'
                f'<div style="font-size: 11px; color: rgba(255,255,255,0.6); white-space: nowrap;">待扣款</div>'
                f'</div>'
            )

    blocks_str = ''.join(html_blocks)
    
    full_html = (
        f'<div style="background: linear-gradient(135deg, #0a1128 0%, #0a1128 40%, #1c5276 50%, #0a1128 60%, #0a1128 100%); background-size: 300% 300%; background-repeat: no-repeat; animation: sweep-light 5s ease-in-out infinite; padding: 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 8px 20px rgba(28, 82, 118, 0.4); margin-bottom: 30px; width: 100%; box-sizing: border-box; overflow: hidden;">'
        f'<p style="font-size: 1.1rem; color: #ffffff; font-weight: bold; margin-bottom: 20px; text-shadow: 0 1px 3px rgba(0,0,0,0.6);">🎯 10 年 120 期解鎖進度 (自動讀取銀行流水與證券明細)</p>'
        f'<div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 20px 5px; width: 100%; justify-items: center;">'
        f'{blocks_str}'
        f'</div>'
        f'</div>'
    )
    st.markdown(full_html, unsafe_allow_html=True)
    
    st.divider()

    # ==========================================
    # 🎯 區塊二：多重資產複利雪球時光機
    # ==========================================
    st.markdown("### ⏳ 多重資產動態投影 (0050 + 台積電)")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    monthly_invest = col_s1.number_input("預測每月扣款 (專攻 0050)", value=real_sip_avg, step=100)
    years = col_s2.slider("預計持續年數", min_value=1, max_value=30, value=10)
    price_rate = col_s3.slider("市場年化成長預期 (%)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)
    div_yield = col_s4.slider("預估殖利率 (%)", min_value=0.0, max_value=10.0, value=3.5, step=0.5)

    st.markdown("##### ⚙️ 圖表時間跨度設定")
    resolution = st.radio("切換解析度", ["每年", "每月"], horizontal=True, label_visibility="collapsed")

    months = years * 12
    monthly_price_rate = price_rate / 100 / 12
    monthly_div_rate = div_yield / 100 / 12
    
    acc_cost_0050 = current_0050_cost
    val_nodrip_0050 = current_0050_value
    val_drip_0050 = current_0050_value
    
    acc_cost_tsmc = current_tsmc_cost
    val_nodrip_tsmc = current_tsmc_value
    val_drip_tsmc = current_tsmc_value
    
    curr_year = datetime.date.today().year
    curr_month = datetime.date.today().month
    
    future_data = [{
        "時間": f"現在 ({curr_year}年{curr_month}月)", 
        "總累積本金": current_0050_cost + current_tsmc_cost, 
        "總無再投入": current_0050_value + current_tsmc_value, 
        "總再投入": current_0050_value + current_tsmc_value,
        "0050累積本金": current_0050_cost, "0050無再投入": current_0050_value, "0050再投入": current_0050_value,
        "TSMC累積本金": current_tsmc_cost, "TSMC無再投入": current_tsmc_value, "TSMC再投入": current_tsmc_value
    }]
    
    for m in range(1, months + 1):
        div_0050 = val_drip_0050 * monthly_div_rate
        div_tsmc = val_drip_tsmc * monthly_div_rate

        acc_cost_0050 += monthly_invest
        val_nodrip_0050 = (val_nodrip_0050 + monthly_invest) * (1 + monthly_price_rate)
        val_drip_0050 = (val_drip_0050 + monthly_invest) * (1 + monthly_price_rate) + div_0050 + div_tsmc

        val_nodrip_tsmc = val_nodrip_tsmc * (1 + monthly_price_rate)
        val_drip_tsmc = val_drip_tsmc * (1 + monthly_price_rate)
        
        future_total_months = curr_month + m - 1
        fy = curr_year + (future_total_months // 12)
        fm = (future_total_months % 12) + 1
        
        time_lbl = f"{fy}年{fm}月" if resolution == "每月" else f"{fy}年"
        
        if resolution == "每月" or (resolution == "每年" and m % 12 == 0):
            future_data.append({
                "時間": time_lbl, 
                "總累積本金": acc_cost_0050 + acc_cost_tsmc, 
                "總無再投入": val_nodrip_0050 + val_nodrip_tsmc, 
                "總再投入": val_drip_0050 + val_drip_tsmc,
                "0050累積本金": acc_cost_0050, "0050無再投入": val_nodrip_0050, "0050再投入": val_drip_0050,
                "TSMC累積本金": acc_cost_tsmc, "TSMC無再投入": val_nodrip_tsmc, "TSMC再投入": val_drip_tsmc
            })
            
    df_future = pd.DataFrame(future_data)
    
    st.markdown('<div id="future-chart-bg"></div>', unsafe_allow_html=True)
    
    fig_future = go.Figure()

    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['總累積本金'], mode='lines', fill='tozeroy', name='[總計] 累積本金', legendgroup="Total", legendgrouptitle_text="全庫存總計", line=dict(color='rgba(149, 165, 166, 0.7)', width=2)))
    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['總無再投入'], mode='lines', fill='tonexty', name='[總計] 單純成長 (股息領出)', legendgroup="Total", line=dict(color='rgba(230, 126, 34, 0.7)', width=2)))
    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['總再投入'], mode='lines', fill='tonexty', name='[總計] 股息再投入', legendgroup="Total", line=dict(color='rgba(241, 196, 15, 0.9)', width=3)))

    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['0050累積本金'], mode='lines', name='[0050] 累積本金', legendgroup="0050", legendgrouptitle_text="0050 (含定期定額)", line=dict(color='#85c1e9', width=2, dash='dot')))
    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['0050無再投入'], mode='lines', name='[0050] 單純成長', legendgroup="0050", line=dict(color='#3498db', width=2, dash='dash')))
    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['0050再投入'], mode='lines', name='[0050] 股息再投入 (含台積電股息挹注)', legendgroup="0050", line=dict(color='#00e5ff', width=2)))

    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['TSMC累積本金'], mode='lines', name='[台積電] 累積本金', legendgroup="TSMC", legendgrouptitle_text="台積電 (單純放著長)", line=dict(color='#f1948a', width=2, dash='dot')))
    fig_future.add_trace(go.Scatter(x=df_future['時間'], y=df_future['TSMC再投入'], mode='lines', name='[台積電] 市值成長 (股息已移轉0050)', legendgroup="TSMC", line=dict(color='#ff4b4b', width=2)))

    fig_future = style_fig(fig_future, f"多重資產軌跡投影 (點擊圖例可隨時開關線條)", height=850)
    
    if resolution == "每年":
        fig_future.update_xaxes(type='category')
        
    fig_future.update_layout(
        # 移除 font=dict(color="#ffffff", size=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=70, b=60),
        legend=dict(
            groupclick="toggleitem",
            # 移除圖例的白色字體限制，只保留大小
            grouptitlefont=dict(size=18)
        )
    )
    
    fig_future.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{x}}</b></span><br><span style='color:{C_VAL}'><b>金額: NT$ %{{y:,.0f}}</b></span><extra></extra>")
    # 移除 theme=None
    st.plotly_chart(fig_future, use_container_width=True)

    st.divider()

    # ==========================================
    # 🎯 區塊三：紀律引擎透視
    # ==========================================
    st.markdown("### 💸 紀律引擎：0050 定期定額透視")
    c3_1, c3_2 = st.columns(2)
    
    est_dividends = current_0050_cost * (div_yield / 100)
    free_shares = (est_dividends / market_price_0050) if market_price_0050 > 0 else 0

    with c3_1:
        st.markdown(create_colorful_card("平均持倉成本 vs 現價", f"NT$ {avg_cost_0050:,.2f}", "📉", "purple"), unsafe_allow_html=True)
        diff_pct = ((market_price_0050 - avg_cost_0050) / avg_cost_0050 * 100) if avg_cost_0050 > 0 else 0
        color = "#ff4b4b" if diff_pct > 0 else "#09ab3b"
        st.markdown(f"<p style='text-align: center; color: {color}; font-weight: bold;'>現價落差: {diff_pct:+.2f}% (市場價 {market_price_0050:,.2f})</p>", unsafe_allow_html=True)

    with c3_2:
        st.markdown(create_colorful_card("累積預估配息 (換算免費零股)", f"{free_shares:,.0f} 股", "🥚", "purple"), unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: #a0a5b1; font-weight: bold;'>預估配息總額: NT$ {est_dividends:,.0f}</p>", unsafe_allow_html=True)
