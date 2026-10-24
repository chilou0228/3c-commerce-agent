"""3C 电商经营分析 Agent 的数据工具层（第一版）。

说明：本文件只负责读取 CSV 和计算可复核的业务数据，不调用大模型。
后续 Agent 会把这些函数注册为工具，由模型根据用户问题选择调用。
所有数据均为模拟数据时，分析结果也仅用于练习。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import math
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读取四张基础表，并检查后续计算所需的字段。"""
    required_files = [
        "products.csv", "sales_daily.csv", "competitor_prices.csv", "inventory.csv"
    ]
    missing_files = [name for name in required_files if not (DATA_DIR / name).exists()]
    if missing_files:
        raise FileNotFoundError(
            f"data 文件夹中缺少文件：{', '.join(missing_files)}。"
            "请先运行 python generate_data.py，并确认 data 文件夹与本文件位于同一项目目录。"
        )

    products = pd.read_csv(DATA_DIR / "products.csv", encoding="utf-8-sig")
    sales = pd.read_csv(DATA_DIR / "sales_daily.csv", encoding="utf-8-sig")
    competitors = pd.read_csv(DATA_DIR / "competitor_prices.csv", encoding="utf-8-sig")
    inventory = pd.read_csv(DATA_DIR / "inventory.csv", encoding="utf-8-sig")

    requirements = {
        "products.csv": (products, ["sku", "product_name", "category", "brand", "current_price", "unit_cost"]),
        "sales_daily.csv": (sales, ["date", "sku", "visitors", "orders", "units_sold", "gmv", "gross_profit"]),
        "competitor_prices.csv": (competitors, ["sku", "competitor_name", "competitor_price"]),
        "inventory.csv": (inventory, ["sku", "current_stock", "stock_cover_days", "supplier_lead_days", "inventory_status"]),
    }
    for filename, (frame, columns) in requirements.items():
        absent = [column for column in columns if column not in frame.columns]
        if absent:
            raise ValueError(f"{filename} 缺少必要字段：{absent}")

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    if sales["date"].isna().any():
        raise ValueError("sales_daily.csv 中存在无法识别的日期，请检查 date 字段。")
    for col in ["visitors", "orders", "units_sold", "gmv", "gross_profit"]:
        sales[col] = pd.to_numeric(sales[col], errors="coerce")
    if sales[["visitors", "orders", "units_sold", "gmv", "gross_profit"]].isna().any().any():
        raise ValueError("sales_daily.csv 的关键数值字段存在空值或非数字，请先检查数据。")
    return products, sales, competitors, inventory


def _safe_divide(numerator: float, denominator: float) -> float | None:
    return float(numerator / denominator) if denominator else None


def _periods(sales: pd.DataFrame, days: int = 7) -> tuple[pd.DataFrame, pd.DataFrame, str, str, str, str]:
    if not isinstance(days, int) or days < 1 or days > 90:
        raise ValueError("days 必须是 1 到 90 之间的整数。")
    last_date = sales["date"].max().normalize()
    recent_start = last_date - pd.Timedelta(days=days - 1)
    previous_end = recent_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=days - 1)
    recent = sales[(sales["date"] >= recent_start) & (sales["date"] <= last_date)]
    previous = sales[(sales["date"] >= previous_start) & (sales["date"] <= previous_end)]
    return (
        recent, previous,
        recent_start.strftime("%Y-%m-%d"), last_date.strftime("%Y-%m-%d"),
        previous_start.strftime("%Y-%m-%d"), previous_end.strftime("%Y-%m-%d"),
    )


def _period_metric(frame: pd.DataFrame) -> dict[str, Any]:
    gmv = float(frame["gmv"].sum())
    profit = float(frame["gross_profit"].sum())
    visitors = int(frame["visitors"].sum())
    orders = int(frame["orders"].sum())
    units = int(frame["units_sold"].sum())
    return {
        "gmv": round(gmv, 2),
        "gross_profit": round(profit, 2),
        "gross_margin_rate": _safe_divide(profit, gmv),
        "visitors": visitors,
        "orders": orders,
        "units_sold": units,
        "conversion_rate": _safe_divide(orders, visitors),
        "average_order_value": _safe_divide(gmv, orders),
    }


def get_business_overview(days: int = 90) -> dict[str, Any]:
    """返回最近 days 天的整体经营概览；days=90 可查看全周期。"""
    _, sales, _, _ = _load_data()
    latest = sales["date"].max().normalize()
    start = latest - pd.Timedelta(days=days - 1)
    frame = sales[(sales["date"] >= start) & (sales["date"] <= latest)]
    result = _period_metric(frame)
    result.update({"start_date": start.strftime("%Y-%m-%d"), "end_date": latest.strftime("%Y-%m-%d"), "days": days})
    return result


