import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==========================================
# 1. 頁面基本配置 (極致寬螢幕與暗黑主題預設)
# ==========================================
st.set_page_config(page_title="個人旗艦資產工作站", layout="wide", page_icon="💎", initial_sidebar_state="collapsed")
st_autorefresh(interval=1200000, key="realtime_data_refresher")

# --- 注入華麗的 CSS 背景與卡片特效 ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e1e1e; border-radius: 8px 8px 0px 0px; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #4CAF50; color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

WEEK_MAP = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
SPREADSHEET_NAME = "個人資產" 

# ==========================================
# 2. 核心資料讀取 (維持最穩定的 gspread 寫法)
# ==========================================
@st.cache_resource(ttl=600)
def get_gspread_client():
    try:
        return gspread.authorize(Credentials.from_service_account_info(dict(st.secrets["gcp_json"]), scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    except Exception as e:
        st.error(f"金鑰讀取失敗: {e}")
        return None

def load_sheet_data():
    client = get_gspread_client()
    if not client: return None, None
    try:
        sh = client.open(SPREADSHEET_NAME)
        def parse_num(v):
            try: return float(str(v).replace('NT$', '').replace('$', '').replace(',', '').replace('%', '').strip())
            except: return 0.0

        # 資產總覽
        ws_summary = sh.worksheet("資產總覽")
        s_rows = ws_summary.get_all_values()
        holdings, total_assets, total_cost, total_profit = [], 0.0, 0.0, 0.0
        if len(s_rows) > 1:
            price_map = {sr[7].strip(): parse_num(sr[8]) for sr in s_rows[1:] if len(sr) >= 10 and sr[7]}
            change_map = {sr[7].strip(): parse_num(str(sr[9]).replace('%', '')) for sr in s_rows[1:] if len(sr) >= 10 and sr[7]}
            
            for sr in s_rows[1:]:
                if len(sr) >= 6 and sr[0]:
                    name, shares, cost, avg_cost, profit, m_val = sr[0].strip(), parse_num(sr[1]), parse_num(sr[2]), parse_num(sr[3]), parse_num(sr[4]), parse_num(sr[5])
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

        # 每日損益追蹤
        ws_overview = sh.worksheet("每日損益追蹤")
        hist_data = [{"日期": r[0], "總累積成本": parse_num(r[5]), "總市值": parse_num(r[6]), "總投資損益": parse_num(r[7]), "0050每日損益": parse_num(r[12]), "台積電每日損益": parse_num(r[13])} for r in ws_overview.get_all_values()[1:] if len(r) >= 14 and str(r[0]).strip() != ""]
        return {"total_assets": total_assets, "total_cost": total_cost, "total_profit": total_profit, "profit_rate": profit_rate, "holdings": holdings}, hist_data
    except Exception as e:
        return None, None

def load_bank_data():
    client = get_gspread_client()
    if not client: return 58661.0, []
    try:
        sh = client.open(SPREADSHEET_NAME)
        try: b_val = float(str(sh.worksheet("資產總覽").get_all_values()[1][11]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 58661)
        except: b_val = 58661.0
        
        txs = []
        for r in sh.worksheet("db_bank_ledger").get_all_values()[1:]:
            if len(r) >= 4 and str(r[0]).strip() != "":
                try: amt = float(str(r[2]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 0)
                except: amt = 0.0
                txs.append({"日期": r[0], "類型": r[1], "金額": amt, "備註": r[3]})
        return b_val, txs
    except: return 58661.0, []

# ==========================================
# 3. 視覺化引擎 (Plotly 華麗格式化函數)
# ==========================================
def style_fig(fig, title):
    """將圖表套用科技感主題，移除多餘格線與背景"""
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=20, color="#ffffff")),
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="rgba(20, 20, 20, 0.95)", font_size=15, font_family="Arial, sans-serif", bordercolor="#4CAF50"),
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", zeroline=True, zerolinecolor="rgba(255,255,255,0.2)")
    )
    return fig

