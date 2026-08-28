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
# 1. 頁面基本配置 (寬螢幕模式以容納大量圖表)
# ==========================================
st.set_page_config(
    page_title="個人資產儀表板 (終極版)",
    layout="wide",
    page_icon="💼",
    initial_sidebar_state="expanded"
)

# 2. ⚡ 雲端自動刷新 (20 分鐘)
st_autorefresh(interval=1200000, key="realtime_data_refresher")

WEEK_MAP = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
SPREADSHEET_NAME = "個人資產" 

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
        st.error(f"Google 金鑰讀取失敗: {e}")
        return None

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

        # 1. 讀取「資產總覽」
        ws_summary = sh.worksheet("資產總覽")
        s_rows = ws_summary.get_all_values()
        
        holdings = []
        total_assets = 0.0
        total_cost = 0.0
        total_profit = 0.0
        
        if len(s_rows) > 1:
            price_map = {}
            change_map = {}
            for sr in s_rows[1:]:
                if len(sr) >= 10 and sr[7]:
                    stock_key = sr[7].strip()
                    price_map[stock_key] = parse_num(sr[8])
                    change_map[stock_key] = parse_num(str(sr[9]).replace('%', ''))

            for sr in s_rows[1:]:
                if len(sr) >= 6 and sr[0]:
                    name = sr[0].strip()
                    shares = parse_num(sr[1])
                    cost = parse_num(sr[2])
                    avg_cost = parse_num(sr[3])
                    profit = parse_num(sr[4])
                    m_val = parse_num(sr[5])
                    
                    if cost > 0 or m_val > 0:
                        total_cost += cost
                        total_assets += m_val
                        total_profit += profit
                        curr_price, chg_pct = 0.0, 0.0
                        
                        for k, p in price_map.items():
                            if ("0050" in name and "0050" in k) or ("台積電" in name and "台積電" in k) or (name in k or k in name):
                                curr_price = p
                                chg_pct = change_map.get(k, 0.0)
                                break
                        
                        if curr_price == 0.0 and shares > 0: curr_price = m_val / shares
                        holdings.append({
                            "stock_name": name, "shares": shares, "avg_cost": avg_cost,
                            "total_cost": cost, "current_price": curr_price,
                            "market_value": m_val, "各股損益": profit, "change_pct": chg_pct
                        })

        profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0

        # 2. 讀取「每日損益追蹤」
        ws_overview = sh.worksheet("每日損益追蹤")
        rows = ws_overview.get_all_values()
        hist_data = []
        if len(rows) > 1:
            for r in rows[1:]:
                if len(r) >= 14 and str(r[0]).strip() != "":
                    hist_data.append({
                        "日期": r[0], "總累積成本": parse_num(r[5]), "總市值": parse_num(r[6]), 
                        "總投資損益": parse_num(r[7]), "0050每日損益": parse_num(r[12]),
                        "台積電每日損益": parse_num(r[13])
                    })
        
        return {"total_assets": total_assets, "total_cost": total_cost, "total_profit": total_profit, "profit_rate": profit_rate, "holdings": holdings}, hist_data
    except Exception as e:
        st.info(f"讀取試算表發生錯誤: {e}")
        return None, None

