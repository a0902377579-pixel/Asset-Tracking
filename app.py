import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
import datetime
import cv2
from PIL import Image
import os
import urllib.request
import time

# ==========================================
# 1. 頁面基本配置與頂級美化 CSS
# ==========================================
st.set_page_config(
    page_title="個人旗艦資產工作站", 
    layout="wide", 
    page_icon="💎", 
    initial_sidebar_state="expanded"
)

# ==========================================
# 🔒 系統安全門神：並排雙通道解鎖 (隱藏密碼版)
# ==========================================
@st.cache_resource
def load_face_models():
    yunet_path = "face_detection_yunet_2023mar.onnx"
    sface_path = "face_recognition_sface_2021dec.onnx"
    try:
        if not os.path.exists(yunet_path):
            urllib.request.urlretrieve("https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx", yunet_path)
        if not os.path.exists(sface_path):
            urllib.request.urlretrieve("https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx", sface_path)

        detector = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320))
        recognizer = cv2.FaceRecognizerSF.create(sface_path, "")
        my_feature = np.load("my_feature.npy")
        return detector, recognizer, my_feature
    except Exception as e:
        return None, None, None

def check_password():
    def password_entered():
        if st.session_state.get("password_input") == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            if "password_input" in st.session_state:
                del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("<h1 style='text-align: center; margin-top: 10vh;'>🔒 個人旗艦資產工作站</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a0a5b1; margin-bottom: 30px;'>請進行身份驗證以解鎖終端</p>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 1], gap="large")
    with col_left:
        st.markdown("### 📸 臉部辨識解鎖")
        st.caption("請允許攝影機權限，對準後點擊拍照進行比對")
        camera_img = st.camera_input("拍攝臉部進行解鎖", label_visibility="collapsed")
        if camera_img is not None:
            detector, recognizer, my_feature = load_face_models()
            if detector is None:
                st.error("⚠️ 找不到特徵檔，請確認 my_feature.npy 檔案已上傳至同目錄。")
            else:
                img = Image.open(camera_img)
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                height, width, _ = img_cv.shape
                detector.setInputSize((width, height))
                _, faces = detector.detect(img_cv)
                if faces is not None and len(faces) > 0:
                    face = faces[0]
                    face_align = recognizer.alignCrop(img_cv, face)
                    current_feature = recognizer.feature(face_align)
                    score = recognizer.match(my_feature, current_feature, cv2.FaceRecognizerSF_FR_COSINE)
                    if score >= 0.55:
                        st.success("✅ 臉部驗證成功！正在登入...")
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error(f"❌ 辨識失敗，這不是你！(相似度: {score:.2f})")
                else:
                    st.warning("⚠️ 畫面中偵測不到人臉，請確認光源並正對鏡頭。")
    with col_right:
        st.markdown("### 🔑 手動密碼登入")
        st.caption("備用通道，輸入正確密碼後按 Enter")
        st.text_input("輸入密碼", type="password", on_change=password_entered, key="password_input", placeholder="輸入密碼...")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ 密碼錯誤")
    return False

if not check_password():
    st.stop()

# ==========================================
# (🚀 主程式開始) 每 60 秒刷新以保持資料庫同步
# ==========================================
st_autorefresh(interval=60000, key="realtime_data_refresher")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    @property --border-angle { syntax: '<angle>'; inherits: false; initial-value: 0deg; }
    @keyframes spin-border { to { --border-angle: 360deg; } }
    @keyframes sweep-light { 0% { background-position: 15% 50%; } 50% { background-position: 85% 50%; } 100% { background-position: 15% 50%; } }
    div[data-testid="stFullScreenFrame"]:has(div[data-testid="stPlotlyChart"]) { background-color: #0a1128 !important; border-radius: 12px !important; }
    section[data-testid="stSidebar"] div[data-testid="stTabs"] { position: relative !important; border-radius: 14px !important; padding: 10px !important; box-shadow: 0 0 20px rgba(241, 39, 17, 0.45) !important; margin-top: 5px !important; margin-bottom: 20px !important; background: transparent !important; }
    section[data-testid="stSidebar"] div[data-testid="stTabs"]::before { content: ""; position: absolute; inset: 0; border-radius: 14px; padding: 4px; background: conic-gradient(from var(--border-angle), #f12711, #FC466B, #ff8008, #f12711); -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; mask-composite: exclude; animation: spin-border 3.5s linear infinite; pointer-events: none; z-index: 10; }
    div[data-baseweb="tab-list"] { display: flex !important; width: 100% !important; gap: 15px !important; background-color: transparent !important; border-bottom: none !important; flex-wrap: wrap !important; }
    div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] { display: none !important; background-color: transparent !important; }
    button[data-baseweb="tab"] { flex: 1 1 auto !important; min-width: 220px !important; background-color: #1e2128 !important; border-radius: 50px !important; padding: 12px 0px !important; border: 1px solid rgba(255, 255, 255, 0.05) !important; margin: 0 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important; }
    button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p { width: 100%; text-align: center; font-size: 18px !important; font-weight: 600 !important; color: #a0a5b1 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%) !important; border: 1px solid rgba(255, 255, 255, 0.3) !important; box-shadow: 0 6px 15px rgba(52, 152, 219, 0.5) !important; }
    button[data-baseweb="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p { color: white !important; font-weight: bold !important; }
    div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    div[data-testid="stRadio"] > div { gap: 10px; background: #111318 !important; padding: 6px 10px; border-radius: 50px; display: inline-flex; border: 1px solid rgba(255,255,255,0.05); box-shadow: inset 0 2px 6px rgba(0,0,0,0.5); }
    div[data-testid="stRadio"] div[role="radiogroup"] label { padding: 8px 32px !important; border-radius: 50px !important; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; background: transparent !important; margin: 0 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover { background: rgba(255,255,255,0.05) !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) { background: linear-gradient(135deg, #0a1128 0%, #0a1128 40%, #1c5276 50%, #0a1128 60%, #0a1128 100%) !important; background-size: 400% 400% !important; background-repeat: no-repeat !important; animation: sweep-light 4s ease-in-out infinite !important; box-shadow: 0 8px 20px rgba(28, 82, 118, 0.5) !important; border: 1px solid rgba(255,255,255,0.1) !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label p { color: #7f8ca6 !important; font-weight: 600 !important; font-size: 16px !important; margin: 0 !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p { color: #ffffff !important; font-weight: 900 !important; text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important; }
</style>
""", unsafe_allow_html=True)

WEEK_MAP = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
SPREADSHEET_ID = "1BButbI49PY3SIy13-zh_wDE9n6ZhLeE0mR-vxtBELYE"

# ==========================================
# 2. 核心資料讀取
# ==========================================
@st.cache_resource(ttl=3600)
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
        sh = client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"🚨 無法連線到新的試算表！\n錯誤訊息: {e}")
        return None, None
        
    try:
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
    except Exception as e: 
        st.error(f"資料處理錯誤: {e}")
        return None, None

def load_bank_data():
    client = get_gspread_client()
    if not client: return 58661.0, []
    try:
        sh = client.open_by_key(SPREADSHEET_ID)
        try: b_val = float(str(sh.worksheet("資產總覽").get_all_values()[1][11]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 58661)
        except: b_val = 58661.0
        txs = [{"日期": r[0].strip(), "類型": r[1].strip(), "金額": float(str(r[2]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 0)} for r in sh.worksheet("db_bank_ledger").get_all_values()[1:] if len(r) >= 3 and str(r[0]).strip() != ""]
        return b_val, txs
    except: return 58661.0, []

def load_stock_transactions():
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SPREADSHEET_ID)
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
    except: pass
    return pd.DataFrame()


# ==========================================
# 3. 視覺化引擎與樣式函數
# ==========================================
C_LBL = "#FFD700"; C_VAL = "#00E5FF"; C_PCT = "#00E676"  
def add_zero_baseline(fig): fig.add_hline(y=0, line_dash="dash", line_color="#FFD700", line_width=2); return fig
def style_fig(fig, title, height=500):
    fig.update_layout( height=height, font=dict(color="#ffffff"), title=dict(text=f"<b>{title}</b>", font=dict(size=22, color="#FFD700"), x=0.01, y=0.95), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hoverlabel=dict(bgcolor="rgba(25, 30, 40, 0.95)", font=dict(size=16, family="Arial, sans-serif", color="#ffffff"), bordercolor="rgba(0, 229, 255, 0.8)", namelength=-1), margin=dict(l=40, r=40, t=85, b=60), hovermode="x unified", xaxis=dict( automargin=True, showgrid=False, zeroline=False, title="", tickformat="%Y-%m-%d", showspikes=True, spikemode="across", spikedash="dash", spikecolor="#FF00FF", spikethickness=2, tickangle=-45 ), yaxis=dict( automargin=True, showgrid=True, gridcolor="rgba(128,128,128,0.2)", zeroline=True, zerolinecolor="rgba(128,128,128,0.3)", title="" ) )
    return fig

def render_neon_container(render_func, element_id, conic_colors, glow_color, padding="15px", bg_color="#0f1117"):
    bg_style = f"background: {bg_color} !important;" if bg_color != "transparent" else ""
    st.markdown(f'''<div id="{element_id}"></div><style>div[data-testid="stElementContainer"]:has(#{element_id}) + div[data-testid="stElementContainer"] {{ position: relative !important; border-radius: 14px !important; padding: {padding} !important; box-shadow: 0 0 20px {glow_color} !important; margin-top: 10px !important; margin-bottom: 30px !important; {bg_style} }} div[data-testid="stElementContainer"]:has(#{element_id}) + div[data-testid="stElementContainer"]::before {{ content: ""; position: absolute; inset: 0; border-radius: 14px; padding: 4px; background: conic-gradient(from var(--border-angle), {conic_colors}); -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; mask-composite: exclude; animation: spin-border 3.5s linear infinite; pointer-events: none; }} </style>''', unsafe_allow_html=True)
    render_func()

def apply_neon_to_next_container(element_id, conic_colors, glow_color, padding="10px", bg_color="transparent"):
    bg_style = f"background: {bg_color} !important;" if bg_color != "transparent" else ""
    st.markdown(f'''<div id="{element_id}"></div><style>div[data-testid="stElementContainer"]:has(#{element_id}) + div[data-testid="stElementContainer"] {{ position: relative !important; border-radius: 14px !important; padding: {padding} !important; box-shadow: 0 0 20px {glow_color} !important; margin-top: 5px !important; margin-bottom: 20px !important; {bg_style} }} div[data-testid="stElementContainer"]:has(#{element_id}) + div[data-testid="stElementContainer"]::before {{ content: ""; position: absolute; inset: 0; border-radius: 14px; padding: 4px; background: conic-gradient(from var(--border-angle), {conic_colors}); -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; mask-composite: exclude; animation: spin-border 3.5s linear infinite; pointer-events: none; z-index: 10; }} </style>''', unsafe_allow_html=True)

neon_styles = [ ("#ff007f, #7928ca, #0070f3, #00dfd8, #7928ca, #ff007f", "rgba(0, 223, 216, 0.45)"), ("#00f2fe, #4facfe, #00f2fe", "rgba(0, 242, 254, 0.45)"), ("#ff8008, #ffc837, #ff8008", "rgba(255, 128, 8, 0.45)"), ("#11998e, #38ef7d, #11998e", "rgba(56, 239, 125, 0.45)"), ("#FC466B, #3F5EFB, #FC466B", "rgba(252, 70, 107, 0.45)"), ("#FDBB2D, #22C1C3, #FDBB2D", "rgba(34, 193, 195, 0.45)"), ("#8E2DE2, #4A00E0, #8E2DE2", "rgba(142, 45, 226, 0.45)"), ("#00c6ff, #0072ff, #00c6ff", "rgba(0, 198, 255, 0.45)"), ("#f12711, #f5af19, #f12711", "rgba(241, 39, 17, 0.45)"), ("#654ea3, #eaafc8, #654ea3", "rgba(101, 78, 163, 0.45)"), ("#FF416C, #FF4B2B, #FF416C", "rgba(255, 65, 108, 0.45)"), ("#00B4DB, #0083B0, #00B4DB", "rgba(0, 180, 219, 0.45)"), ("#b92b27, #1565C0, #b92b27", "rgba(185, 43, 39, 0.45)"), ("#ee0979, #ff6a00, #ee0979", "rgba(238, 9, 121, 0.45)"), ("#00c3ff, #ffff1c, #00c3ff", "rgba(0, 195, 255, 0.45)"), ("#f85032, #e73827, #f85032", "rgba(248, 80, 50, 0.45)"), ("#5614B0, #DBD65C, #5614B0", "rgba(86, 20, 176, 0.45)"), ("#F09819, #EDDE5D, #F09819", "rgba(240, 152, 25, 0.45)"), ("#8A2387, #E94057, #F27121, #8A2387", "rgba(233, 64, 87, 0.45)"), ("#1D976C, #93F9B9, #1D976C", "rgba(29, 151, 108, 0.45)"), ("#3E5151, #DECBA4, #3E5151", "rgba(62, 81, 81, 0.45)") ]

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
            
    return f"""<div style="background: {bg}; background-size: 400% 400%; background-repeat: no-repeat; animation: sweep-light 4s ease-in-out infinite; border-radius: 12px; padding: 15px; box-shadow: {glow_shadow}; border: 1px solid rgba(255,255,255,0.05); min-height: 120px; height: 100%; display: flex; flex-direction: column; justify-content: center; position: relative; overflow: hidden; margin-bottom: 15px;"><p style="margin: 0; font-size: 1.1rem; color: #d1d5db; font-weight: bold; text-shadow: 0 1px 2px rgba(0,0,0,0.5); position: relative; z-index: 1;">{title}</p><p style="margin: 5px 0 0 0; font-size: clamp(1.4rem, 2vw, 2.3rem); font-weight: 900; color: {text_c}; text-shadow: 0 0 15px {text_c}50; line-height: 1.2; word-wrap: break-word; position: relative; z-index: 1;">{value_str}</p><div style="position: absolute; right: -15px; bottom: -25px; font-size: 6.5rem; opacity: 0.15; z-index: 0; transform: rotate(-15deg); pointer-events: none;">{icon}</div></div>"""

def style_profit_loss(s): return ['color: #ff4b4b; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else ('color: #09ab3b; font-weight: bold;' if isinstance(v, (int, float)) and v < 0 else '') for v in s]
def style_portfolio_row(row):
    styles = [''] * len(row)
    for i, col in enumerate(row.index):
        if col in ['各股損益', '各股損益(%)']: styles[i] = 'color: #ff4b4b; font-weight: bold;' if row[col] > 0 else ('color: #09ab3b; font-weight: bold;' if row[col] < 0 else '')
        elif col in ['即時現價', '即時漲跌幅(%)']: styles[i] = 'color: #ff4b4b; font-weight: bold;' if row['即時漲跌幅(%)'] > 0 else ('color: #09ab3b; font-weight: bold;' if row['即時漲跌幅(%)'] < 0 else '')
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
        if name not in stock_options: stock_options.insert(0, name)
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
# 5. 側邊欄：控制中心
# ==========================================
if "stock_selector" not in st.session_state: st.session_state.stock_selector = stock_options[0]
if "s_price" not in st.session_state: st.session_state.s_price = float(stock_price_dict.get(stock_options[0], 0.0))
if "s_shares" not in st.session_state: st.session_state.s_shares = 0
if "s_fee" not in st.session_state: st.session_state.s_fee = 0.0

def on_stock_change():
    sel = st.session_state.stock_selector
    st.session_state.s_price = float(stock_price_dict.get(sel, 0.0)) if sel != "其他 (手動輸入新股)" else 0.0
    calc_fee()

def calc_fee():
    shares = st.session_state.s_shares; price = st.session_state.s_price; name = st.session_state.stock_selector
    if name == "其他 (手動輸入新股)": name = st.session_state.get("s_name_input", "")
    if shares == 0 or price == 0.0: st.session_state.s_fee = 0.0; return
    cost = abs(shares) * price
    st.session_state.s_fee = float(max(20, int(cost * 0.001425 * 0.6)) + (int(cost * (0.001 if "00" in name else 0.003)) if shares < 0 else 0))

with st.sidebar:
    st.title("⚙️ 異動控制中心")
    apply_neon_to_next_container("sidebar_info_neon", "#ff007f, #00f2fe, #8E2DE2, #ff007f", "rgba(255, 0, 127, 0.45)", padding="4px", bg_color="transparent")
    st.info("💡 輸入後自動換算手續費，送出後即時更新。")
    apply_neon_to_next_container("sidebar_btn_neon", "#00b894, #00c6ff, #11998e, #00b894", "rgba(0, 184, 148, 0.45)", padding="4px", bg_color="transparent")
    
    if st.button("🔄 強制同步最新試算表資料", use_container_width=True): 
        st.cache_resource.clear()
        st.rerun()

    st.divider()
    apply_neon_to_next_container("sidebar_tabs_neon", "#f12711, #FC466B, #ff8008, #f12711", "rgba(241, 39, 17, 0.45)", padding="8px", bg_color="transparent")
    
    tab_bank, tab_stock = st.tabs(["🏦 銀行金流", "📈 股票交易"])
    with tab_bank:
        st.markdown("### 新增銀行金流")
        if "bank_confirm" not in st.session_state: st.session_state.bank_confirm = False
        is_locked = st.session_state.bank_confirm
        rec_date = st.date_input("入帳日期", value=datetime.date.today(), max_value=datetime.date.today(), key="bank_date", disabled=is_locked)
        rec_type = st.selectbox("異動類型", ["現金", "跨行轉", "轉帳提", "委代入", "證券款", "電匯", "定期定額"], key="bank_type", disabled=is_locked)
        
        # 🚀 終極更新：動態顯示定期定額專屬欄位
        amount = st.number_input("扣款總額" if rec_type == "定期定額" else "金額 (系統將自動判斷正負)", min_value=0.0, step=100.0, key="bank_amount", disabled=is_locked)
        
        if rec_type == "定期定額":
            st.info("💡 系統將自動同步寫入「股票交易」明細 (預設標的: 元大台灣0050)")
            sip_price = st.number_input("買入價格 (成交單價)", min_value=0.0, step=0.01, key="sip_price", disabled=is_locked)
            sip_shares = st.number_input("實際買入股數", min_value=0, step=1, value=0, key="sip_shares", disabled=is_locked)
        else:
            sip_price = 0.0
            sip_shares = 0

        action_container = st.empty()
        if not st.session_state.bank_confirm:
            if action_container.button("寫入金流紀錄", use_container_width=True, disabled=(amount == 0), key="bank_submit_btn"): st.session_state.bank_confirm = True; st.rerun()
        else:
            if rec_type == "定期定額":
                action_container.warning(f"⚠️ 確定寫入定期定額嗎？\n\n- **日期**: {rec_date.strftime('%Y/%m/%d')}\n- **扣款總額**: NT$ {amount:,.0f}\n- **買入單價**: {sip_price}\n- **買入股數**: {sip_shares} 股")
            else:
                action_container.warning(f"⚠️ 請問確定要寫入此筆銀行金流嗎？\n\n- **日期**: {rec_date.strftime('%Y/%m/%d')}\n- **類型**: {rec_type}\n- **金額**: NT$ {amount:,.0f}")
                
            c_yes, c_no = action_container.columns(2)
            with c_yes:
                if st.button("✅ 確認寫入", use_container_width=True, key="bank_yes"):
                    try:
                        sh = get_gspread_client().open_by_key(SPREADSHEET_ID)
                        # 1. 寫入銀行流水 (扣款記錄負數)
                        sh.worksheet("db_bank_ledger").append_row([rec_date.strftime('%Y/%m/%d'), rec_type, amount if rec_type in ["現金", "跨行轉", "委代入", "電匯"] else -amount], value_input_option="USER_ENTERED")
                        
                        # 2. 如果是定期定額，連動寫入股票交易明細
                        if rec_type == "定期定額" and sip_shares > 0:
                            fee = max(0, amount - (sip_price * sip_shares))
                            # 股票交易欄位: [日期, 標的, 股數, 單價, 手續費, 單筆總價]
                            sh.worksheet("db_stock_transactions").append_row([rec_date.strftime('%Y/%m/%d'), "元大台灣0050", sip_shares, sip_price, fee, amount], value_input_option="USER_ENTERED")
                            
                        st.cache_resource.clear()
                        st.session_state.bank_confirm = False; st.success("紀錄成功寫入與同步！"); st.rerun()
                    except Exception as e: st.error(f"寫入失敗: {e}")
            with c_no:
                if st.button("❌ 取消", use_container_width=True, key="bank_no"): st.session_state.bank_confirm = False; st.rerun()
                
    with tab_stock:
        st.markdown("### 新增股票交易")
        if "stock_confirm" not in st.session_state: st.session_state.stock_confirm = False
        is_stock_locked = st.session_state.stock_confirm
        selected_stock = st.selectbox("選擇操作標的", stock_options, key="stock_selector", on_change=on_stock_change, disabled=is_stock_locked)
        if selected_stock == "其他 (手動輸入新股)": st.text_input("輸入新股票名稱", key="s_name_input", on_change=calc_fee, disabled=is_stock_locked)
        s_date = st.date_input("交易日期", value=datetime.date.today(), max_value=datetime.date.today(), disabled=is_stock_locked)
        st.number_input("股數 (買入為正，賣出為負)", step=1, key="s_shares", on_change=calc_fee, disabled=is_stock_locked)
        st.number_input("成交單價", step=0.1, key="s_price", on_change=calc_fee, disabled=is_stock_locked)
        st.number_input("手續費/稅金 (已自動試算中信費率)", step=1.0, key="s_fee", disabled=is_stock_locked)
        
        current_shares, current_price, current_fee = st.session_state.s_shares, st.session_state.s_price, st.session_state.s_fee
        st.markdown("""<style>.est-box { padding: 12px 15px; border-radius: 8px; font-weight: 900; white-space: nowrap; font-size: 16px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); } .est-blue { background-color: #74b9ff !important; border-left: 6px solid #0984e3 !important; color: #0c2461 !important; } .est-green { background-color: #55efc4 !important; border-left: 6px solid #00b894 !important; color: #004d40 !important; } .est-gray { background-color: #dfe6e9 !important; border-left: 6px solid #636e72 !important; color: #2d3436 !important; } .est-blue *, .est-green *, .est-gray * { color: inherit !important; }</style>""", unsafe_allow_html=True)
        if current_shares > 0: st.markdown(f'<div class="est-box est-blue">💵 預估扣款: NT$ {round((current_shares * current_price) + current_fee):,.0f}</div>', unsafe_allow_html=True)
        elif current_shares < 0: st.markdown(f'<div class="est-box est-green">💰 預估入帳: NT$ {round(abs(current_shares * current_price) - current_fee):,.0f}</div>', unsafe_allow_html=True)
        else: st.markdown('<div class="est-box est-gray">💡 預估交割: NT$ 0</div>', unsafe_allow_html=True)
        
        name_check = st.session_state.get("s_name_input", "") if selected_stock == "其他 (手動輸入新股)" else selected_stock
        stock_action_container = st.empty()
        if not st.session_state.stock_confirm:
            if stock_action_container.button("寫入股票紀錄", use_container_width=True, disabled=(current_shares == 0 or not name_check.strip())): st.session_state.stock_confirm = True; st.rerun()
        if st.session_state.stock_confirm:
            total_amt_check = round((current_shares * current_price) + st.session_state.s_fee)
            stock_action_container.warning(f"⚠️ 請問確定要寫入此筆股票交易嗎？\n\n- **日期**: {s_date.strftime('%Y/%m/%d')}\n- **標的**: {name_check}\n- **股數**: {current_shares:,}\n- **單價**: {current_price}\n- **金額**: NT$ {total_amt_check:,.0f}")
            sc_yes, sc_no = stock_action_container.columns(2)
            with sc_yes:
                if st.button("✅ 確認寫入", use_container_width=True, key="stock_yes"):
                    try:
                        sh = get_gspread_client().open_by_key(SPREADSHEET_ID)
                        sh.worksheet("db_stock_transactions").append_row([s_date.strftime('%Y/%m/%d'), name_check, current_shares, current_price, st.session_state.s_fee, total_amt_check], value_input_option="USER_ENTERED")
                        st.cache_resource.clear()
                        st.session_state.stock_confirm = False; st.success("股票紀錄成功寫入！"); st.rerun()
                    except Exception as e: st.error(f"寫入失敗: {e}")
            with sc_no:
                if st.button("❌ 取消寫入", use_container_width=True, key="stock_no"): st.session_state.stock_confirm = False; st.rerun()

# ==========================================
# 主畫面開始
# ==========================================
st.title("💼 個人旗艦資產工作站 ☁️")
tz_tw = datetime.timezone(datetime.timedelta(hours=8))
st.markdown(f"##### 🚀 終極數據戰情室 | 全方位投資決策系統 (V4.3 精準股數版 - 頁面讀取時間: {datetime.datetime.now(tz_tw).strftime('%H:%M:%S')})")

tab1, tab2, tab3 = st.tabs(["📊 總覽儀表板", "🌌 數據戰情室", "🎯 定期定額與願景"])

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
            df_display = df_h.rename(columns={"stock_name":"股票名稱", "shares":"總股數", "avg_cost":"平均成本", "total_cost":"總成本", "current_price":"即時現價", "market_value":"即時市值", "change_pct":"即時漲跌幅(%)"})[["股票名稱", "總股數", "平均成本", "總成本", "即時現價", "即時市值", "各股損益", "即時漲跌幅(%)", "各股損益(%)"]]
            styled_df = df_display.style.apply(style_portfolio_row, axis=1).format({"總股數": "{:,.0f}", "平均成本": "{:,.2f}", "總成本": "{:,.0f}", "即時現價": "{:,.2f}", "即時市值": "{:,.0f}", "各股損益": "{:+,.0f}", "即時漲跌幅(%)": "{:+.2f}%", "各股損益(%)": "{:+.2f}%"})
            render_neon_container(lambda: st.dataframe(styled_df, use_container_width=True, hide_index=True), "df_portfolio", neon_styles[0][0], neon_styles[0][1], padding="6px", bg_color="transparent")
            
    st.divider()
    col_hist, col_bank = st.columns(2)
    with col_hist:
        st.subheader("📜 歷史每日結算報表")
        if df_hist is not None:
            df_hist_filtered = df_hist[df_hist['星期'].isin(['一', '二', '三', '四', '五'])].copy()
            df_hist_filtered['日期'] = df_hist_filtered['日期_顯示']
            df_hist_display = df_hist_filtered.drop(columns=["單日損益變化", "單日漲跌幅(%)", "最高市值", "市值回撤", "20日均線", "真實日期", "日期_顯示", "星期", "0050累計", "台積電累計", "總損益_str", "單日漲跌幅_str"], errors='ignore')[::-1]
            styled_hist = df_hist_display.style.apply(style_profit_loss, subset=["總投資損益", "0050每日損益", "台積電每日損益", "總損益(%)"]).format({"總累積成本": "{:,.0f}", "總市值": "{:,.0f}", "總投資損益": "{:+,.0f}", "0050每日損益": "{:+,.0f}", "台積電每日損益": "{:+,.0f}", "總損益(%)": "{:+.2f}%"})
            render_neon_container(lambda: st.dataframe(styled_hist, use_container_width=True, hide_index=True), "df_history", neon_styles[0][0], neon_styles[0][1], padding="6px", bg_color="transparent")
        else:
            st.info("目前暫無歷史紀錄。")
            
    with col_bank:
        st.subheader("🏦 銀行帳戶資金流水明細")
        if df_txs is not None:
            df_bank_display = df_txs[::-1][["日期_顯示", "類型", "金額"]].copy().rename(columns={"日期_顯示": "日期"})
            styled_bank = df_bank_display.style.apply(style_profit_loss, subset=["金額"]).format({"金額": "{:+,.0f}"})
            render_neon_container(lambda: st.dataframe(styled_bank, use_container_width=True, hide_index=True, column_config={"類型": st.column_config.TextColumn("類型", alignment="right")}), "df_bank", neon_styles[0][0], neon_styles[0][1], padding="6px", bg_color="transparent")
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
            fig1.update_traces(hovertemplate=f"<span style='color:{C_LBL}'><b>%{{label}}</b></span><br><span style='color:{