def create_colorful_card(title, value_str, icon="", is_profit=False, num_val=None):
    if is_profit and num_val is not None:
        bg, glow, text_c = "linear-gradient(135deg, #1e2128 0%, #13151a 100%)", ("#ff4b4b" if num_val>0 else "#09ab3b"), ("#ff4b4b" if num_val>0 else "#09ab3b")
        glow_shadow = f"0 8px 20px rgba({(255,75,75) if num_val>0 else (9,171,59)}, 0.4)"
    else:
        bg, glow_shadow, text_c = "linear-gradient(135deg, #2b5876 0%, #4e4376 100%)", "0 8px 20px rgba(78, 67, 118, 0.6)", "#ffffff"
    
    return f"""
    <div style="background: {bg}; border-radius: 12px; padding: 20px; box-shadow: {glow_shadow}; border: 1px solid rgba(255,255,255,0.05); height: 130px; position: relative; overflow: hidden; margin-bottom: 15px;">
        <p style="margin: 0; font-size: 1.1rem; color: #a0a5b1; font-weight: bold;">{title}</p>
        <p style="margin: 5px 0 0 0; font-size: 2rem; font-weight: 900; color: {text_c}; text-shadow: 0 0 10px {text_c}40;">{value_str}</p>
        <div style="position: absolute; right: -10px; bottom: -20px; font-size: 5.5rem; opacity: 0.15; z-index: 0; transform: rotate(-10deg);">{icon}</div>
    </div>
    """

# ==========================================
# 主畫面架構
# ==========================================
st.title("💼 個人旗艦資產工作站 ☁️")
st.markdown("##### 🚀 終極數據大廳 | 深度可視化分析系統")

bank_balance, txs = load_bank_data()
dashboard_data, hist_data = load_sheet_data()

tab1, tab2, tab3, tab4 = st.tabs(["📊 總覽儀表板", "🌌 終極數據戰情室 (21種圖表)", "📜 歷史報表", "🏦 金流明細"])

# ------------------------------------------
# 分頁 1：總覽儀表板
# ------------------------------------------
with tab1:
    if dashboard_data:
        d = dashboard_data
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(create_colorful_card("總市值", f"NT$ {d['total_assets']:,.0f}", "💎"), unsafe_allow_html=True)
        c2.markdown(create_colorful_card("總投入成本", f"NT$ {d['total_cost']:,.0f}", "📥"), unsafe_allow_html=True)
        c3.markdown(create_colorful_card("銀行活存餘額", f"NT$ {bank_balance:,.0f}", "🏦"), unsafe_allow_html=True)
        c4.markdown(create_colorful_card("帳面總損益", f"{d['total_profit']:+,.0f}", "🔥", True, d['total_profit']), unsafe_allow_html=True)
        c5.markdown(create_colorful_card("總獲利率 (%)", f"{d['profit_rate']:+.2f}%", "📈", True, d['profit_rate']), unsafe_allow_html=True)

        if d.get("holdings"):
            df_h = pd.DataFrame(d["holdings"])
            df_h["各股損益(%)"] = df_h.apply(lambda x: (x["各股損益"]/x["total_cost"]*100) if x["total_cost"]>0 else 0, axis=1)
            st.subheader("📋 投資組合即時明細")
            df_display = df_h.rename(columns={"stock_name":"股票名稱", "shares":"總股數", "avg_cost":"平均成本", "total_cost":"總成本", "current_price":"即時現價", "market_value":"即時市值", "change_pct":"即時漲跌幅(%)"})[["股票名稱", "總股數", "平均成本", "總成本", "即時現價", "即時市值", "各股損益", "即時漲跌幅(%)", "各股損益(%)"]]
            
            def color_market(row):
                return ['color: #ff4b4b; font-weight: bold;' if val > 0 else ('color: #09ab3b; font-weight: bold;' if val < 0 else '') if col in ["即時現價", "各股損益", "各股損益(%)", "即時漲跌幅(%)"] and pd.notna(val) and isinstance(val, (int, float)) else '' for col, val in row.items()]
            
            st.dataframe(df_display.style.apply(color_market, axis=1).format({"總股數": "{:,.0f}", "平均成本": "{:,.2f}", "總成本": "{:,.0f}", "即時現價": "{:,.2f}", "即時市值": "{:,.0f}", "各股損益": "{:+,.0f}", "即時漲跌幅(%)": "{:+.2f}%", "各股損益(%)": "{:+.2f}%"}), use_container_width=True, hide_index=True)