def compare_sales_periods(days: int = 7) -> dict[str, Any]:
    """比较最近 days 天和紧邻的前一个同长度周期。"""
    _, sales, _, _ = _load_data()
    recent, previous, recent_start, recent_end, previous_start, previous_end = _periods(sales, days)
    current_metrics = _period_metric(recent)
    previous_metrics = _period_metric(previous)
    change = {}
    for metric in ["gmv", "gross_profit", "units_sold", "visitors", "orders"]:
        old = previous_metrics[metric]
        new = current_metrics[metric]
        change[f"{metric}_change"] = round(new - old, 2)
        change[f"{metric}_change_pct"] = None if not old else round((new - old) / old * 100, 2)
    # 转化率和毛利率是比率，差值应以“百分点”表达。
    for metric in ["conversion_rate", "gross_margin_rate"]:
        old = previous_metrics[metric]
        new = current_metrics[metric]
        change[f"{metric}_change_percentage_points"] = (
            None if old is None or new is None else round((new - old) * 100, 4)
        )

    # 客单价是金额，不能按百分点表示。分别返回金额差和相对变化百分比。
    old_aov = previous_metrics["average_order_value"]
    new_aov = current_metrics["average_order_value"]
    change["average_order_value_change"] = (
        None if old_aov is None or new_aov is None else round(new_aov - old_aov, 2)
    )
    change["average_order_value_change_pct"] = (
        None if old_aov in (None, 0) or new_aov is None
        else round((new_aov - old_aov) / old_aov * 100, 2)
    )
    return {
        "recent_period": {"start_date": recent_start, "end_date": recent_end, **current_metrics},
        "previous_period": {"start_date": previous_start, "end_date": previous_end, **previous_metrics},
        "change": change,
        "note": "环比描述两个周期的变化，不单独证明变化原因。",
    }


def get_category_performance(days: int = 7) -> list[dict[str, Any]]:
    """返回最近 days 天各品类 GMV、销量、毛利和毛利率，按 GMV 降序排列。"""
    products, sales, _, _ = _load_data()
    recent, _, start, end, _, _ = _periods(sales, days)
    merged = recent.merge(products[["sku", "category"]], on="sku", how="left")
    grouped = merged.groupby("category", as_index=False).agg(
        gmv=("gmv", "sum"), gross_profit=("gross_profit", "sum"), units_sold=("units_sold", "sum")
    )
    grouped["gross_margin_rate"] = grouped.apply(
        lambda row: _safe_divide(float(row["gross_profit"]), float(row["gmv"])), axis=1
    )
    grouped = grouped.sort_values("gmv", ascending=False)
    results = []
    for _, row in grouped.iterrows():
        results.append({
            "category": str(row["category"]), "gmv": round(float(row["gmv"]), 2),
            "gross_profit": round(float(row["gross_profit"]), 2),
            "units_sold": int(row["units_sold"]),
            "gross_margin_rate": None if pd.isna(row["gross_margin_rate"]) else float(row["gross_margin_rate"]),
            "start_date": start, "end_date": end,
        })
    return results


def get_declining_skus(days: int = 7, top_n: int = 10, category: str | None = None) -> list[dict[str, Any]]:
    """找出最近周期 GMV 下降最多的 SKU，可按品类筛选。"""
    products, sales, _, _ = _load_data()
    if not isinstance(top_n, int) or not 1 <= top_n <= 100:
        raise ValueError("top_n 必须是 1 到 100 之间的整数。")
    recent, previous, recent_start, recent_end, previous_start, previous_end = _periods(sales, days)
    recent_agg = recent.groupby("sku", as_index=False).agg(recent_gmv=("gmv", "sum"), recent_units=("units_sold", "sum"))
    previous_agg = previous.groupby("sku", as_index=False).agg(previous_gmv=("gmv", "sum"), previous_units=("units_sold", "sum"))
    result = products[["sku", "product_name", "category", "brand", "current_price", "unit_cost"]].merge(
        recent_agg, on="sku", how="left"
    ).merge(previous_agg, on="sku", how="left")
    for col in ["recent_gmv", "recent_units", "previous_gmv", "previous_units"]:
        result[col] = result[col].fillna(0)
    result["gmv_change"] = result["recent_gmv"] - result["previous_gmv"]
    result["gmv_change_pct"] = result.apply(
        lambda row: None if not row["previous_gmv"] else (row["gmv_change"] / row["previous_gmv"] * 100), axis=1
    )
    result = result[result["gmv_change"] < 0]
    if category:
        result = result[result["category"].astype(str).str.contains(category, case=False, na=False)]
    result = result.sort_values("gmv_change", ascending=True).head(top_n)
    return [{
        "sku": str(row.sku), "product_name": str(row.product_name), "category": str(row.category),
        "brand": str(row.brand), "current_price": round(float(row.current_price), 2),
        "unit_cost": round(float(row.unit_cost), 2), "recent_gmv": round(float(row.recent_gmv), 2),
        "previous_gmv": round(float(row.previous_gmv), 2), "gmv_change": round(float(row.gmv_change), 2),
        "gmv_change_pct": None if pd.isna(row.gmv_change_pct) else round(float(row.gmv_change_pct), 2),
        "recent_units": int(row.recent_units), "previous_units": int(row.previous_units),
        "recent_period": f"{recent_start} 至 {recent_end}",
        "previous_period": f"{previous_start} 至 {previous_end}",
    } for row in result.itertuples(index=False)]