def load_bank_data():
    client = get_gspread_client()
    if not client: return 58661.0, []
    try:
        sh = client.open(SPREADSHEET_NAME)
        try:
            ws_summary = sh.worksheet("資產總覽")
            s_rows = ws_summary.get_all_values()
            b_val = float(str(s_rows[1][11]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 58661) if len(s_rows) > 1 and len(s_rows[1]) >= 12 else 58661.0
        except: b_val = 58661.0

        ws_bank = sh.worksheet("db_bank_ledger")
        b_rows = ws_bank.get_all_values()
        txs = []
        if len(b_rows) > 1:
            for r in b_rows[1:]:
                if len(r) >= 4 and str(r[0]).strip() != "":
                    try: amt = float(str(r[2]).replace('NT$', '').replace('$', '').replace(',', '').strip() or 0)
                    except: amt = 0.0
                    txs.append({"日期": r[0], "類型": r[1], "金額": amt, "備註": r[3]})
        return b_val, txs
    except Exception as e:
        return 58661.0, []

# ==========================================
# UI 元件：彩色資訊卡片
# ==========================================
def create_colorful_card(title, value_str, icon="", theme="blue", is_profit=False, num_val=None):
    if is_profit and num_val is not None:
        bg_gradient = "linear-gradient(135deg, #1e2128 0%, #13151a 100%)"
        title_color = "#a0a5b1"
        if num_val > 0:
            val_color, glow_color, text_shadow = "#ff4b4b", "rgba(255, 75, 75, 0.6)", "0 0 10px rgba(255, 75, 75, 0.4)"
        elif num_val < 0:
            val_color, glow_color, text_shadow = "#09ab3b", "rgba(9, 171, 59, 0.6)", "0 0 10px rgba(9, 171, 59, 0.4)"
        else:
            val_color, glow_color, text_shadow = "#ffffff", "rgba(255, 255, 255, 0.2)", "none"
        title_shadow = "0 1px 3px rgba(0,0,0,0.3)"
    else:
        text_shadow, title_shadow = "0 2px 4px rgba(0,0,0,0.3)", "0 1px 3px rgba(0,0,0,0.3)"
        if theme == "purple":
            bg_gradient, glow_color, title_color, val_color = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "rgba(118, 75, 162, 0.6)", "#e0c3fc", "#fef08a"
        elif theme == "blue":
            bg_gradient, glow_color, title_color, val_color = "linear-gradient(135deg, #2b5876 0%, #4e4376 100%)", "rgba(78, 67, 118, 0.6)", "#bae6fd", "#a7f3d0"
        elif theme == "gold":
            bg_gradient, glow_color, title_color, val_color = "linear-gradient(135deg, #FF8008 0%, #FFC837 100%)", "rgba(200, 128, 8, 0.6)", "#78350f", "#80caf0"

    return f"""
    <div style="background: {bg_gradient}; border-radius: 16px; padding: 20px 10px; box-shadow: 0 8px 20px {glow_color}; height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; position: relative; overflow: hidden; margin-bottom: 15px;">
        <div style="position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center;">
            <p style="margin: 0; font-size: 1.05rem; color: {title_color}; font-weight: 600; text-shadow: {title_shadow};">{title}</p>
            <p style="margin: 8px 0 0 0; font-size: 1.7rem; font-weight: 800; letter-spacing: 0.5px; color: {val_color}; text-shadow: {text_shadow}; white-space: nowrap;">{value_str}</p>
        </div>
        <div style="position: absolute; right: 0px; bottom: -15px; font-size: 5rem; opacity: 0.12; z-index: 0; transform: rotate(-15deg); pointer-events: none; color: {val_color};">{icon}</div>
    </div>
    """

# ==========================================
# 主畫面開始
# ==========================================
st.title("💼 個人旗艦資產工作站 ☁️")
st.markdown("##### 🚀 終極數據大廳 (18 種進階分析圖表)")

bank_balance, txs = load_bank_data()
dashboard_data, hist_data = load_sheet_data()

tab1, tab2, tab3, tab4 = st.tabs(["📊 儀表板總覽", "📈 終極數據大廳 (18 圖表)", "📜 歷史結算報表", "🏦 銀行流水明細"])

# ------------------------------------------
# 分頁 1：儀表板總覽
# ------------------------------------------
with tab1:
    if dashboard_data:
        d_tot_assets, d_tot_cost, d_tot_prof, d_prof_rt = dashboard_data.get("total_assets", 0.0), dashboard_data.get("total_cost", 0.0), dashboard_data.get("total_profit", 0.0), dashboard_data.get("profit_rate", 0.0)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.markdown(create_colorful_card("總市值", f"NT$ {d_tot_assets:,.0f}", "💎", "purple"), unsafe_allow_html=True)
        with c2: st.markdown(create_colorful_card("總成本", f"NT$ {d_tot_cost:,.0f}", "📥", "blue"), unsafe_allow_html=True)
        with c3: st.markdown(create_colorful_card("帳戶餘額", f"NT$ {bank_balance:,.0f}", "🏦", "gold"), unsafe_allow_html=True)
        with c4: st.markdown(create_colorful_card("即時總損益", f"{d_tot_prof:+,.0f}", "🔥" if d_tot_prof>0 else "💧", is_profit=True, num_val=d_tot_prof), unsafe_allow_html=True)
        with c5: st.markdown(create_colorful_card("總損益 (%)", f"{d_prof_rt:+.2f}%", "📈", is_profit=True, num_val=d_prof_rt), unsafe_allow_html=True)

        st.subheader("📋 投資組合即時明細")
        holdings = dashboard_data.get("holdings", [])
        if holdings:
            df_holdings = pd.DataFrame(holdings)
            df_holdings["各股損益(%)"] = df_holdings.apply(lambda x: (x["各股損益"] / x["total_cost"] * 100) if x["total_cost"] > 0 else 0.0, axis=1)
            df_display = df_holdings.rename(columns={"stock_name": "股票名稱", "shares": "總股數", "avg_cost": "平均成本", "total_cost": "總成本", "current_price": "即時現價", "market_value": "即時市值", "change_pct": "即時漲跌幅(%)"})[["股票名稱", "總股數", "平均成本", "總成本", "即時現價", "即時市值", "各股損益", "即時漲跌幅(%)", "各股損益(%)"]]

            def color_tw_market(row):
                styles = [''] * len(row)
                for i, col in enumerate(row.index):
                    val = row[col]
                    if col in ["即時現價", "各股損益", "各股損益(%)", "即時漲跌幅(%)"] and pd.notna(val) and isinstance(val, (int, float)):
                        styles[i] = 'color: #ff4b4b; font-weight: bold;' if val > 0 else ('color: #09ab3b; font-weight: bold;' if val < 0 else '')
                return styles

            styled_df = df_display.style.apply(color_tw_market, axis=1).format({"總股數": "{:,.0f}", "平均成本": "{:,.2f}", "總成本": "{:,.0f}", "即時現價": "{:,.2f}", "即時市值": "{:,.0f}", "各股損益": "{:+,.0f}", "即時漲跌幅(%)": "{:+.2f}%", "各股損益(%)": "{:+.2f}%"})
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ------------------------------------------
# 分頁 2：📈 終極數據大廳 (火力展示區)
# ------------------------------------------
with tab2:
    bg_transparent = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.markdown("### 🔍 第一展區：資產結構與現況分析")
    
    if dashboard_data and dashboard_data.get("holdings", []):
        df_h = pd.DataFrame(dashboard_data["holdings"])
        df_h["各股損益(%)"] = df_h.apply(lambda x: (x["各股損益"] / x["total_cost"] * 100) if x["total_cost"] > 0 else 0.0, axis=1)
        
        c2_1, c2_2, c2_3 = st.columns(3)
        # 圖表 1：大類資產圓餅圖
        with c2_1:
            fig1 = px.pie(names=['股票總市值', '銀行帳戶餘額'], values=[dashboard_data["total_assets"], bank_balance], title="1. 總資產配置", hole=0.45, color_discrete_sequence=['#4B8BBE', '#FFE873'])
            fig1.update_layout(**bg_transparent)
            st.plotly_chart(fig1, use_container_width=True)
            
        # 圖表 2：持股市值分布 (Donut)
        with c2_2:
            fig2 = px.pie(df_h, names='stock_name', values='market_value', title="2. 個股市值佔比", hole=0.45)
            fig2.update_layout(**bg_transparent)
            st.plotly_chart(fig2, use_container_width=True)
            
        # 圖表 3：總投資報酬率儀表板
        with c2_3:
            fig3 = go.Figure(go.Indicator(
                mode = "gauge+number", value = dashboard_data["profit_rate"],
                title = {'text': "3. 總帳面獲利率 (%)"},
                gauge = {'axis': {'range': [-20, 20]}, 'bar': {'color': "#ff4b4b" if dashboard_data["profit_rate"]>0 else "#09ab3b"}}
            ))
            fig3.update_layout(**bg_transparent)
            st.plotly_chart(fig3, use_container_width=True)

        c2_4, c2_5 = st.columns(2)
        # 圖表 4：板塊熱力圖 (Treemap)
        with c2_4:
            fig4 = px.treemap(df_h, path=['stock_name'], values='market_value', color='各股損益(%)', color_continuous_scale=['#09ab3b', '#222222', '#ff4b4b'], color_continuous_midpoint=0, title="4. 股票熱力圖 (大小=市值, 顏色=賺賠)")
            fig4.update_layout(**bg_transparent, margin=dict(t=40, l=10, r=10, b=10))
            st.plotly_chart(fig4, use_container_width=True)

        # 圖表 5：個股獲利貢獻瀑布圖
        with c2_5:
            fig5 = go.Figure(go.Waterfall(
                name="2020", orientation="v", measure=["relative"] * len(df_h) + ["total"],
                x=df_h['stock_name'].tolist() + ["淨損益總計"], textposition="outside",
                y=df_h['各股損益'].tolist() + [dashboard_data["total_profit"]],
                decreasing={"marker":{"color":"#09ab3b"}}, increasing={"marker":{"color":"#ff4b4b"}}, totals={"marker":{"color":"#3498db"}}
            ))
            fig5.update_layout(title="5. 各股獲利貢獻瀑布圖", **bg_transparent)
            st.plotly_chart(fig5, use_container_width=True)

        c2_6, c2_7 = st.columns(2)
        # 圖表 6：成本與市值對比條形圖
        with c2_6:
            fig6 = go.Figure(data=[
                go.Bar(name='總投入成本', x=df_h['stock_name'], y=df_h['total_cost'], marker_color='#8e44ad'),
                go.Bar(name='當前總市值', x=df_h['stock_name'], y=df_h['market_value'], marker_color='#f1c40f')
            ])
            fig6.update_layout(title="6. 個股成本 vs 現值對比", barmode='group', **bg_transparent)
            st.plotly_chart(fig6, use_container_width=True)
            
        # 圖表 7：各股絕對損益長條圖
        with c2_7:
            colors = ['#ff4b4b' if val > 0 else '#09ab3b' for val in df_h['各股損益']]
            fig7 = go.Figure(go.Bar(x=df_h['各股損益'], y=df_h['stock_name'], orientation='h', marker_color=colors))
            fig7.update_layout(title="7. 各股帳面損益金額", **bg_transparent)
            st.plotly_chart(fig7, use_container_width=True)

    st.divider()
    st.markdown("### 📈 第二展區：時間序列與績效回溯")
    if hist_data:
        df_hist = pd.DataFrame(hist_data)
        df_hist["真實日期"] = pd.to_datetime(df_hist["日期"])
        df_hist = df_hist.sort_values("真實日期")
        df_hist["投資報酬率(%)"] = (df_hist["總投資損益"] / df_hist["總累積成本"]) * 100
        # 計算單日變化
        df_hist["單日損益變化"] = df_hist["總投資損益"].diff().fillna(0)
        df_hist["最高市值"] = df_hist["總市值"].cummax()
        df_hist["市值回撤"] = df_hist["總市值"] - df_hist["最高市值"]

        c2_8, c2_9 = st.columns(2)
        # 圖表 8：累積損益面積圖
        with c2_8:
            fig8 = px.area(df_hist, x="真實日期", y="總投資損益", title="8. 總投資累積損益走勢", color_discrete_sequence=['#e74c3c'])
            fig8.update_layout(**bg_transparent)
            st.plotly_chart(fig8, use_container_width=True)
            
        # 圖表 9：總市值與成本平行走勢
        with c2_9:
            fig9 = go.Figure()
            fig9.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['總市值'], mode='lines', name='總市值', line=dict(color='#2ecc71', width=3)))
            fig9.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['總累積成本'], mode='lines', name='總成本', line=dict(color='#95a5a6', dash='dash')))
            fig9.update_layout(title="9. 總資產成長軌跡", **bg_transparent)
            st.plotly_chart(fig9, use_container_width=True)

        c2_10, c2_11 = st.columns(2)
        # 圖表 10：ROI 走勢
        with c2_10:
            fig10 = px.line(df_hist, x="真實日期", y="投資報酬率(%)", title="10. 投資報酬率 (ROI) 趨勢", markers=True, color_discrete_sequence=['#9b59b6'])
            fig10.update_layout(**bg_transparent)
            st.plotly_chart(fig10, use_container_width=True)
            
        # 圖表 11：每日個股貢獻疊加
        with c2_11:
            fig11 = go.Figure()
            fig11.add_trace(go.Bar(x=df_hist['真實日期'], y=df_hist['0050每日損益'], name='0050', marker_color='#3498db'))
            fig11.add_trace(go.Bar(x=df_hist['真實日期'], y=df_hist['台積電每日損益'], name='台積電', marker_color='#e74c3c'))
            fig11.update_layout(title="11. 每日損益部位貢獻拆解", barmode='relative', **bg_transparent)
            st.plotly_chart(fig11, use_container_width=True)

        st.divider()
        st.markdown("### ⚠️ 第三展區：風險、波動與規律分析")
        c2_12, c2_13, c2_14 = st.columns(3)
        
        # 圖表 12：單日波動長條圖
        with c2_12:
            vol_colors = ['#ff4b4b' if val > 0 else '#09ab3b' for val in df_hist['單日損益變化']]
            fig12 = go.Figure(go.Bar(x=df_hist['真實日期'], y=df_hist['單日損益變化'], marker_color=vol_colors))
            fig12.update_layout(title="12. 單日總損益劇烈震幅", **bg_transparent)
            st.plotly_chart(fig12, use_container_width=True)
            
        # 圖表 13：0050 vs 2330 累計獲利賽跑
        with c2_13:
            fig13 = go.Figure()
            fig13.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['0050每日損益'].cumsum(), mode='lines', name='0050累計'))
            fig13.add_trace(go.Scatter(x=df_hist['真實日期'], y=df_hist['台積電每日損益'].cumsum(), mode='lines', name='台積電累計'))
            fig13.update_layout(title="13. 雙引擎累計獲利賽跑", **bg_transparent)
            st.plotly_chart(fig13, use_container_width=True)
            
        # 圖表 14：最大回撤 (Drawdown)
        with c2_14:
            fig14 = px.area(df_hist, x="真實日期", y="市值回撤", title="14. 距離歷史最高點回撤", color_discrete_sequence=['#e67e22'])
            fig14.update_layout(**bg_transparent)
            st.plotly_chart(fig14, use_container_width=True)

        c2_15, _ = st.columns([1, 1])
        # 圖表 15：星期規律分析
        with c2_15:
            df_hist["星期"] = df_hist["真實日期"].dt.weekday.map(WEEK_MAP)
            dow_avg = df_hist.groupby("星期")["單日損益變化"].mean().reset_index()
            # 確保按星期一到五排序
            sorter = ['一', '二', '三', '四', '五']
            dow_avg['星期'] = pd.Categorical(dow_avg['星期'], categories=sorter, ordered=True)
            dow_avg = dow_avg.sort_values('星期')
            dow_colors = ['#ff4b4b' if val > 0 else '#09ab3b' for val in dow_avg['單日損益變化']]
            fig15 = go.Figure(go.Bar(x=dow_avg['星期'], y=dow_avg['單日損益變化'], marker_color=dow_colors))
            fig15.update_layout(title="15. 星期幾最容易賺錢？(平均單日變化)", **bg_transparent)
            st.plotly_chart(fig15, use_container_width=True)

    st.divider()
    st.markdown("### 🏦 第四展區：現金流動脈分析")
    if txs:
        df_txs = pd.DataFrame(txs)
        df_txs['日期_dt'] = pd.to_datetime(df_txs['日期'])
        df_txs = df_txs.sort_values('日期_dt')
        df_txs['流向'] = df_txs['金額'].apply(lambda x: '流出 (支出/買股)' if x < 0 else '流入 (存錢/賣股)')
        df_txs['金額絕對值'] = df_txs['金額'].abs()
        df_txs['累計淨現金流'] = df_txs['金額'].cumsum()

        c2_16, c2_17, c2_18 = st.columns(3)
        
        # 圖表 16：資金流向結構
        with c2_16:
            fig16 = px.sunburst(df_txs, path=['流向', '類型'], values='金額絕對值', title="16. 銀行資金流向樹狀結構", color='流向', color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig16.update_layout(**bg_transparent)
            st.plotly_chart(fig16, use_container_width=True)
            
        # 圖表 17：每日現金進出柱狀圖
        with c2_17:
            fig17 = px.bar(df_txs, x="日期_dt", y="金額", color="流向", title="17. 單筆金流紀錄分布", color_discrete_map={'流入 (存錢/賣股)': '#09ab3b', '流出 (支出/買股)': '#ff4b4b'})
            fig17.update_layout(**bg_transparent)
            st.plotly_chart(fig17, use_container_width=True)
            
        # 圖表 18：歷史淨現金流走勢
        with c2_18:
            fig18 = px.line(df_txs, x="日期_dt", y="累計淨現金流", title="18. 累計淨金流變化", markers=True)
            fig18.update_layout(**bg_transparent)
            st.plotly_chart(fig18, use_container_width=True)
    else:
        st.info("需要更多銀行明細來生成金流分析。")

# ------------------------------------------
# 分頁 3：歷史結算報表
# ------------------------------------------
with tab3:
    st.subheader("📜 歷史每日結算報表")
    if hist_data:
        df_hist_display = df_hist.drop(columns=["真實日期", "單日損益變化", "最高市值", "市值回撤"], errors='ignore').copy()[::-1]
        def color_history(row):
            styles = [''] * len(row)
            for i, col in enumerate(row.index):
                val = row[col]
                if col in ["總投資損益", "0050每日損益", "台積電每日損益", "投資報酬率(%)"] and pd.notna(val) and isinstance(val, (int, float)):
                    styles[i] = 'color: #ff4b4b; font-weight: bold;' if val > 0 else ('color: #09ab3b; font-weight: bold;' if val < 0 else '')
            return styles
        format_hist_dict = {"總累積成本": "{:,.0f}", "總市值": "{:,.0f}", "總投資損益": "{:+,.0f}", "0050每日損益": "{:+,.0f}", "台積電每日損益": "{:+,.0f}", "投資報酬率(%)": "{:+.2f}%"}
        styled_hist = df_hist_display.style.apply(color_history, axis=1).format(format_hist_dict, na_rep="")
        st.dataframe(styled_hist, use_container_width=True, hide_index=True)

# ------------------------------------------
# 分頁 4：銀行帳戶明細與記帳
# ------------------------------------------
with tab4:
    st.subheader("🏦 銀行帳戶資金流水")
    st.markdown(create_colorful_card("銀行帳戶活存總結餘", f"NT$ {bank_balance:,.0f}", "💰", "gold"), unsafe_allow_html=True)
    st.divider()
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
            def color_bank(row):
                styles = [''] * len(row)
                for i, col in enumerate(row.index):
                    if col == "金額" and pd.notna(row[col]) and isinstance(row[col], (int, float)):
                        styles[i] = 'color: #ff4b4b; font-weight: bold;' if row[col] > 0 else ('color: #09ab3b; font-weight: bold;' if row[col] < 0 else '')
                return styles
            st.dataframe(df_bank.style.apply(color_bank, axis=1).format({"金額": "{:+,.0f}"}), use_container_width=True, hide_index=True)