# ------------------------------------------
# 分頁 2：🌌 終極數據戰情室 (全客製中文標籤)
# ------------------------------------------
with tab2:
    st.markdown("### 🔍 展區一：資產版圖與持股透視")
    if dashboard_data and dashboard_data.get("holdings"):
        df_h = pd.DataFrame(dashboard_data["holdings"])
        df_h["各股損益(%)"] = df_h.apply(lambda x: (x["各股損益"]/x["total_cost"]*100) if x["total_cost"]>0 else 0, axis=1)
        
        c2_1, c2_2, c2_3 = st.columns(3)
        with c2_1:
            fig1 = px.pie(names=['股票總市值', '銀行帳戶餘額'], values=[dashboard_data["total_assets"], bank_balance], hole=0.5, color_discrete_sequence=['#3498db', '#f1c40f'])
            fig1.update_traces(hovertemplate="<b>%{label}</b><br>金額: NT$ %{value:,.0f}<br>佔比: %{percent}<extra></extra>", textinfo='label+percent', textfont_size=14)
            st.plotly_chart(style_fig(fig1, "1. 總資產水庫配置"), use_container_width=True)
            
        with c2_2:
            fig2 = px.pie(df_h, names='stock_name', values='market_value', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig2.update_traces(hovertemplate="<b>%{label}</b><br>市值: NT$ %{value:,.0f}<br>佔比: %{percent}<extra></extra>", textinfo='label+percent')
            st.plotly_chart(style_fig(fig2, "2. 個股市值佔比 (Donut)"), use_container_width=True)

        with c2_3:
            fig3 = px.treemap(df_h, path=['stock_name'], values='market_value', color='各股損益(%)', color_continuous_scale=['#09ab3b', '#222222', '#ff4b4b'], color_continuous_midpoint=0)
            fig3.update_traces(hovertemplate="<b>%{label}</b><br>市值: NT$ %{value:,.0f}<br>帳面損益: %{color:+.2f}%<extra></extra>", textfont=dict(size=18, color="white"))
            st.plotly_chart(style_fig(fig3, "3. 板塊熱力圖 (大小=市值, 顏色=賺賠)"), use_container_width=True)

        c2_4, c2_5 = st.columns([1, 1])
        with c2_4:
            fig4 = go.Figure(go.Waterfall(
                orientation="v", measure=["relative"]*len(df_h) + ["total"],
                x=df_h['stock_name'].tolist() + ["淨損益總計"], y=df_h['各股損益'].tolist() + [dashboard_data["total_profit"]],
                decreasing={"marker":{"color":"#09ab3b"}}, increasing={"marker":{"color":"#ff4b4b"}}, totals={"marker":{"color":"#3498db"}}
            ))
            fig4.update_traces(hovertemplate="<b>%{x}</b><br>貢獻金額: NT$ %{y:+,.0f}<extra></extra>", texttemplate="%{y:+,.0s}", textposition="outside")
            st.plotly_chart(style_fig(fig4, "4. 各股獲利貢獻瀑布圖"), use_container_width=True)

        with c2_5:
            fig5 = go.Figure(data=[
                go.Bar(name='總投入成本', x=df_h['stock_name'], y=df_h['total_cost'], marker_color='#9b59b6'),
                go.Bar(name='當前總市值', x=df_h['stock_name'], y=df_h['market_value'], marker_color='#f1c40f')
            ])
            fig5.update_traces(hovertemplate="<b>%{x}</b><br>金額: NT$ %{y:,.0f}<extra></extra>")
            fig5.update_layout(barmode='group')
            st.plotly_chart(style_fig(fig5, "5. 個股成本 vs 現值對比"), use_container_width=True)

    st.divider()
    st.markdown("### 📈 展區二：時間維度與趨勢擴張")
    if hist_data:
        df_hist = pd.DataFrame(hist_data)
        df_hist["真實日期"] = pd.to_datetime(df_hist["日期"])
        df_hist = df_hist.sort_values("真實日期")
        df_hist["ROI(%)"] = (df_hist["總投資損益"] / df_hist["總累積成本"]) * 100
        df_hist["單日損益變化"] = df_hist["總投資損益"].diff().fillna(0)
        df_hist["最高市值"] = df_hist["總市值"].cummax()
        df_hist["市值回撤"] = df_hist["總市值"] - df_hist["最高市值"]
        df_hist["20日均線"] = df_hist["總市值"].rolling(window=20, min_periods=1).mean()

        c2_6, c2_7 = st.columns(2)
        with c2_6:
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['總投資損益'], mode='lines', fill='tozeroy', line=dict(color='#ff4b4b', width=3), name="累積損益"))
            fig6.update_traces(hovertemplate="<b>日期: %{x}</b><br>累積損益: NT$ %{y:+,.0f}<extra></extra>")
            st.plotly_chart(style_fig(fig6, "6. 總投資累積損益面積圖"), use_container_width=True)
            
        with c2_7:
            fig7 = go.Figure()
            fig7.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['總市值'], mode='lines', name='總市值', line=dict(color='#2ecc71', width=3)))
            fig7.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['20日均線'], mode='lines', name='20日均線', line=dict(color='#f39c12', width=2, dash='dot')))
            fig7.update_traces(hovertemplate="<b>日期: %{x}</b><br>數值: NT$ %{y:,.0f}<extra></extra>")
            fig7.update_layout(hovermode="x unified")
            st.plotly_chart(style_fig(fig7, "7. 總市值與 20 日均線乖離"), use_container_width=True)

        c2_8, c2_9 = st.columns(2)
        with c2_8:
            fig8 = go.Figure()
            fig8.add_trace(go.Bar(x=df_hist['真實日期'], y=df_hist['0050每日損益'], name='0050', marker_color='#3498db'))
            fig8.add_trace(go.Bar(x=df_hist['真實日期'], y=df_hist['台積電每日損益'], name='台積電', marker_color='#e74c3c'))
            fig8.update_traces(hovertemplate="<b>日期: %{x}</b><br>部位損益: NT$ %{y:+,.0f}<extra></extra>")
            fig8.update_layout(barmode='relative', hovermode="x unified")
            st.plotly_chart(style_fig(fig8, "8. 每日損益部位貢獻疊加"), use_container_width=True)
            
        with c2_9:
            fig9 = px.scatter(df_hist, x="總累積成本", y="總市值", color="ROI(%)", color_continuous_scale="Turbo", size_max=10)
            fig9.add_shape(type="line", x0=df_hist["總累積成本"].min(), y0=df_hist["總累積成本"].min(), x1=df_hist["總累積成本"].max(), y1=df_hist["總累積成本"].max(), line=dict(color="rgba(255,255,255,0.5)", dash="dash"))
            fig9.update_traces(hovertemplate="<b>總成本: NT$ %{x:,.0f}</b><br>總市值: NT$ %{y:,.0f}<br>ROI: %{marker.color:+.2f}%<extra></extra>", marker=dict(size=8, opacity=0.8))
            st.plotly_chart(style_fig(fig9, "9. 資產擴張趨勢散點圖 (虛線為損益兩平點)"), use_container_width=True)

        st.divider()
        st.markdown("### ⚠️ 展區三：風險回撤與規律矩陣")
        c2_10, c2_11, c2_12 = st.columns(3)
        with c2_10:
            vol_colors = ['#ff4b4b' if val > 0 else '#09ab3b' for val in df_hist['單日損益變化']]
            fig10 = go.Figure(go.Bar(x=df_hist['真實日期'], y=df_hist['單日損益變化'], marker_color=vol_colors))
            fig10.update_traces(hovertemplate="<b>日期: %{x}</b><br>單日波動: NT$ %{y:+,.0f}<extra></extra>")
            st.plotly_chart(style_fig(fig10, "10. 單日總損益波動柱狀圖"), use_container_width=True)
            
        with c2_11:
            fig11 = go.Figure(go.Scatter(x=df_hist['真實日期'], y=df_hist['市值回撤'], fill='tozeroy', mode='lines', line=dict(color='#e67e22', width=2)))
            fig11.update_traces(hovertemplate="<b>日期: %{x}</b><br>距離新高回撤: NT$ %{y:,.0f}<extra></extra>")
            st.plotly_chart(style_fig(fig11, "11. 歷史最大回撤 (Drawdown)"), use_container_width=True)
            
        with c2_12:
            win_days = len(df_hist[df_hist['單日損益變化'] > 0])
            lose_days = len(df_hist[df_hist['單日損益變化'] < 0])
            fig12 = px.pie(names=['上漲天數', '下跌天數'], values=[win_days, lose_days], hole=0.6, color_discrete_sequence=['#ff4b4b', '#09ab3b'])
            fig12.update_traces(hovertemplate="<b>%{label}</b><br>天數: %{value} 天<br>勝率: %{percent}<extra></extra>", textinfo='label+percent')
            st.plotly_chart(style_fig(fig12, "12. 歷史操作日勝率"), use_container_width=True)

        c2_13, c2_14 = st.columns([1, 1])
        with c2_13:
            df_hist["星期"] = df_hist["真實日期"].dt.weekday.map(WEEK_MAP)
            dow_avg = df_hist.groupby("星期")["單日損益變化"].mean().reindex(['一', '二', '三', '四', '五']).reset_index()
            fig13 = go.Figure(go.Bar(x=dow_avg['星期'], y=dow_avg['單日損益變化'], marker_color=['#ff4b4b' if v>0 else '#09ab3b' for v in dow_avg['單日損益變化']]))
            fig13.update_traces(hovertemplate="<b>星期%{x}</b><br>平均波動: NT$ %{y:+,.0f}<extra></extra>")
            st.plotly_chart(style_fig(fig13, "13. 星期別平均波動分析"), use_container_width=True)

        with c2_14:
            fig14 = go.Figure()
            fig14.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['0050每日損益'].cumsum(), mode='lines', name='0050 累計', line=dict(color='#3498db')))
            fig14.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['台積電每日損益'].cumsum(), mode='lines', name='台積電 累計', line=dict(color='#e74c3c')))
            fig14.update_traces(hovertemplate="<b>日期: %{x}</b><br>累計貢獻: NT$ %{y:+,.0f}<extra></extra>")
            fig14.update_layout(hovermode="x unified")
            st.plotly_chart(style_fig(fig14, "14. 雙引擎累計獲利賽跑"), use_container_width=True)

    st.divider()
    st.markdown("### 🏦 展區四：金流動脈與部位控管")
    if txs:
        df_txs = pd.DataFrame(txs)
        df_txs['日期_dt'] = pd.to_datetime(df_txs['日期'])
        df_txs = df_txs.sort_values('日期_dt')
        df_txs['流向'] = df_txs['金額'].apply(lambda x: '流出 (支出/買股)' if x < 0 else '流入 (存錢/賣股)')
        df_txs['金額絕對值'] = df_txs['金額'].abs()
        df_txs['累計淨現金流'] = df_txs['金額'].cumsum()

        c2_15, c2_16, c2_17 = st.columns(3)
        with c2_15:
            fig15 = px.sunburst(df_txs, path=['流向', '類型'], values='金額絕對值', color='流向', color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig15.update_traces(hovertemplate="<b>%{label}</b><br>總計: NT$ %{value:,.0f}<extra></extra>")
            st.plotly_chart(style_fig(fig15, "15. 銀行金流樹狀結構"), use_container_width=True)
            
        with c2_16:
            fig16 = px.bar(df_txs, x="日期_dt", y="金額", color="流向", color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig16.update_traces(hovertemplate="<b>日期: %{x}</b><br>單筆金額: NT$ %{y:+,.0f}<extra></extra>")
            st.plotly_chart(style_fig(fig16, "16. 單筆資金進出分布"), use_container_width=True)
            
        with c2_17:
            fig17 = go.Figure(go.Scatter(x=df_txs['日期_dt'], y=df_txs['累計淨現金流'], mode='lines+markers', line=dict(color='#9b59b6', width=3)))
            fig17.update_traces(hovertemplate="<b>日期: %{x}</b><br>累計淨金流: NT$ %{y:+,.0f}<extra></extra>")
            st.plotly_chart(style_fig(fig17, "17. 累計淨現金流走勢"), use_container_width=True)

# ------------------------------------------
# 分頁 3：歷史報表 & 分頁 4：金流明細
# ------------------------------------------
with tab3:
    st.subheader("📜 歷史每日結算報表")
    if hist_data:
        df_hist_display = df_hist.drop(columns=["真實日期", "單日損益變化", "最高市值", "市值回撤", "20日均線"], errors='ignore').copy()[::-1]
        def color_history(row):
            return ['color: #ff4b4b; font-weight: bold;' if val > 0 else ('color: #09ab3b; font-weight: bold;' if val < 0 else '') if col in ["總投資損益", "0050每日損益", "台積電每日損益", "ROI(%)"] and pd.notna(val) and isinstance(val, (int, float)) else '' for col, val in row.items()]
        st.dataframe(df_hist_display.style.apply(color_history, axis=1).format({"總累積成本": "{:,.0f}", "總市值": "{:,.0f}", "總投資損益": "{:+,.0f}", "0050每日損益": "{:+,.0f}", "台積電每日損益": "{:+,.0f}", "ROI(%)": "{:+.2f}%"}), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("🏦 銀行帳戶資金流水")
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.markdown("#### ✍️ 記帳 / 資金異動")
        with st.form("bank_record_form"):
            rec_date = st.date_input("日期")
            rec_type = st.selectbox("異動類型", ["現金", "跨行轉", "轉帳投", "委代入", "證券款", "電匯", "交割扣款"])
            amount = st.number_input("金額 (元) 【扣款請直接輸入負數】", value=0.0, step=100.0)
            note = st.text_input("備註說明")
            if st.form_submit_button("寫入試算表"):
                if amount != 0:
                    try:
                        client = get_gspread_client()
                        client.open(SPREADSHEET_NAME).worksheet("db_bank_ledger").append_row([str(rec_date), rec_type, amount, note], value_input_option="USER_ENTERED")
                        st.success("紀錄成功！畫面將自動更新。")
                        st.rerun()
                    except Exception as e: st.error(f"寫入失敗: {e}")
                else: st.warning("請輸入有效金額。")

    with col_list:
        st.markdown("#### 📋 帳戶流水明細")
        if txs:
            df_bank = pd.DataFrame(txs)
            st.dataframe(df_bank.style.apply(lambda row: ['color: #ff4b4b; font-weight: bold;' if row[col] > 0 else ('color: #09ab3b; font-weight: bold;' if row[col] < 0 else '') if col == "金額" and pd.notna(row[col]) and isinstance(row[col], (int, float)) else '' for col in row.index], axis=1).format({"金額": "{:+,.0f}"}), use_container_width=True, hide_index=True)