def get_competitor_price_gaps(top_n: int = 10, min_gap_pct: float = 0.0) -> list[dict[str, Any]]:
    """计算本商品标价相对竞品价格的差异；正数代表本商品更贵。"""
    products, _, competitors, _ = _load_data()
    if not isinstance(top_n, int) or not 1 <= top_n <= 100:
        raise ValueError("top_n 必须是 1 到 100 之间的整数。")
    merged = products[["sku", "product_name", "category", "brand", "current_price", "unit_cost"]].merge(
        competitors[["sku", "competitor_name", "competitor_price"]], on="sku", how="left"
    )
    merged["price_gap_pct"] = (merged["current_price"] - merged["competitor_price"]) / merged["competitor_price"] * 100
    merged["estimated_unit_gross_profit_at_current_price"] = merged["current_price"] - merged["unit_cost"]
    merged["estimated_unit_gross_profit_at_competitor_price"] = merged["competitor_price"] - merged["unit_cost"]
    merged = merged[merged["price_gap_pct"] >= float(min_gap_pct)].sort_values("price_gap_pct", ascending=False).head(top_n)
    return [{
        "sku": str(row.sku), "product_name": str(row.product_name), "category": str(row.category),
        "brand": str(row.brand), "current_price": round(float(row.current_price), 2),
        "competitor_name": str(row.competitor_name), "competitor_price": round(float(row.competitor_price), 2),
        "price_gap_pct": round(float(row.price_gap_pct), 2), "unit_cost": round(float(row.unit_cost), 2),
        "estimated_unit_gross_profit_at_current_price": round(float(row.estimated_unit_gross_profit_at_current_price), 2),
        "estimated_unit_gross_profit_at_competitor_price": round(float(row.estimated_unit_gross_profit_at_competitor_price), 2),
        "note": "这是价格差异和简单单位毛利测算，不含平台佣金、优惠成本、运费等其他费用；不应据此自动调价。",
    } for row in merged.itertuples(index=False)]


def get_inventory_risks(status: str | None = None, top_n: int = 20) -> list[dict[str, Any]]:
    """查看缺货/滞销风险；status 可填写“缺货风险”或“滞销风险”。"""
    products, _, _, inventory = _load_data()
    if not isinstance(top_n, int) or not 1 <= top_n <= 100:
        raise ValueError("top_n 必须是 1 到 100 之间的整数。")
    merged = inventory.merge(products[["sku", "product_name", "category", "brand"]], on="sku", how="left")
    if status:
        allowed = {"缺货风险", "滞销风险", "正常"}
        if status not in allowed:
            raise ValueError(f"status 只能是：{', '.join(sorted(allowed))}")
        merged = merged[merged["inventory_status"] == status]
    else:
        merged = merged[merged["inventory_status"].isin(["缺货风险", "滞销风险"])]
    merged = merged.sort_values("stock_cover_days", ascending=True).head(top_n)
    return [{
        "sku": str(row.sku), "product_name": str(row.product_name), "category": str(row.category),
        "brand": str(row.brand), "inventory_status": str(row.inventory_status),
        "current_stock": int(row.current_stock), "avg_daily_sales_7d": float(row.avg_daily_sales_7d),
        "stock_cover_days": float(row.stock_cover_days), "supplier_lead_days": int(row.supplier_lead_days),
        "safety_stock": int(row.safety_stock) if hasattr(row, "safety_stock") else None,
    } for row in merged.itertuples(index=False)]


TOOL_FUNCTIONS = {
    "get_business_overview": get_business_overview,
    "compare_sales_periods": compare_sales_periods,
    "get_category_performance": get_category_performance,
    "get_declining_skus": get_declining_skus,
    "get_competitor_price_gaps": get_competitor_price_gaps,
    "get_inventory_risks": get_inventory_risks,
}


def run_tool(tool_name: str, **kwargs: Any) -> Any:
    """按名称调用允许的分析工具。后续大模型只允许从这个白名单选择工具。"""
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"未知工具：{tool_name}。可用工具：{', '.join(TOOL_FUNCTIONS)}")
    return TOOL_FUNCTIONS[tool_name](**kwargs)
