"""3C 数码电商经营分析工作台（京东红色主题 / 本地无 API 版）
运行：python -m streamlit run app.py
说明：全部数据来自本地模拟 CSV；不调用任何大模型 API。
"""
from __future__ import annotations
from pathlib import Path
import html
import math
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agent_tools import (
    get_business_overview,
    compare_sales_periods,
    get_category_performance,
    get_declining_skus,
    get_competitor_price_gaps,
    get_inventory_risks,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(
    page_title="京东风格 · 3C 电商经营工作台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

RED = "#E1251B"
RED_DARK = "#B91C1C"
ORANGE = "#FF6A00"
INK = "#1F2937"
MUTED = "#6B7280"
GREEN = "#0F9D75"
BG = "#F4F6FA"

# -------------------------- 全局视觉样式 --------------------------
st.markdown(
    f"""
    <style>
    :root {{
      --jd-red: {RED}; --jd-red-dark: {RED_DARK}; --jd-orange: {ORANGE};
      --ink: {INK}; --muted: {MUTED}; --page-bg: {BG};
    }}
    .stApp {{ background: var(--page-bg); color: var(--ink); }}
    [data-testid="stHeader"] {{ background: rgba(244,246,250,.88); }}
    .block-container {{ padding-top: 1.35rem; padding-bottom: 2.5rem; max-width: 1500px; }}
    section[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #E8EBF1; }}
    section[data-testid="stSidebar"] .block-container {{ padding-top: 1.25rem; }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
      padding: .55rem .65rem; border-radius: 10px; margin: .08rem 0;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{ background: #FFF2F1; }}
    div.stButton > button, div.stFormSubmitButton > button {{
      border-radius: 10px; border: 1px solid var(--jd-red); background: var(--jd-red);
      color: #fff; font-weight: 650; padding: .48rem 1rem; transition: all .15s ease;
    }}
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {{
      background: var(--jd-red-dark); border-color: var(--jd-red-dark); color: #fff;
    }}
    div[data-testid="stMetric"] {{ background: transparent; }}
    div[data-testid="stDataFrame"] {{ border: 1px solid #E6E9EF; border-radius: 12px; overflow: hidden; }}
    div[data-testid="stPlotlyChart"] {{ background: #fff; border: 1px solid #E9ECF2; border-radius: 14px; padding: 8px 8px 0 8px; }}
    div[data-testid="stExpander"] {{ border: 1px solid #E6E9EF; border-radius: 12px; background: #fff; }}
    .brand-mark {{ display:flex; align-items:center; gap:10px; padding: 2px 2px 16px 2px; }}
    .brand-logo {{ width:42px; height:42px; border-radius:13px; color:#fff; display:flex; align-items:center; justify-content:center;
      background:linear-gradient(135deg, {RED} 0%, {ORANGE} 100%); font-size:22px; font-weight:900; box-shadow:0 6px 16px rgba(225,37,27,.2); }}
    .brand-name {{ font-size:16px; font-weight:800; line-height:1.3; color:#202938; }}
    .brand-sub {{ color:#87909F; font-size:11px; margin-top:3px; letter-spacing:.3px; }}
    .sidebar-section {{ color:#9AA2AE; font-size:11px; font-weight:800; letter-spacing:1px; margin: 10px 0 7px 3px; }}
    .hero {{ border-radius:18px; padding:25px 28px 23px 28px; color:#fff; position:relative; overflow:hidden;
      background:linear-gradient(112deg, {RED_DARK} 0%, {RED} 55%, {ORANGE} 120%); box-shadow:0 10px 24px rgba(225,37,27,.13); margin-bottom:18px; }}
    .hero:after {{ content:""; position:absolute; width:260px; height:260px; border:36px solid rgba(255,255,255,.075); border-radius:50%; right:-60px; top:-130px; }}
    .hero-kicker {{ font-size:11px; letter-spacing:1.8px; opacity:.82; font-weight:800; text-transform:uppercase; }}
    .hero-title {{ font-size:27px; line-height:1.3; letter-spacing:-.5px; font-weight:850; margin:7px 0 6px 0; }}
    .hero-desc {{ color:rgba(255,255,255,.86); font-size:13px; line-height:1.7; max-width:760px; }}
    .hero-chip {{ display:inline-block; border:1px solid rgba(255,255,255,.32); background:rgba(255,255,255,.12); border-radius:99px;
      padding:5px 10px; font-size:11px; margin-top:13px; margin-right:6px; }}
    .section-head {{ display:flex; align-items:center; gap:10px; margin: 20px 0 12px 0; }}
    .section-bar {{ width:4px; min-width:4px; height:23px; border-radius:8px; background:linear-gradient(180deg, {RED}, {ORANGE}); }}
    .section-title {{ color:#202938; font-weight:800; font-size:18px; }}
    .section-subtitle {{ color:#8992A1; font-size:12px; margin-top:3px; }}
    .kpi-card {{ background:#fff; border:1px solid #E8EBF1; border-radius:15px; padding:17px 18px 15px 18px; min-height:126px;
      box-shadow:0 3px 12px rgba(30,41,59,.025); position:relative; overflow:hidden; }}
    .kpi-card:before {{ content:""; position:absolute; left:0; top:0; width:4px; height:100%; background:var(--card-accent, {RED}); }}
    .kpi-label {{ color:#7C8594; font-size:12px; font-weight:650; margin-bottom:10px; }}
    .kpi-value {{ color:#1E2735; font-size:23px; font-weight:850; line-height:1.2; letter-spacing:-.4px; }}
    .kpi-foot {{ color:#9AA2AF; font-size:11px; margin-top:9px; }}
    .kpi-icon {{ float:right; color:{RED}; background:#FFF0EF; border-radius:10px; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-size:15px; }}
    .panel {{ background:#fff; border:1px solid #E8EBF1; border-radius:15px; padding:17px 18px; box-shadow:0 3px 12px rgba(30,41,59,.025); }}
    .panel-title {{ font-size:14px; font-weight:800; color:#273142; margin-bottom:3px; }}
    .panel-desc {{ font-size:11px; color:#929AA7; margin-bottom:13px; }}
    .notice {{ border-radius:10px; background:#FFF7ED; color:#9A5B13; border:1px solid #FDE6C7; padding:10px 12px; font-size:12px; line-height:1.65; }}
    .info-strip {{ border-radius:10px; background:#FFF1F0; color:#9C2823; border:1px solid #FAD8D5; padding:10px 12px; font-size:12px; line-height:1.65; }}
    .footer {{ color:#A0A7B3; font-size:11px; padding-top:20px; border-top:1px solid #E7EAF0; margin-top:28px; }}
    @media (max-width: 800px) {{ .hero-title {{font-size:22px;}} .kpi-value {{font-size:19px;}} .hero {{padding:20px;}} }}
    </style>
    """,
    unsafe_allow_html=True,
)

CATEGORY_WORDS = ["手机", "笔记本电脑", "平板电脑", "耳机"]


def detect_category(question: str) -> str | None:
    for category in CATEGORY_WORDS:
        if category in question:
            return category
    return None


def route_question(question: str) -> tuple[str, str | None]:
    """关键词路由：无大模型 API 的本地规则，不代表自然语言推理。"""
    q = question.strip().lower()
    category = detect_category(q)
    if any(word in q for word in ["促销模拟", "促销方案", "折扣模拟", "利润模拟", "促销利润", "促销测算", "优惠券模拟"]):
        return "promotion", category
    if any(word in q for word in ["运营优先级", "商品优先级", "优先处理", "优先运营", "运营机会", "机会商品", "优先级清单"]):
        return "priorities", category
    if any(word in q for word in ["单品诊断", "诊断商品", "商品详情", "sku诊断", "单个商品"]) or re.search(r"SKU\d{1,5}", question.upper()):
        return "sku_diagnosis", None
    if any(word in q for word in ["库存", "缺货", "滞销", "补货"]):
        return "inventory", None
    if any(word in q for word in ["竞品", "价格", "调价", "比对价格", "贵多少"]):
        return "price", None
    if any(word in q for word in ["下降", "下滑", "跌幅", "下降最多", "表现差"]):
        return "declines", category
    if any(word in q for word in ["品类", "各类别", "类别排名", "品类排名", "品类表现"]):
        return "category", None
    if any(word in q for word in ["对比", "环比", "变化", "前7天", "前 7 天", "趋势"]):
        return "periods", None
    if category and any(word in q for word in ["销售", "销量", "gmv", "毛利"]):
        return "category", None
    return "overview", None


def money(value: float | int | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"¥{value:,.{digits}f}"


def pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:.2f}%"


def number(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.0f}"


def section_title(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="section-head"><div class="section-bar"></div><div><div class="section-title">{html.escape(title)}</div>'
        f'<div class="section-subtitle">{html.escape(subtitle)}</div></div></div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, foot: str = "", icon: str = "●", accent: str = RED) -> None:
    st.markdown(
        f'<div class="kpi-card" style="--card-accent:{accent}">'
        f'<div class="kpi-icon" style="color:{accent};">{html.escape(icon)}</div>'
        f'<div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-foot">{html.escape(foot)}</div></div>',
        unsafe_allow_html=True,
    )


def chart_layout(fig, height: int = 350):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=14, r=18, t=30, b=18),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
        font=dict(family="Arial, Microsoft YaHei, sans-serif", color=INK, size=12),
        title_font=dict(size=14, color=INK), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#202938", font_color="#FFFFFF"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEF0F4", zeroline=False, linecolor="#E8EBF1")
    fig.update_yaxes(showgrid=True, gridcolor="#EEF0F4", zeroline=False, linecolor="#E8EBF1")
    return fig


def styled_table(df: pd.DataFrame, height: int | None = None, column_config: dict | None = None) -> None:
    if df.empty:
        st.info("当前筛选条件下暂无数据。")
        return
    st.dataframe(
        df.style.set_properties(**{"background-color": "#FFFFFF", "color": INK, "border-color": "#EEF0F4"})
        .set_table_styles([
            {"selector": "th", "props": [("background-color", "#FFF0EF"), ("color", "#9C2823"), ("font-weight", "700"), ("border-color", "#F4D9D7")]},
            {"selector": "td", "props": [("padding", "9px 12px"), ("font-size", "12px")]},
        ]),
        use_container_width=True, hide_index=True, height=height,
        column_config=column_config or {},
    )


def load_sales() -> pd.DataFrame:
    path = DATA_DIR / "sales_daily.csv"
    if not path.exists():
        raise FileNotFoundError(f"找不到 {path}。请确认 data 文件夹与 app.py 在同一项目目录，并先运行 python generate_data.py。")
    df = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["date"])
    return df


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">JD INSIGHT · COMMERCE INTELLIGENCE</div>
          <div class="hero-title">3C 数码电商经营工作台</div>
          <div class="hero-desc">把经营数据转化为清晰的业务洞察。集中查看销售表现、商品竞争力与库存风险，支持从异常商品继续下钻到单品级排查。</div>
          <span class="hero-chip">● 本地数据分析</span><span class="hero-chip">模拟数据 · 非真实商家数据</span><span class="hero-chip">免 API 版本</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview() -> None:
    result = get_business_overview(90)
    periods = compare_sales_periods(7)
    sales = load_sales()
    recent = periods["recent_period"]
    change = periods["change"]

    section_title("核心经营指标", f"数据周期 {result['start_date']} — {result['end_date']} · 最近 90 天")
    c = st.columns(4, gap="medium")
    with c[0]: kpi_card("成交总额 GMV", money(result["gmv"], 0), "近 90 天累计", "¥", RED)
    with c[1]: kpi_card("毛利额", money(result["gross_profit"], 0), "按模拟数据中的毛利字段汇总", "↗", ORANGE)
    with c[2]: kpi_card("整体毛利率", pct(result["gross_margin_rate"]), "毛利额 ÷ GMV", "%", GREEN)
    with c[3]: kpi_card("支付转化率", pct(result["conversion_rate"]), "订单数 ÷ 访客数", "◎", RED)

    c = st.columns(4, gap="medium")
    with c[0]: kpi_card("累计访客", number(result["visitors"]), "90 天累计", "◉", "#64748B")
    with c[1]: kpi_card("累计订单", number(result["orders"]), "90 天累计", "▤", "#64748B")
    with c[2]: kpi_card("平均客单价", money(result["average_order_value"]), "GMV ÷ 订单数", "￥", ORANGE)
    with c[3]: kpi_card("最近 7 天 GMV 环比", f"{change['gmv_change_pct']:+.2f}%", f"最近 7 天 GMV {money(recent['gmv'], 0)}", "↗" if change["gmv_change_pct"] >= 0 else "↘", GREEN if change["gmv_change_pct"] >= 0 else RED)

    section_title("经营趋势", "查看 GMV 每日变化，观察周期内的波动与峰值")
    daily = sales.groupby("date", as_index=False).agg(gmv=("gmv", "sum"), gross_profit=("gross_profit", "sum"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["gmv"], name="GMV", mode="lines", line=dict(color=RED, width=2.8), fill="tozeroy", fillcolor="rgba(225,37,27,.08)"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["gross_profit"], name="毛利额", mode="lines", line=dict(color=ORANGE, width=2), visible="legendonly"))
    fig.update_layout(title="每日 GMV 趋势（可点击图例切换毛利额）", xaxis_title="日期", yaxis_title="金额（元）", hovermode="x unified")
    chart_layout(fig, 365)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns([1.15, 0.85], gap="large")
    with col1:
        section_title("最近一周表现", "最近 7 天与前 7 天对比")
        display = pd.DataFrame([
            {"指标": "GMV", "前 7 天": money(periods["previous_period"]["gmv"], 0), "最近 7 天": money(recent["gmv"], 0), "环比": f"{change['gmv_change_pct']:+.2f}%"},
            {"指标": "毛利额", "前 7 天": money(periods["previous_period"]["gross_profit"], 0), "最近 7 天": money(recent["gross_profit"], 0), "环比": f"{change['gross_profit_change_pct']:+.2f}%"},
            {"指标": "销量", "前 7 天": number(periods["previous_period"]["units_sold"]), "最近 7 天": number(recent["units_sold"]), "环比": f"{change['units_sold_change_pct']:+.2f}%"},
            {"指标": "访客数", "前 7 天": number(periods["previous_period"]["visitors"]), "最近 7 天": number(recent["visitors"]), "环比": f"{change['visitors_change_pct']:+.2f}%"},
        ])
        styled_table(display, height=220)
        st.caption(f"最近周期：{recent['start_date']} 至 {recent['end_date']}。环比仅描述变化，不单独证明变化原因。")
    with col2:
        section_title("品类 GMV 构成", "最近 7 天 · 按品类汇总")
        cats = pd.DataFrame(get_category_performance(7))
        if not cats.empty:
            fig2 = px.pie(cats, names="category", values="gmv", hole=0.68, color_discrete_sequence=[RED, ORANGE, "#F3A6A0", "#64748B"])
            fig2.update_traces(textposition="inside", textinfo="percent", hovertemplate="%{label}<br>GMV：¥%{value:,.0f}<extra></extra>")
            fig2.update_layout(title="", showlegend=True, legend=dict(orientation="h", y=-0.12), margin=dict(l=5,r=5,t=5,b=15), height=270)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<div class="notice">口径提示：本项目使用模拟练习数据。GMV、毛利额及转化率用于演示经营分析流程，不代表任何真实商家经营结果。</div>', unsafe_allow_html=True)


def render_periods() -> None:
    result = compare_sales_periods(7)
    recent, previous, change = result["recent_period"], result["previous_period"], result["change"]
    section_title("周期经营对比", f"最近周期 {recent['start_date']} 至 {recent['end_date']}；对比周期 {previous['start_date']} 至 {previous['end_date']}")
    cols = st.columns(4, gap="medium")
    entries = [
        ("GMV 环比", f"{change['gmv_change_pct']:+.2f}%", money(change["gmv_change"], 0), "↗", GREEN if change["gmv_change_pct"] >= 0 else RED),
        ("毛利额环比", f"{change['gross_profit_change_pct']:+.2f}%", money(change["gross_profit_change"], 0), "￥", GREEN if change["gross_profit_change_pct"] >= 0 else RED),
        ("销量环比", f"{change['units_sold_change_pct']:+.2f}%", f"{change['units_sold_change']:+,} 件", "▤", GREEN if change["units_sold_change_pct"] >= 0 else RED),
        ("访客环比", f"{change['visitors_change_pct']:+.2f}%", f"{change['visitors_change']:+,} 人", "◉", GREEN if change["visitors_change_pct"] >= 0 else RED),
    ]
    for col, (label, value, foot, icon, accent) in zip(cols, entries):
        with col: kpi_card(label, value, foot, icon, accent)
    section_title("指标明细", "金额变化使用金额或相对变化率；转化率和毛利率变化使用百分点")
    rows = [
        {"指标": "GMV", "前 7 天": money(previous["gmv"]), "最近 7 天": money(recent["gmv"]), "变化值": money(change["gmv_change"]), "相对变化": f"{change['gmv_change_pct']:+.2f}%"},
        {"指标": "毛利额", "前 7 天": money(previous["gross_profit"]), "最近 7 天": money(recent["gross_profit"]), "变化值": money(change["gross_profit_change"]), "相对变化": f"{change['gross_profit_change_pct']:+.2f}%"},
        {"指标": "访客数", "前 7 天": number(previous["visitors"]), "最近 7 天": number(recent["visitors"]), "变化值": f"{change['visitors_change']:+,}", "相对变化": f"{change['visitors_change_pct']:+.2f}%"},
        {"指标": "销量", "前 7 天": number(previous["units_sold"]), "最近 7 天": number(recent["units_sold"]), "变化值": f"{change['units_sold_change']:+,}", "相对变化": f"{change['units_sold_change_pct']:+.2f}%"},
        {"指标": "转化率", "前 7 天": pct(previous["conversion_rate"]), "最近 7 天": pct(recent["conversion_rate"]), "变化值": f"{change['conversion_rate_change_percentage_points']:+.4f} 个百分点", "相对变化": "—"},
        {"指标": "毛利率", "前 7 天": pct(previous["gross_margin_rate"]), "最近 7 天": pct(recent["gross_margin_rate"]), "变化值": f"{change['gross_margin_rate_change_percentage_points']:+.4f} 个百分点", "相对变化": "—"},
        {"指标": "客单价", "前 7 天": money(previous["average_order_value"]), "最近 7 天": money(recent["average_order_value"]), "变化值": money(change["average_order_value_change"]), "相对变化": f"{change['average_order_value_change_pct']:+.2f}%"},
    ]
    styled_table(pd.DataFrame(rows), height=330)
    st.markdown('<div class="notice">分析边界：环比变化能帮助定位问题，但本身不能证明因果。若要判断原因，需要进一步查看流量、转化、价格、促销和库存等证据。</div>', unsafe_allow_html=True)


def render_categories() -> None:
    records = get_category_performance(7)
    df = pd.DataFrame(records)
    section_title("品类经营分析", "最近 7 天 · 从 GMV、销量、毛利额和毛利率比较品类表现")
    if df.empty:
        st.info("暂时没有品类数据。")
        return
    lead = df.iloc[0]
    cols = st.columns(3, gap="medium")
    with cols[0]: kpi_card("GMV 最高品类", str(lead["category"]), money(lead["gmv"], 0), "★", RED)
    with cols[1]: kpi_card("最高品类毛利额", money(lead["gross_profit"], 0), f"品类：{lead['category']}", "￥", ORANGE)
    best_margin = df.sort_values("gross_margin_rate", ascending=False).iloc[0]
    with cols[2]: kpi_card("毛利率最高品类", str(best_margin["category"]), pct(best_margin["gross_margin_rate"]), "%", GREEN)
    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        section_title("品类 GMV 排名", "横向条形图便于比较量级")
        fig = px.bar(df.sort_values("gmv"), x="gmv", y="category", orientation="h", text=df.sort_values("gmv")["gmv"].map(lambda x: f"¥{x/10000:.1f}万"), color="gmv", color_continuous_scale=["#F9B7B3", RED])
        fig.update_layout(coloraxis_showscale=False, xaxis_title="GMV（元）", yaxis_title="", showlegend=False)
        fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>GMV：¥%{x:,.0f}<extra></extra>")
        chart_layout(fig, 320)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        section_title("品类毛利率", "毛利额 ÷ GMV")
        margin_df = df.copy()
        margin_df["毛利率"] = margin_df["gross_margin_rate"] * 100
        fig2 = px.bar(margin_df.sort_values("毛利率"), x="毛利率", y="category", orientation="h", text=margin_df.sort_values("毛利率")["毛利率"].map(lambda x: f"{x:.1f}%"), color_discrete_sequence=[ORANGE])
        fig2.update_layout(xaxis_title="毛利率（%）", yaxis_title="")
        fig2.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>毛利率：%{x:.2f}%<extra></extra>")
        chart_layout(fig2, 320)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    display = df.rename(columns={"category": "品类", "units_sold": "销量"}).copy()
    display["GMV"] = display["gmv"].map(money)
    display["毛利额"] = display["gross_profit"].map(money)
    display["毛利率"] = display["gross_margin_rate"].map(pct)
    section_title("品类数据明细", "可横向比较不同品类的规模与利润率")
    styled_table(display[["品类", "GMV", "毛利额", "销量", "毛利率"]], height=230)


def render_declines(category_filter: str | None = None) -> None:
    section_title("商品销售下滑排查", "找出最近 7 天 GMV 下降幅度较大的 SKU；这是排查入口，不是原因归因结论")
    options = ["全部品类"] + CATEGORY_WORDS
    default = options.index(category_filter) if category_filter in options else 0
    chosen = st.selectbox("筛选品类", options, index=default, key="decline_category_filter")
    category = None if chosen == "全部品类" else chosen
    records = get_declining_skus(days=7, top_n=20, category=category)
    df = pd.DataFrame(records)
    if df.empty:
        st.success("当前筛选下没有 GMV 下降的 SKU。")
        return
    worst = df.iloc[0]
    c = st.columns(3, gap="medium")
    with c[0]: kpi_card("需优先关注 SKU", str(worst["sku"]), str(worst["product_name"]), "!", RED)
    with c[1]: kpi_card("最大 GMV 降幅", money(worst["gmv_change"], 0), f"{worst['gmv_change_pct']:.2f}% 环比", "↘", RED)
    with c[2]: kpi_card("当前商品售价", money(worst["current_price"], 0), f"品类：{worst['category']}", "￥", ORANGE)
    display = df[["sku", "product_name", "category", "previous_gmv", "recent_gmv", "gmv_change", "gmv_change_pct", "previous_units", "recent_units"]].copy()
    display.columns = ["SKU", "商品名称", "品类", "前 7 天 GMV", "最近 7 天 GMV", "GMV 变化", "变化幅度", "前 7 天销量", "最近 7 天销量"]
    for col in ["前 7 天 GMV", "最近 7 天 GMV", "GMV 变化"]:
        display[col] = display[col].map(lambda x: money(x, 0))
    display["变化幅度"] = display["变化幅度"].map(lambda x: "—" if pd.isna(x) else f"{x:.2f}%")
    display["前 7 天销量"] = display["前 7 天销量"].map(number)
    display["最近 7 天销量"] = display["最近 7 天销量"].map(number)
    section_title("下滑 SKU 清单", "优先看 GMV 绝对损失，同时结合百分比判断影响程度")
    styled_table(display, height=440)
    st.download_button("下载下滑 SKU 清单 CSV", df.to_csv(index=False, encoding="utf-8-sig"), file_name="sku_gmv_declines.csv", mime="text/csv")
    st.markdown('<div class="notice">下一步排查建议：分别核对访客数、转化率、当前售价/竞品价格、活动状态和库存。仅凭 GMV 下降无法确定根本原因。</div>', unsafe_allow_html=True)


def render_prices() -> None:
    section_title("竞品价格竞争力", "标记本商品价格高于竞品的 SKU，并展示简单单位毛利空间")
    min_gap = st.slider("最低高价幅度（%）", min_value=0, max_value=30, value=0, step=1, help="例如设置为 5，只查看本商品售价至少高于竞品 5% 的 SKU。")
    records = get_competitor_price_gaps(top_n=100, min_gap_pct=float(min_gap))
    df = pd.DataFrame(records)
    if df.empty:
        st.success("当前阈值下没有价格高于竞品的商品。")
        return
    top = df.iloc[0]
    c = st.columns(3, gap="medium")
    with c[0]: kpi_card("最大价格差", f"+{top['price_gap_pct']:.1f}%", str(top["product_name"]), "↗", RED)
    with c[1]: kpi_card("当前商品售价", money(top["current_price"], 0), f"SKU：{top['sku']}", "￥", ORANGE)
    with c[2]: kpi_card("竞品价格", money(top["competitor_price"], 0), str(top["competitor_name"]), "⇄", "#64748B")
    chart_df = df.head(10).sort_values("price_gap_pct")
    section_title("价格差距 Top 10", "仅展示价差，不代表商品规格完全一致或一定应该降价")
    fig = px.bar(chart_df, x="price_gap_pct", y="product_name", orientation="h", text=chart_df["price_gap_pct"].map(lambda x: f"+{x:.1f}%"), color="price_gap_pct", color_continuous_scale=["#F9B7B3", RED])
    fig.update_layout(coloraxis_showscale=False, xaxis_title="高于竞品幅度（%）", yaxis_title="", showlegend=False)
    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>高于竞品：%{x:.2f}%<extra></extra>")
    chart_layout(fig, 360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    display = df[["sku", "product_name", "category", "competitor_name", "current_price", "competitor_price", "price_gap_pct", "estimated_unit_gross_profit_at_current_price", "estimated_unit_gross_profit_at_competitor_price"]].copy()
    display.columns = ["SKU", "商品名称", "品类", "竞品平台", "本商品售价", "竞品售价", "高于竞品", "当前单位毛利（简化）", "按竞品价单位毛利（简化）"]
    for col in ["本商品售价", "竞品售价", "当前单位毛利（简化）", "按竞品价单位毛利（简化）"]:
        display[col] = display[col].map(lambda x: money(x, 0))
    display["高于竞品"] = display["高于竞品"].map(lambda x: f"+{x:.2f}%")
    section_title("价格差异明细", "按价格差距从高到低排列")
    styled_table(display, height=420)
    st.download_button("下载竞品价格清单 CSV", df.to_csv(index=False, encoding="utf-8-sig"), file_name="competitor_price_gap.csv", mime="text/csv")
    st.markdown('<div class="notice">风险提示：竞品规格、服务、优惠条件可能不同；当前单位毛利为售价减商品成本的简化估算，未计平台佣金、优惠成本、物流等费用。不要依据这一张表自动调价。</div>', unsafe_allow_html=True)


def render_inventory() -> None:
    section_title("库存健康与风险预警", "依据当前模拟库存、近 7 天日均销量及供应商交期识别风险")
    status_option = st.selectbox("库存状态", ["全部风险", "缺货风险", "滞销风险"], key="inventory_status_filter")
    status = None if status_option == "全部风险" else status_option
    records = get_inventory_risks(status=status, top_n=100)
    df = pd.DataFrame(records)
    if df.empty:
        st.success("当前条件下没有库存风险 SKU。")
        return
    stockout = int((df["inventory_status"] == "缺货风险").sum())
    slow = int((df["inventory_status"] == "滞销风险").sum())
    critical = int((df["stock_cover_days"] < df["supplier_lead_days"]).sum())
    c = st.columns(3, gap="medium")
    with c[0]: kpi_card("缺货风险 SKU", number(stockout), "当前筛选结果", "!", RED)
    with c[1]: kpi_card("滞销风险 SKU", number(slow), "当前筛选结果", "◷", ORANGE)
    with c[2]: kpi_card("覆盖天数低于交期", number(critical), "建议优先核实供应计划", "⌛", RED)
    display = df[["sku", "product_name", "category", "inventory_status", "current_stock", "avg_daily_sales_7d", "stock_cover_days", "supplier_lead_days", "safety_stock"]].copy()
    display.columns = ["SKU", "商品名称", "品类", "库存状态", "当前库存", "近 7 天日均销量", "库存覆盖天数", "供应商交期（天）", "安全库存"]
    display["近 7 天日均销量"] = display["近 7 天日均销量"].map(lambda x: f"{x:.2f}")
    display["库存覆盖天数"] = display["库存覆盖天数"].map(lambda x: f"{x:.1f} 天")
    section_title("风险 SKU 清单", "库存覆盖天数低于供应商交期的商品建议优先确认")
    styled_table(display, height=420)
    st.download_button("下载库存风险清单 CSV", df.to_csv(index=False, encoding="utf-8-sig"), file_name="inventory_risks.csv", mime="text/csv")
    st.markdown('<div class="notice">库存预警只用于辅助检查。真实补货还需要考虑在途库存、采购起订量、仓库分布、需求波动与供应商交期可靠性。</div>', unsafe_allow_html=True)



def load_sku_detail_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读取单品诊断所需的本地模拟数据。"""
    required = {
        "products": DATA_DIR / "products.csv",
        "sales": DATA_DIR / "sales_daily.csv",
        "competitors": DATA_DIR / "competitor_prices.csv",
        "inventory": DATA_DIR / "inventory.csv",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("单品诊断所需文件不存在：" + ", ".join(missing))
    products = pd.read_csv(required["products"], encoding="utf-8-sig")
    sales = pd.read_csv(required["sales"], encoding="utf-8-sig", parse_dates=["date"])
    competitors = pd.read_csv(required["competitors"], encoding="utf-8-sig")
    inventory = pd.read_csv(required["inventory"], encoding="utf-8-sig")
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    for col in ["visitors", "add_to_cart", "orders", "units_sold", "sale_price", "gmv", "gross_profit"]:
        if col in sales.columns:
            sales[col] = pd.to_numeric(sales[col], errors="coerce").fillna(0)
    return products, sales, competitors, inventory


def _sku_period_metrics(frame: pd.DataFrame) -> dict:
    gmv = float(frame["gmv"].sum()) if not frame.empty else 0.0
    profit = float(frame["gross_profit"].sum()) if not frame.empty else 0.0
    visitors = int(frame["visitors"].sum()) if not frame.empty else 0
    carts = int(frame["add_to_cart"].sum()) if "add_to_cart" in frame.columns and not frame.empty else 0
    orders = int(frame["orders"].sum()) if not frame.empty else 0
    units = int(frame["units_sold"].sum()) if not frame.empty else 0
    avg_price = gmv / units if units else None
    return {
        "gmv": gmv, "gross_profit": profit, "visitors": visitors, "add_to_cart": carts,
        "orders": orders, "units_sold": units,
        "conversion_rate": orders / visitors if visitors else None,
        "add_to_cart_rate": carts / visitors if visitors else None,
        "cart_to_order_rate": orders / carts if carts else None,
        "avg_realized_price": avg_price,
        "gross_margin_rate": profit / gmv if gmv else None,
    }


def _change_pct(current: float | int | None, previous: float | int | None) -> float | None:
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / previous * 100


def render_sku_diagnosis() -> None:
    """单 SKU 诊断：周期对比、流量漏斗、价格/库存上下文与审慎提示。"""
    products, sales, competitors, inventory = load_sku_detail_data()
    section_title("单品诊断", "从销售变化进入商品级排查：流量、加购、转化、价格与库存一起看")
    st.markdown('<div class="info-strip">本页用于定位需要进一步核查的信号，不会仅凭相关指标变化就断言根本原因；当前数据全部为模拟数据。</div>', unsafe_allow_html=True)

    product_options = products.sort_values("sku")["sku"].tolist()
    product_names = products.set_index("sku")["product_name"].to_dict()
    if "diagnosis_sku" not in st.session_state or st.session_state["diagnosis_sku"] not in product_options:
        st.session_state["diagnosis_sku"] = product_options[0]
    sku = st.selectbox(
        "选择需要诊断的商品",
        options=product_options,
        format_func=lambda code: f"{code}  |  {product_names.get(code, '')}",
        key="diagnosis_sku",
    )
    product_row = products.loc[products["sku"] == sku].iloc[0]
    item_sales = sales.loc[sales["sku"] == sku].copy().sort_values("date")
    if item_sales.empty:
        st.warning("这个 SKU 暂无销售记录。")
        return

    latest = sales["date"].max().normalize()
    recent_start = latest - pd.Timedelta(days=6)
    previous_end = recent_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=6)
    recent = item_sales[(item_sales["date"] >= recent_start) & (item_sales["date"] <= latest)]
    previous = item_sales[(item_sales["date"] >= previous_start) & (item_sales["date"] <= previous_end)]
    cur = _sku_period_metrics(recent)
    prev = _sku_period_metrics(previous)
    gmv_delta_pct = _change_pct(cur["gmv"], prev["gmv"])
    visitors_delta_pct = _change_pct(cur["visitors"], prev["visitors"])
    carts_delta_pct = _change_pct(cur["add_to_cart"], prev["add_to_cart"])
    orders_delta_pct = _change_pct(cur["orders"], prev["orders"])
    conv_delta_pp = None if cur["conversion_rate"] is None or prev["conversion_rate"] is None else (cur["conversion_rate"] - prev["conversion_rate"]) * 100

    competitor = competitors.loc[competitors["sku"] == sku]
    comp_price = float(competitor.iloc[0]["competitor_price"]) if not competitor.empty else None
    comp_name = str(competitor.iloc[0]["competitor_name"]) if not competitor.empty else "暂无竞品数据"
    current_price = float(product_row["current_price"])
    price_gap_pct = None if comp_price in (None, 0) else (current_price - comp_price) / comp_price * 100
    inv = inventory.loc[inventory["sku"] == sku]
    inv_row = inv.iloc[0] if not inv.empty else None

    st.markdown(
        f'<div class="panel" style="margin:12px 0 16px 0;"><div class="panel-title">{html.escape(str(product_row["product_name"]))}</div>'
        f'<div class="panel-desc">SKU：{html.escape(str(sku))}　·　品类：{html.escape(str(product_row["category"]))}　·　品牌：{html.escape(str(product_row["brand"]))}</div>'
        f'<div style="font-size:12px;color:#687385;">对比周期：{previous_start:%Y-%m-%d} 至 {previous_end:%Y-%m-%d}　→　{recent_start:%Y-%m-%d} 至 {latest:%Y-%m-%d}</div></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(4, gap="medium")
    with cols[0]: kpi_card("最近 7 天 GMV", money(cur["gmv"], 0), f"前 7 天 {money(prev['gmv'], 0)}", "¥", RED)
    with cols[1]: kpi_card("GMV 环比", "—" if gmv_delta_pct is None else f"{gmv_delta_pct:+.2f}%", "仅描述周期变化", "↗" if (gmv_delta_pct or 0) >= 0 else "↘", GREEN if (gmv_delta_pct or 0) >= 0 else RED)
    with cols[2]: kpi_card("最近 7 天访客", number(cur["visitors"]), "商品级累计访客", "◉", "#64748B")
    with cols[3]: kpi_card("支付转化率", pct(cur["conversion_rate"]), "订单数 ÷ 访客数", "◎", ORANGE)

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        section_title("最近 30 天销售趋势", "查看该 SKU 的每日 GMV 和销量变化")
        trend_start = latest - pd.Timedelta(days=29)
        trend = item_sales[(item_sales["date"] >= trend_start) & (item_sales["date"] <= latest)].copy()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend["date"], y=trend["gmv"], name="每日 GMV", mode="lines+markers", line=dict(color=RED, width=2.5), fill="tozeroy", fillcolor="rgba(225,37,27,.08)"))
        fig.update_layout(title="每日 GMV", xaxis_title="日期", yaxis_title="GMV（元）", hovermode="x unified")
        chart_layout(fig, 320)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        section_title("商品流量漏斗", "最近 7 天 vs 前 7 天")
        funnel = pd.DataFrame([
            {"指标": "访客", "前 7 天": prev["visitors"], "最近 7 天": cur["visitors"]},
            {"指标": "加购", "前 7 天": prev["add_to_cart"], "最近 7 天": cur["add_to_cart"]},
            {"指标": "订单", "前 7 天": prev["orders"], "最近 7 天": cur["orders"]},
        ])
        fig2 = px.bar(funnel, x="指标", y=["前 7 天", "最近 7 天"], barmode="group", color_discrete_sequence=["#C9CED8", RED], text_auto=True)
        fig2.update_layout(title="流量到订单的数量对比", xaxis_title="", yaxis_title="数量", legend_title="")
        chart_layout(fig2, 320)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    section_title("关键指标对比", "注意区分数量变化、转化率变化和实际成交均价")
    def metric_pct(current, previous):
        value = _change_pct(current, previous)
        return "—" if value is None else f"{value:+.2f}%"
    metric_rows = [
        {"指标": "GMV", "前 7 天": money(prev["gmv"]), "最近 7 天": money(cur["gmv"]), "环比": metric_pct(cur["gmv"], prev["gmv"])},
        {"指标": "毛利额", "前 7 天": money(prev["gross_profit"]), "最近 7 天": money(cur["gross_profit"]), "环比": metric_pct(cur["gross_profit"], prev["gross_profit"])},
        {"指标": "访客数", "前 7 天": number(prev["visitors"]), "最近 7 天": number(cur["visitors"]), "环比": metric_pct(cur["visitors"], prev["visitors"])},
        {"指标": "加购数", "前 7 天": number(prev["add_to_cart"]), "最近 7 天": number(cur["add_to_cart"]), "环比": metric_pct(cur["add_to_cart"], prev["add_to_cart"])},
        {"指标": "订单数", "前 7 天": number(prev["orders"]), "最近 7 天": number(cur["orders"]), "环比": metric_pct(cur["orders"], prev["orders"])},
        {"指标": "加购率", "前 7 天": pct(prev["add_to_cart_rate"]), "最近 7 天": pct(cur["add_to_cart_rate"]), "变化": "—" if cur["add_to_cart_rate"] is None or prev["add_to_cart_rate"] is None else f"{(cur['add_to_cart_rate'] - prev['add_to_cart_rate']) * 100:+.3f} 个百分点"},
        {"指标": "支付转化率", "前 7 天": pct(prev["conversion_rate"]), "最近 7 天": pct(cur["conversion_rate"]), "变化": "—" if conv_delta_pp is None else f"{conv_delta_pp:+.3f} 个百分点"},
        {"指标": "实际成交均价（GMV ÷ 销量）", "前 7 天": money(prev["avg_realized_price"]), "最近 7 天": money(cur["avg_realized_price"]), "环比": metric_pct(cur["avg_realized_price"], prev["avg_realized_price"])},
    ]
    styled_table(pd.DataFrame(metric_rows), height=330)

    left, right = st.columns(2, gap="large")
    with left:
        section_title("价格竞争力", "挂牌价与当前竞品快照对比")
        price_cols = st.columns(2)
        with price_cols[0]: kpi_card("商品当前标价", money(current_price), f"单位成本 {money(float(product_row['unit_cost']))}", "￥", ORANGE)
        with price_cols[1]: kpi_card("竞品价差", "—" if price_gap_pct is None else f"{price_gap_pct:+.1f}%", comp_name, "⇄", RED if (price_gap_pct or 0) > 0 else GREEN)
        if comp_price is not None:
            st.caption(f"按当前商品标价与竞品快照计算：{money(current_price)} 对比 {money(comp_price)}。价差为正表示本商品更贵。")
        else:
            st.info("暂无可用竞品价格记录。")
    with right:
        section_title("库存与供应信息", "使用当前库存快照进行风险提示")
        if inv_row is not None:
            inv_cols = st.columns(3)
            with inv_cols[0]: kpi_card("库存状态", str(inv_row["inventory_status"]), f"当前库存 {number(inv_row['current_stock'])}", "▣", RED if str(inv_row["inventory_status"]) != "正常" else GREEN)
            with inv_cols[1]: kpi_card("库存覆盖", f"{float(inv_row['stock_cover_days']):.1f} 天", f"供应交期 {int(inv_row['supplier_lead_days'])} 天", "⌛", RED if float(inv_row["stock_cover_days"]) < float(inv_row["supplier_lead_days"]) else GREEN)
            with inv_cols[2]: kpi_card("安全库存", number(inv_row["safety_stock"]), "需结合在途库存核实", "▤", ORANGE)
        else:
            st.info("暂无可用库存记录。")

    section_title("排查线索与建议", "规则生成的检查清单，不是已证实的因果诊断")
    hints = []
    if visitors_delta_pct is not None and visitors_delta_pct <= -10:
        hints.append(("流量信号", f"访客环比下降 {abs(visitors_delta_pct):.1f}%，建议核对搜索曝光、广告投放、活动入口和商品页流量来源。"))
    if carts_delta_pct is not None and carts_delta_pct <= -10:
        hints.append(("加购信号", f"加购数环比下降 {abs(carts_delta_pct):.1f}%，建议检查商品卖点、评价、页面内容和促销权益。"))
    if conv_delta_pp is not None and conv_delta_pp <= -0.3:
        hints.append(("转化信号", f"支付转化率下降 {abs(conv_delta_pp):.2f} 个百分点，建议核查到手价、优惠门槛、配送时效及商品页面。"))
    if price_gap_pct is not None and price_gap_pct >= 5:
        hints.append(("价格信号", f"当前标价高于竞品快照 {price_gap_pct:.1f}%。先核对型号、规格、服务和优惠口径，再做价格测算；不要据此直接降价。"))
    if inv_row is not None and float(inv_row["stock_cover_days"]) < float(inv_row["supplier_lead_days"]):
        hints.append(("库存信号", f"库存覆盖约 {float(inv_row['stock_cover_days']):.1f} 天，低于供应商交期 {int(inv_row['supplier_lead_days'])} 天，建议优先核实在途库存和补货计划。"))
    if gmv_delta_pct is not None and gmv_delta_pct < 0:
        hints.append(("经营变化", f"GMV 环比下降 {abs(gmv_delta_pct):.1f}%。建议按访客 → 加购 → 订单漏斗逐层排查，而不是直接归因于价格。"))
    if not hints:
        hints.append(("暂未发现明显异常", "当前规则没有发现达到预设阈值的单一异常信号。仍建议结合活动、广告、评价、竞品口径和库存变化人工复核。"))
    for tag, body in hints:
        st.markdown(f'<div class="panel" style="padding:12px 14px;margin:8px 0;"><span style="display:inline-block;border-radius:6px;background:#FFF0EF;color:#B91C1C;padding:3px 7px;font-size:11px;font-weight:800;margin-right:8px;">{html.escape(tag)}</span><span style="font-size:13px;line-height:1.7;color:#394456;">{html.escape(body)}</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="notice">分析边界：本页面基于模拟数据和固定规则生成排查线索，不使用大模型，也不能证明因果。正式经营中还应核实数据口径、活动、广告、评价、在途库存与竞品规格。</div>', unsafe_allow_html=True)


def build_sku_priority_table() -> pd.DataFrame:
    """用可解释的规则为 SKU 排定排查优先级；不是因果模型。"""
    products, sales, competitors, inventory = load_sku_detail_data()
    latest = sales["date"].max().normalize()
    recent_start = latest - pd.Timedelta(days=6)
    previous_end = recent_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=6)
    recent = sales[(sales["date"] >= recent_start) & (sales["date"] <= latest)]
    previous = sales[(sales["date"] >= previous_start) & (sales["date"] <= previous_end)]

    cur = recent.groupby("sku", as_index=False).agg(
        recent_gmv=("gmv", "sum"), recent_gross_profit=("gross_profit", "sum"), recent_units=("units_sold", "sum")
    )
    prev = previous.groupby("sku", as_index=False).agg(
        previous_gmv=("gmv", "sum"), previous_units=("units_sold", "sum")
    )
    df = products.merge(cur, on="sku", how="left").merge(prev, on="sku", how="left")
    df = df.merge(competitors[["sku", "competitor_name", "competitor_price"]], on="sku", how="left")
    df = df.merge(inventory[["sku", "current_stock", "stock_cover_days", "supplier_lead_days", "safety_stock", "inventory_status"]], on="sku", how="left")
    for col in ["recent_gmv", "recent_gross_profit", "recent_units", "previous_gmv", "previous_units"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["gmv_change"] = df["recent_gmv"] - df["previous_gmv"]
    df["gmv_change_pct"] = df.apply(
        lambda row: ((row["recent_gmv"] - row["previous_gmv"]) / row["previous_gmv"] * 100)
        if row["previous_gmv"] else None,
        axis=1,
    )
    df["price_gap_pct"] = df.apply(
        lambda row: ((row["current_price"] - row["competitor_price"]) / row["competitor_price"] * 100)
        if pd.notna(row["competitor_price"]) and float(row["competitor_price"]) > 0 else 0.0,
        axis=1,
    )
    df["recent_gross_margin_rate"] = df.apply(
        lambda row: row["recent_gross_profit"] / row["recent_gmv"] if row["recent_gmv"] else 0.0,
        axis=1,
    )

    # 四类可解释信号，共 100 分：相对 GMV 下滑 30、绝对 GMV 损失 20、竞品价差 25、库存状态 25。
    decline = (-pd.to_numeric(df["gmv_change_pct"], errors="coerce").fillna(0)).clip(lower=0)
    df["score_gmv_decline"] = (decline / 20 * 30).clip(upper=30)
    loss = (-df["gmv_change"]).clip(lower=0)
    max_loss = float(loss.max()) if not loss.empty else 0.0
    df["score_gmv_loss"] = (loss / max_loss * 20) if max_loss > 0 else 0.0
    df["score_price_gap"] = (df["price_gap_pct"].clip(lower=0) / 20 * 25).clip(upper=25)
    df["score_inventory"] = df["inventory_status"].map({"缺货风险": 25, "滞销风险": 12, "正常": 0}).fillna(0)
    df["priority_score"] = (df["score_gmv_decline"] + df["score_gmv_loss"] + df["score_price_gap"] + df["score_inventory"]).clip(0, 100).round(1)

    def priority_level(score: float) -> str:
        if score >= 70:
            return "P0-紧急"
        if score >= 45:
            return "P1-高"
        if score >= 25:
            return "P2-中"
        return "P3-常规"

    def explain(row) -> tuple[str, str]:
        reasons = []
        pct_change = row["gmv_change_pct"]
        if pd.notna(pct_change) and pct_change <= -10:
            reasons.append(f"GMV下降{abs(pct_change):.1f}%")
        elif row["gmv_change"] < 0:
            reasons.append("GMV下降")
        if row["price_gap_pct"] >= 5:
            reasons.append(f"高于竞品{row['price_gap_pct']:.1f}%")
        if row["inventory_status"] == "缺货风险":
            reasons.append("缺货风险")
        elif row["inventory_status"] == "滞销风险":
            reasons.append("滞销风险")

        if row["inventory_status"] == "缺货风险":
            action = "优先核实在途库存与采购交期；促销扩量前先确认可供货量。"
        elif row["inventory_status"] == "滞销风险":
            action = "检查库存周转与需求；如考虑清货，先设置最低毛利底线。"
        elif pd.notna(pct_change) and pct_change <= -10 and row["price_gap_pct"] >= 5:
            action = "同步核查流量与转化；再模拟保毛利的价格/优惠方案。"
        elif row["price_gap_pct"] >= 5:
            action = "核对同规格与到手价口径，测算毛利底线内的促销空间。"
        elif pd.notna(pct_change) and pct_change <= -5:
            action = "检查访客、加购、支付转化、活动与评价变化，不要直接归因。"
        else:
            action = "保持常规监控；优先级来自规则信号，不代表已经确认问题。"
        return ("；".join(reasons) if reasons else "暂无突出风险信号", action)

    reason_action = df.apply(explain, axis=1)
    df["priority_reason"] = [x[0] for x in reason_action]
    df["suggested_action"] = [x[1] for x in reason_action]
    df["priority_level"] = df["priority_score"].map(priority_level)
    df["recent_period"] = f"{recent_start:%Y-%m-%d} 至 {latest:%Y-%m-%d}"
    df["previous_period"] = f"{previous_start:%Y-%m-%d} 至 {previous_end:%Y-%m-%d}"
    return df.sort_values(["priority_score", "gmv_change"], ascending=[False, True]).reset_index(drop=True)


def render_promotion_simulator(category_filter: str | None = None) -> None:
    """透明的静态促销情景模拟；销量提升率为人为假设，不是模型预测。"""
    products, sales, _, _ = load_sku_detail_data()
    section_title("促销利润模拟", "调整折扣、预期销量提升、商家补贴与预算，测算 GMV 和毛利影响")
    st.markdown('<div class="notice">模拟口径：以该 SKU 最近 7 天实际成交均价和销量作为基线；销量提升率由你手动假设，不是模型预测，也不代表真实促销因果效果。</div>', unsafe_allow_html=True)

    categories = ["全部品类"] + sorted(products["category"].dropna().unique().tolist())
    category_key = "promotion_category_filter"
    category_default = categories.index(category_filter) if category_filter in categories else 0
    chosen_category = st.selectbox("先筛选品类", categories, index=category_default, key=category_key)
    options_df = products if chosen_category == "全部品类" else products[products["category"] == chosen_category]
    options_df = options_df.sort_values("sku")
    name_map = options_df.set_index("sku")["product_name"].to_dict()
    if options_df.empty:
        st.info("当前品类下暂无商品。")
        return
    selected_sku = st.selectbox(
        "选择模拟商品", options_df["sku"].tolist(),
        format_func=lambda code: f"{code}｜{name_map.get(code, '')}", key="promotion_sku",
    )
    product = products.loc[products["sku"] == selected_sku].iloc[0]
    latest = sales["date"].max().normalize()
    start = latest - pd.Timedelta(days=6)
    item_recent = sales[(sales["sku"] == selected_sku) & (sales["date"] >= start) & (sales["date"] <= latest)]
    base = _sku_period_metrics(item_recent)
    baseline_units = int(base["units_sold"])
    baseline_gmv = float(base["gmv"])
    baseline_gp = float(base["gross_profit"])
    baseline_avg_price = float(base["avg_realized_price"] or product["current_price"])
    unit_cost = float(product["unit_cost"])

    left, right = st.columns([1, 1], gap="large")
    with left:
        section_title("促销参数", "请把它当作情景假设，后续可用实际活动数据校准")
        discount_pct = st.slider("相对近期成交均价的额外折扣（%）", min_value=0, max_value=35, value=5, step=1, key="promo_discount")
        lift_pct = st.slider("预期销量提升（%）", min_value=-20, max_value=200, value=20, step=5, key="promo_lift")
        subsidy_per_unit = st.number_input("商家额外承担的单件优惠/营销成本（元）", min_value=0.0, max_value=1000.0, value=0.0, step=1.0, key="promo_subsidy")
        budget_cap = st.number_input("活动预算上限（元）", min_value=0.0, max_value=100000000.0, value=5000.0, step=500.0, key="promo_budget")
        min_margin_pct = st.slider("最低目标毛利率（%）", min_value=0, max_value=50, value=10, step=1, key="promo_min_margin")
    with right:
        section_title("商品当前基线", f"最近 7 天：{start:%Y-%m-%d} 至 {latest:%Y-%m-%d}")
        base_cols = st.columns(2)
        with base_cols[0]: kpi_card("近期成交均价", money(baseline_avg_price), "GMV ÷ 销量", "￥", ORANGE)
        with base_cols[1]: kpi_card("近期销量", number(baseline_units), "最近 7 天", "▦", RED)
        base_cols2 = st.columns(2)
        with base_cols2[0]: kpi_card("近期 GMV", money(baseline_gmv, 0), "最近 7 天实际值", "↗", RED)
        with base_cols2[1]: kpi_card("近期毛利额", money(baseline_gp, 0), "数据表中的实际模拟值", "￥", GREEN)
        st.caption(f"商品标价：{money(float(product['current_price']))}；单位成本：{money(unit_cost)}。当前情景的折扣基于近期实际成交均价，而非挂牌价。")

    scenario_price = baseline_avg_price * (1 - discount_pct / 100)
    projected_units = max(0, int(round(baseline_units * (1 + lift_pct / 100))))
    scenario_unit_profit = scenario_price - unit_cost - float(subsidy_per_unit)
    scenario_gmv = projected_units * scenario_price
    scenario_gp = projected_units * scenario_unit_profit
    scenario_margin = scenario_gp / scenario_gmv if scenario_gmv > 0 else 0.0
    discount_spend = max(0.0, baseline_avg_price - scenario_price) * projected_units
    subsidy_spend = float(subsidy_per_unit) * projected_units
    promo_spend = discount_spend + subsidy_spend
    gmv_delta = scenario_gmv - baseline_gmv
    gp_delta = scenario_gp - baseline_gp
    gmv_delta_pct = (gmv_delta / baseline_gmv * 100) if baseline_gmv else None
    gp_delta_pct = (gp_delta / abs(baseline_gp) * 100) if baseline_gp else None
    feasible_margin = scenario_margin * 100 >= min_margin_pct
    feasible_budget = promo_spend <= budget_cap

    section_title("模拟结果", "情景值不等于预测值；请关注毛利变化、毛利率和预算是否达标")
    cols = st.columns(4, gap="medium")
    with cols[0]: kpi_card("模拟 GMV", money(scenario_gmv, 0), f"相对基线 {gmv_delta_pct:+.1f}%" if gmv_delta_pct is not None else "无基线 GMV", "￥", GREEN if gmv_delta >= 0 else RED)
    with cols[1]: kpi_card("模拟毛利额", money(scenario_gp, 0), f"相对基线 {gp_delta:+,.0f} 元", "￥", GREEN if gp_delta >= 0 else RED)
    with cols[2]: kpi_card("模拟毛利率", pct(scenario_margin), f"目标不低于 {min_margin_pct}%", "%", GREEN if feasible_margin else RED)
    with cols[3]: kpi_card("预计促销投入", money(promo_spend, 0), f"预算上限 {money(budget_cap, 0)}", "▤", GREEN if feasible_budget else RED)

    if feasible_margin and feasible_budget and scenario_unit_profit >= 0:
        st.success("当前参数满足你设置的毛利率和预算约束。建议将此方案作为待审核备选方案，而非直接执行。")
    else:
        issues = []
        if not feasible_margin:
            issues.append(f"模拟毛利率低于目标 {min_margin_pct}%")
        if not feasible_budget:
            issues.append("预计促销投入超出预算上限")
        if scenario_unit_profit < 0:
            issues.append("扣除商家补贴后的单件毛利为负")
        st.warning("；".join(issues) + "。请调低折扣、减少补贴或重新评估销量假设。")

    if scenario_unit_profit > 0 and baseline_gp > 0 and baseline_units > 0:
        units_to_match_gp = math.ceil(baseline_gp / scenario_unit_profit)
        required_lift = (units_to_match_gp / baseline_units - 1) * 100
        st.caption(f"按当前模拟单件毛利估算，为达到/超过最近 7 天基线毛利额，约需销量 {units_to_match_gp} 件（相对基线需提升约 {required_lift:.1f}%）。这是算术盈亏门槛，不是销量预测。")
    else:
        st.caption("当前模拟单件毛利不为正，或基线条件不足，无法计算维持基线毛利额所需销量。")

    compare_df = pd.DataFrame([
        {"指标": "GMV", "近期 7 天基线": baseline_gmv, "促销情景": scenario_gmv, "变化": gmv_delta},
        {"指标": "毛利额", "近期 7 天基线": baseline_gp, "促销情景": scenario_gp, "变化": gp_delta},
        {"指标": "销量", "近期 7 天基线": baseline_units, "促销情景": projected_units, "变化": projected_units - baseline_units},
        {"指标": "平均成交价", "近期 7 天基线": baseline_avg_price, "促销情景": scenario_price, "变化": scenario_price - baseline_avg_price},
    ])
    display_compare = compare_df.copy()
    for col in ["近期 7 天基线", "促销情景", "变化"]:
        display_compare[col] = display_compare[col].map(lambda x: f"{x:,.2f}" if pd.notna(x) else "—")
    styled_table(display_compare, height=220)

    scenario_record = pd.DataFrame([{
        "sku": selected_sku, "product_name": product["product_name"], "recent_baseline_units_7d": baseline_units,
        "recent_baseline_gmv_7d": round(baseline_gmv, 2), "recent_baseline_gross_profit_7d": round(baseline_gp, 2),
        "baseline_avg_realized_price": round(baseline_avg_price, 2), "discount_pct": discount_pct,
        "assumed_units_lift_pct": lift_pct, "seller_subsidy_per_unit": subsidy_per_unit,
        "projected_units": projected_units, "projected_gmv": round(scenario_gmv, 2),
        "projected_gross_profit": round(scenario_gp, 2), "projected_gross_margin_rate": round(scenario_margin, 4),
        "estimated_promo_spend": round(promo_spend, 2), "budget_cap": budget_cap,
        "min_margin_target_pct": min_margin_pct, "budget_feasible": feasible_budget, "margin_feasible": feasible_margin,
    }])
    st.download_button("下载当前促销情景 CSV", scenario_record.to_csv(index=False, encoding="utf-8-sig"), file_name=f"promotion_scenario_{selected_sku}.csv", mime="text/csv")
    st.markdown('<div class="notice">注意：该模拟未纳入平台佣金、物流、退货、税费、流量投放等全部费用；销量提升率由用户手动输入，未经历史活动数据回测。所有方案都需要人工复核。</div>', unsafe_allow_html=True)


def render_priorities(category_filter: str | None = None) -> None:
    """将 GMV 下滑、绝对损失、竞品价差和库存风险汇总成可解释优先级。"""
    df = build_sku_priority_table()
    section_title("商品运营优先级", "把经营风险合并成可解释的排查清单，帮助决定先看哪个 SKU")
    st.markdown('<div class="notice">分数是启发式规则：GMV 相对下滑 30 分、绝对损失 20 分、竞品价差 25 分、库存状态 25 分。它用于安排排查顺序，不是模型预测，也不意味着已经证明问题原因。</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        categories = ["全部品类"] + sorted(df["category"].dropna().unique().tolist())
        default = categories.index(category_filter) if category_filter in categories else 0
        selected_category = st.selectbox("品类筛选", categories, index=default, key="priority_category_filter")
    with c2:
        min_score = st.slider("最低优先级分数", min_value=0, max_value=100, value=0, step=5, key="priority_min_score")
    filtered = df.copy()
    if selected_category != "全部品类":
        filtered = filtered[filtered["category"] == selected_category]
    filtered = filtered[filtered["priority_score"] >= min_score].sort_values("priority_score", ascending=False)
    count_p0 = int((df["priority_level"] == "P0-紧急").sum())
    count_p1 = int((df["priority_level"] == "P1-高").sum())
    count_stock = int((df["inventory_status"] == "缺货风险").sum())
    count_price = int((df["price_gap_pct"] >= 5).sum())
    cards = st.columns(4, gap="medium")
    with cards[0]: kpi_card("P0 紧急", number(count_p0), "综合评分 ≥ 70", "!", RED)
    with cards[1]: kpi_card("P1 高优先级", number(count_p1), "综合评分 45–69.9", "↗", ORANGE)
    with cards[2]: kpi_card("缺货风险 SKU", number(count_stock), "当前库存快照", "▣", RED)
    with cards[3]: kpi_card("价差 ≥ 5% SKU", number(count_price), "当前标价高于竞品快照", "⇄", ORANGE)

    if filtered.empty:
        st.info("当前筛选条件下没有符合条件的商品。")
        return
    chart_df = filtered.head(12).copy().sort_values("priority_score", ascending=True)
    section_title("优先处理 Top 12", "分数越高代表同时出现的规则信号越多/越强")
    fig = px.bar(chart_df, x="priority_score", y="sku", orientation="h", color="priority_score", text="priority_score", color_continuous_scale=["#F9C7C3", RED])
    fig.update_layout(coloraxis_showscale=False, xaxis_title="规则评分（0–100）", yaxis_title="SKU", showlegend=False, xaxis_range=[0, 105])
    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>优先级评分：%{x:.1f}<extra></extra>")
    chart_layout(fig, max(340, len(chart_df) * 29))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    show = filtered.head(100).copy()
    display = show[["priority_level", "priority_score", "sku", "product_name", "category", "gmv_change", "gmv_change_pct", "price_gap_pct", "inventory_status", "priority_reason", "suggested_action"]].copy()
    display.columns = ["优先级", "评分", "SKU", "商品名称", "品类", "GMV变化", "GMV变化幅度", "高于竞品", "库存状态", "主要信号", "建议排查动作"]
    display["GMV变化"] = display["GMV变化"].map(lambda x: money(x, 0))
    display["GMV变化幅度"] = display["GMV变化幅度"].map(lambda x: "—" if pd.isna(x) else f"{x:+.1f}%")
    display["高于竞品"] = display["高于竞品"].map(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
    section_title("SKU 优先级明细", "可按品类或最低评分筛选，下载后用于复盘或面试作品集展示")
    styled_table(display, height=470)
    st.download_button("下载商品运营优先级清单 CSV", show.to_csv(index=False, encoding="utf-8-sig"), file_name="sku_operation_priority.csv", mime="text/csv")
    st.markdown('<div class="notice">执行建议：先核实数据与库存，再做价格或促销决策。缺货风险商品不应仅因高分就扩大促销；建议仅作为待确认任务，不自动执行调价或采购。</div>', unsafe_allow_html=True)


def render_task(task: str, category: str | None = None) -> None:
    if task == "periods":
        render_periods()
    elif task == "category":
        render_categories()
    elif task == "declines":
        render_declines(category)
    elif task == "price":
        render_prices()
    elif task == "inventory":
        render_inventory()
    elif task == "sku_diagnosis":
        render_sku_diagnosis()
    elif task == "promotion":
        render_promotion_simulator(category)
    elif task == "priorities":
        render_priorities(category)
    else:
        render_overview()

# -------------------------- 侧边栏导航 --------------------------
with st.sidebar:
    st.markdown(
        f'<div class="brand-mark"><div class="brand-logo">J</div><div><div class="brand-name">经营分析中台</div><div class="brand-sub">3C MERCHANDISING INSIGHT</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-section">工作空间 / WORKSPACE</div>', unsafe_allow_html=True)
    page_labels = {
        "总览驾驶舱": "overview",
        "周期经营对比": "periods",
        "品类经营分析": "category",
        "商品下滑诊断": "declines",
        "竞品价格分析": "price",
        "库存风险预警": "inventory",
        "单品诊断": "sku_diagnosis",
        "促销利润模拟": "promotion",
        "商品运营优先级": "priorities",
    }
    selected_label = st.radio("页面导航", list(page_labels.keys()), label_visibility="collapsed", key="page_navigation")
    selected_page = page_labels[selected_label]
    st.markdown("---")
    st.markdown('<div class="sidebar-section">项目状态 / STATUS</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="panel" style="padding:12px 13px; box-shadow:none;">'
        '<div style="font-size:12px;font-weight:750;color:#273142;">🟢 本地分析服务</div>'
        '<div style="font-size:11px;color:#87909F;line-height:1.7;margin-top:5px;">Python 工具已连接<br>无需大模型 API<br>含单品下钻诊断<br>模拟数据环境</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.caption("建议：先用总览查看异常，再进入对应模块深入排查。")

# -------------------------- 主页面 --------------------------
render_hero()

with st.container(border=True):
    st.markdown("**⌕ 经营问题快捷分析**")
    st.caption("用自然语言描述需求，系统将按关键词规则选择本地分析工具；当前版本不是大模型推理。")
    with st.form("question_form", clear_on_submit=False):
        question = st.text_input(
            "问题描述", label_visibility="collapsed",
            placeholder="例如：找出 GMV 下滑最多的手机 / 哪些商品售价高于竞品 / 哪些商品缺货？",
        )
        submit_col, examples_col = st.columns([0.22, 0.78])
        with submit_col:
            submitted = st.form_submit_button("分析问题  →", use_container_width=True)
        with examples_col:
            st.markdown("<div style='padding:8px 0;color:#8B93A1;font-size:12px;'>试试：品类排名 · 销售环比 · 竞品价差 · 库存风险 · 促销利润模拟 · 商品运营优先级</div>", unsafe_allow_html=True)

active_page = selected_page
active_category: str | None = None
if submitted and question.strip():
    active_page, active_category = route_question(question)
    sku_match = re.search(r"SKU\d{1,5}", question.upper())
    if active_page == "sku_diagnosis" and sku_match:
        st.session_state["diagnosis_sku"] = sku_match.group(0)
    labels = {"overview": "整体经营概览", "periods": "周期经营对比", "category": "品类经营分析", "declines": "商品下滑诊断", "price": "竞品价格分析", "inventory": "库存风险预警", "sku_diagnosis": "单品诊断", "promotion": "促销利润模拟", "priorities": "商品运营优先级"}
    st.markdown(
        f'<div class="info-strip"><b>已识别分析方向：</b>{html.escape(labels.get(active_page, active_page))}　·　<b>你的问题：</b>{html.escape(question.strip())}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
# 搜索提交时展示匹配的分析模块；未提交搜索时由侧边栏导航控制页面。
try:
    render_task(active_page, active_category)
except FileNotFoundError as exc:
    st.error(str(exc))
except Exception as exc:
    st.error(f"页面加载失败：{exc}")
    with st.expander("查看技术错误详情"):
        st.exception(exc)

with st.expander("数据口径与使用说明"):
    st.markdown("""
    - **数据来源：** 本地 CSV 模拟数据，不是真实京东或其他商家经营数据。
    - **GMV：** 按销售明细中的 GMV 字段汇总。
    - **毛利率：** 毛利额 ÷ GMV；不应与扣除所有平台和履约费用后的净利率混淆。
    - **转化率：** 订单数 ÷ 访客数。
    - **规则路由：** 自然语言问题通过关键词映射到分析模块，不具备大模型的开放式推理能力。
    - **促销模拟：** 预期销量提升由用户手动输入；模拟未包含全部平台与履约费用，不是预测。
    - **运营优先级：** 由 GMV 变化、绝对损失、价差与库存状态加权组成的启发式评分，仅用于排序。
    - **调价和补货：** 页面只提供分析与预警，不会执行真实价格修改或采购。
    """)

st.markdown('<div class="footer">3C Commerce Insight · Personal Portfolio Project · Local Demo · All data are simulated</div>', unsafe_allow_html=True)
