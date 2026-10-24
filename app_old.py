"""3C 数码电商分析工作台（本地无收费 API 版）

运行：python -m streamlit run app.py
说明：本版本使用本地 Python 工具与关键词规则，不调用任何大模型 API。
所有输入数据均为练习用模拟数据。
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.express as px
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

st.set_page_config(page_title="3C 数码电商经营分析工作台", page_icon="📊", layout="wide")

CATEGORY_WORDS = ["手机", "笔记本电脑", "平板电脑", "耳机"]


def detect_category(question: str) -> str | None:
    for category in CATEGORY_WORDS:
        if category in question:
            return category
    return None


def route_question(question: str) -> tuple[str, str | None]:
    """用简单关键词规则选择本地分析工具；这不是大模型推理。"""
    q = question.strip().lower()
    category = detect_category(q)
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


def money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"¥{value:,.2f}"


def pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:.2f}%"


def show_overview() -> None:
    result = get_business_overview(90)
    st.subheader("整体经营概览")
    st.caption(f"数据日期：{result['start_date']} 至 {result['end_date']}（模拟数据）")
    cols = st.columns(4)
    cols[0].metric("90 天 GMV", money(result["gmv"]))
    cols[1].metric("毛利额", money(result["gross_profit"]))
    cols[2].metric("毛利率", pct(result["gross_margin_rate"]))
    cols[3].metric("转化率", pct(result["conversion_rate"]))
    cols = st.columns(3)
    cols[0].metric("访客数", f"{result['visitors']:,}")
    cols[1].metric("订单数", f"{result['orders']:,}")
    cols[2].metric("平均订单金额", money(result["average_order_value"]))

    sales_path = DATA_DIR / "sales_daily.csv"
    sales = pd.read_csv(sales_path, encoding="utf-8-sig", parse_dates=["date"])
    daily = sales.groupby("date", as_index=False).agg(gmv=("gmv", "sum"), gross_profit=("gross_profit", "sum"))
    chart = px.line(daily, x="date", y="gmv", title="每日 GMV 趋势", labels={"date": "日期", "gmv": "GMV（元）"})
    chart.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(chart, use_container_width=True)
    st.info("口径说明：GMV 为模拟成交额；毛利额按数据表中的字段汇总。当前页面不调用大模型 API。")


def show_periods() -> None:
    result = compare_sales_periods(7)
    recent, previous, change = result["recent_period"], result["previous_period"], result["change"]
    st.subheader("最近 7 天 vs 前 7 天")
    st.caption(f"最近周期：{recent['start_date']} 至 {recent['end_date']}；前一周期：{previous['start_date']} 至 {previous['end_date']}")
    cols = st.columns(3)
    cols[0].metric("GMV", money(recent["gmv"]), f"{change['gmv_change_pct']:+.2f}%")
    cols[1].metric("毛利额", money(recent["gross_profit"]), f"{change['gross_profit_change_pct']:+.2f}%")
    cols[2].metric("销量", f"{recent['units_sold']:,}", f"{change['units_sold_change_pct']:+.2f}%")
    rows = [
        {"指标": "GMV", "前 7 天": money(previous["gmv"]), "最近 7 天": money(recent["gmv"]), "变化": f"{change['gmv_change_pct']:+.2f}%"},
        {"指标": "毛利额", "前 7 天": money(previous["gross_profit"]), "最近 7 天": money(recent["gross_profit"]), "变化": f"{change['gross_profit_change_pct']:+.2f}%"},
        {"指标": "访客数", "前 7 天": f"{previous['visitors']:,}", "最近 7 天": f"{recent['visitors']:,}", "变化": f"{change['visitors_change_pct']:+.2f}%"},
        {"指标": "转化率", "前 7 天": pct(previous["conversion_rate"]), "最近 7 天": pct(recent["conversion_rate"]), "变化": f"{change['conversion_rate_change_percentage_points']:+.4f} 个百分点"},
        {"指标": "毛利率", "前 7 天": pct(previous["gross_margin_rate"]), "最近 7 天": pct(recent["gross_margin_rate"]), "变化": f"{change['gross_margin_rate_change_percentage_points']:+.4f} 个百分点"},
        {"指标": "客单价", "前 7 天": money(previous["average_order_value"]), "最近 7 天": money(recent["average_order_value"]), "变化": f"{change['average_order_value_change']:+.2f} 元（{change['average_order_value_change_pct']:+.2f}%）"},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.warning("周期对比只能说明指标如何变化，不能单独证明变化原因。")


def show_categories() -> None:
    records = get_category_performance(7)
    df = pd.DataFrame(records)
    if df.empty:
        st.warning("没有找到品类数据。")
        return
    st.subheader("最近 7 天各品类表现")
    df["毛利率"] = df["gross_margin_rate"].map(pct)
    df["GMV"] = df["gmv"].map(money)
    df["毛利额"] = df["gross_profit"].map(money)
    st.dataframe(df[["category", "GMV", "毛利额", "units_sold", "毛利率"]].rename(columns={"category": "品类", "units_sold": "销量"}), use_container_width=True, hide_index=True)
    chart = px.bar(pd.DataFrame(records), x="gmv", y="category", orientation="h", title="最近 7 天品类 GMV 排名", labels={"gmv": "GMV（元）", "category": "品类"})
    chart.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(chart, use_container_width=True)


def show_declines(category: str | None = None) -> None:
    records = get_declining_skus(days=7, top_n=10, category=category)
    st.subheader("GMV 下滑 SKU 排查清单")
    if category:
        st.caption(f"品类筛选：{category}；比较最近 7 天与之前 7 天。")
    if not records:
        st.success("当前筛选条件下没有 GMV 下降的 SKU。")
        return
    df = pd.DataFrame(records)
    df["最近 7 天 GMV"] = df["recent_gmv"].map(money)
    df["前 7 天 GMV"] = df["previous_gmv"].map(money)
    df["GMV 变化"] = df["gmv_change"].map(money)
    df["变化幅度"] = df["gmv_change_pct"].map(lambda x: "—" if x is None else f"{x:.2f}%")
    st.dataframe(df[["sku", "product_name", "category", "最近 7 天 GMV", "前 7 天 GMV", "GMV 变化", "变化幅度"]].rename(columns={"sku": "SKU", "product_name": "商品", "category": "品类"}), use_container_width=True, hide_index=True)
    st.warning("此处识别的是 GMV 下滑商品，不代表已证明下滑原因。需继续查看流量、转化率、价格和库存等证据。")


def show_prices() -> None:
    records = get_competitor_price_gaps(top_n=10, min_gap_pct=0)
    st.subheader("商品与竞品价格差异")
    if not records:
        st.success("没有高于竞品价格的商品。")
        return
    df = pd.DataFrame(records)
    df["本商品售价"] = df["current_price"].map(money)
    df["竞品售价"] = df["competitor_price"].map(money)
    df["高于竞品"] = df["price_gap_pct"].map(lambda x: f"{x:.2f}%")
    df["当前单位毛利（简化）"] = df["estimated_unit_gross_profit_at_current_price"].map(money)
    df["竞品价下单位毛利（简化）"] = df["estimated_unit_gross_profit_at_competitor_price"].map(money)
    st.dataframe(df[["sku", "product_name", "category", "competitor_name", "本商品售价", "竞品售价", "高于竞品", "当前单位毛利（简化）", "竞品价下单位毛利（简化）"]].rename(columns={"sku": "SKU", "product_name": "商品", "category": "品类", "competitor_name": "竞品平台"}), use_container_width=True, hide_index=True)
    st.warning("价格差异不等于直接降价建议。简化单位毛利未计入平台佣金、优惠成本、物流等费用。")


def show_inventory(status: str | None = None) -> None:
    records = get_inventory_risks(status=status, top_n=100)
    st.subheader("库存风险清单")
    if not records:
        st.success("当前条件没有匹配的 SKU。")
        return
    df = pd.DataFrame(records)
    df["库存覆盖天数"] = df["stock_cover_days"].map(lambda x: f"{x:.1f} 天")
    st.dataframe(df[["sku", "product_name", "category", "inventory_status", "current_stock", "avg_daily_sales_7d", "库存覆盖天数", "supplier_lead_days", "safety_stock"]].rename(columns={"sku": "SKU", "product_name": "商品", "category": "品类", "inventory_status": "状态", "current_stock": "当前库存", "avg_daily_sales_7d": "近 7 天日均销量", "supplier_lead_days": "供应商交期（天）", "safety_stock": "安全库存"}), use_container_width=True, hide_index=True)
    st.warning("库存建议是基于模拟库存和近 7 天日均销量的预警，不会自动下采购单。")


st.title("📊 3C 数码电商经营分析工作台")
st.caption("本地运行版 · 不需要收费 API · 数据均为模拟数据")
st.markdown("你可以用自然语言描述问题，系统会根据关键词选择本地分析工具。")

with st.form("question_form"):
    question = st.text_input(
        "输入你想分析的问题",
        placeholder="例如：分析最近7天各品类GMV排名 / 哪些商品缺货 / 找出GMV下滑的手机",
    )
    submitted = st.form_submit_button("分析问题", type="primary")

if "task" not in st.session_state:
    st.session_state.task = "overview"
    st.session_state.category_filter = None
    st.session_state.question = ""

if submitted:
    st.session_state.question = question.strip()
    st.session_state.task, st.session_state.category_filter = route_question(question)

if st.session_state.question:
    st.write(f"**你的问题：** {st.session_state.question}")
    st.caption(f"本地规则路由结果：{st.session_state.task}。注意：这里使用关键词规则，不是大模型推理。")

try:
    task = st.session_state.task
    if task == "periods":
        show_periods()
    elif task == "category":
        show_categories()
    elif task == "declines":
        show_declines(st.session_state.category_filter)
    elif task == "price":
        show_prices()
    elif task == "inventory":
        show_inventory()
    else:
        show_overview()
except FileNotFoundError as exc:
    st.error(str(exc))
except Exception as exc:
    st.error(f"分析过程中发生错误：{exc}")
    st.exception(exc)

with st.expander("可尝试的提问"):
    st.markdown("""
    - 请看一下整体经营概览
    - 对比最近 7 天和前 7 天的经营表现
    - 查询最近 7 天各品类的 GMV 排名
    - 找出 GMV 下降最多的手机 SKU
    - 哪些商品的售价高于竞品？
    - 哪些商品有缺货或滞销风险？
    """)
