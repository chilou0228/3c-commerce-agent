"""3C 数码电商经营分析项目的本地质量检查脚本。

运行方式：在项目根目录执行 python evaluate_project.py
不调用大模型 API，不会修改原始 CSV 数据。
报告将保存到 reports/quality_evaluation.csv 和 .txt。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"

# 使用项目已有的工具，确认接口结果和独立计算是否一致。
try:
    from agent_tools import (
        get_business_overview,
        compare_sales_periods,
        get_category_performance,
        get_declining_skus,
        get_competitor_price_gaps,
        get_inventory_risks,
        run_tool,
    )
except Exception as exc:  # 使入门用户能看到清晰的修复提示
    print("无法导入 agent_tools.py。请确认此脚本与 agent_tools.py 位于同一项目根目录。")
    print(f"具体错误：{exc}")
    sys.exit(2)

results: list[dict[str, Any]] = []


def record(name: str, passed: bool, detail: str) -> None:
    results.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})
    symbol = "✓" if passed else "✗"
    print(f"[{symbol}] {name}：{detail}")


def approx_equal(a: Any, b: Any, tol: float = 0.02) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-8, abs_tol=tol)
    except (TypeError, ValueError):
        return False


def load_tables():
    required = ["products.csv", "sales_daily.csv", "competitor_prices.csv", "inventory.csv"]
    missing = [name for name in required if not (DATA_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"data 文件夹缺少：{', '.join(missing)}。请确认你在项目根目录运行，且 data 文件夹没有被移动。"
        )
    products = pd.read_csv(DATA_DIR / "products.csv", encoding="utf-8-sig")
    sales = pd.read_csv(DATA_DIR / "sales_daily.csv", encoding="utf-8-sig")
    competitors = pd.read_csv(DATA_DIR / "competitor_prices.csv", encoding="utf-8-sig")
    inventory = pd.read_csv(DATA_DIR / "inventory.csv", encoding="utf-8-sig")
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    return products, sales, competitors, inventory


def main() -> int:
    print("=" * 68)
    print("3C 数码电商经营分析项目｜本地质量检查")
    print("数据为模拟数据；本脚本不调用大模型 API，也不会修改原始数据。")
    print("=" * 68)

    try:
        products, sales, competitors, inventory = load_tables()
    except Exception as exc:
        print(f"\n无法开始检查：{exc}")
        return 2

    # 1. 数据结构与质量
    record("商品数量与唯一 SKU", len(products) == 100 and products["sku"].nunique() == 100,
           f"行数={len(products)}，唯一 SKU={products['sku'].nunique()}（目标均为 100）")
    record("销售记录与日期覆盖", len(sales) == 9000 and sales["date"].nunique() == 90,
           f"销售行数={len(sales)}，日期数={sales['date'].nunique()}（目标为 9000 行、90 天）")
    per_day_counts = sales.groupby(sales["date"].dt.date).size()
    record("每天每个 SKU 一条销售记录", len(per_day_counts) == 90 and bool((per_day_counts == 100).all()),
           f"每日记录数范围={per_day_counts.min() if len(per_day_counts) else 0}–{per_day_counts.max() if len(per_day_counts) else 0}")
    record("竞品与库存快照数量", len(competitors) == 100 and len(inventory) == 100,
           f"竞品={len(competitors)} 行，库存={len(inventory)} 行（目标均为 100）")

    required_cols = {
        "products": (products, ["sku", "category", "current_price", "unit_cost"]),
        "sales": (sales, ["date", "sku", "visitors", "add_to_cart", "orders", "units_sold", "sale_price", "gmv", "gross_profit"]),
        "competitors": (competitors, ["sku", "competitor_price"]),
        "inventory": (inventory, ["sku", "current_stock", "stock_cover_days", "supplier_lead_days", "inventory_status"]),
    }
    missing_fields = []
    for table_name, (frame, cols) in required_cols.items():
        missing_fields.extend([f"{table_name}.{col}" for col in cols if col not in frame.columns])
    record("关键字段齐全", not missing_fields, "缺失字段：" + (", ".join(missing_fields) if missing_fields else "无"))

    key_missing = int(products[["sku", "current_price", "unit_cost"]].isna().sum().sum())
    key_missing += int(sales[["date", "sku", "visitors", "orders", "units_sold", "sale_price", "gmv", "gross_profit"]].isna().sum().sum())
    key_missing += int(competitors[["sku", "competitor_price"]].isna().sum().sum())
    key_missing += int(inventory[["sku", "current_stock", "stock_cover_days", "supplier_lead_days", "inventory_status"]].isna().sum().sum())
    record("关键字段无缺失值", key_missing == 0, f"缺失值合计={key_missing}")

    # 2. 基础业务算术校验
    expected_gmv = (sales["units_sold"] * sales["sale_price"]).round(2)
    gmv_errors = int(((sales["gmv"] - expected_gmv).abs() > 0.02).sum())
    record("GMV 计算一致", gmv_errors == 0, f"与销量 × 成交价不一致的行数={gmv_errors}")

    cost_lookup = products.set_index("sku")["unit_cost"]
    sales_with_cost = sales.copy()
    sales_with_cost["unit_cost"] = sales_with_cost["sku"].map(cost_lookup)
    expected_profit = (sales_with_cost["units_sold"] * (sales_with_cost["sale_price"] - sales_with_cost["unit_cost"])).round(2)
    profit_errors = int(((sales_with_cost["gross_profit"] - expected_profit).abs() > 0.02).sum())
    record("毛利额计算一致", profit_errors == 0, f"与销量 ×（成交价 - 单位成本）不一致的行数={profit_errors}")

    # 3. 检查工具结果与原始表的独立汇总是否一致
    overview = get_business_overview(days=90)
    raw_gmv = round(float(sales["gmv"].sum()), 2)
    raw_gp = round(float(sales["gross_profit"].sum()), 2)
    raw_visitors = int(sales["visitors"].sum())
    raw_orders = int(sales["orders"].sum())
    overview_ok = (
        approx_equal(overview.get("gmv"), raw_gmv)
        and approx_equal(overview.get("gross_profit"), raw_gp)
        and int(overview.get("visitors", -1)) == raw_visitors
        and int(overview.get("orders", -1)) == raw_orders
        and approx_equal(overview.get("conversion_rate"), raw_orders / raw_visitors, tol=1e-8)
    )
    record("经营概览工具与原表一致", overview_ok,
           f"GMV=¥{raw_gmv:,.2f}，毛利额=¥{raw_gp:,.2f}，转化率={raw_orders/raw_visitors:.2%}")

    comparison = compare_sales_periods(days=7)
    recent_start = pd.to_datetime(comparison["recent_period"]["start_date"])
    recent_end = pd.to_datetime(comparison["recent_period"]["end_date"])
    prev_start = pd.to_datetime(comparison["previous_period"]["start_date"])
    prev_end = pd.to_datetime(comparison["previous_period"]["end_date"])
    raw_recent = sales[(sales["date"] >= recent_start) & (sales["date"] <= recent_end)]
    raw_prev = sales[(sales["date"] >= prev_start) & (sales["date"] <= prev_end)]
    expected_gmv_change = round(float(raw_recent["gmv"].sum() - raw_prev["gmv"].sum()), 2)
    change_obj = comparison.get("change", {})
    period_ok = approx_equal(change_obj.get("gmv_change"), expected_gmv_change)
    record("7 天环比工具计算一致", period_ok,
           f"工具 GMV 变化={change_obj.get('gmv_change')}，独立复算={expected_gmv_change}")

    # 客单价是金额，应使用“金额变化”和“相对变化百分比”，不应称为百分点。
    aov_fields_ok = "average_order_value_change" in change_obj and "average_order_value_change_pct" in change_obj
    if aov_fields_ok:
        expected_aov_change = round(
            float(comparison["recent_period"]["average_order_value"])
            - float(comparison["previous_period"]["average_order_value"]), 2
        )
        aov_fields_ok = approx_equal(change_obj.get("average_order_value_change"), expected_aov_change)
    record("客单价变化口径正确", aov_fields_ok,
           "金额变化应使用 average_order_value_change，相对变化应使用 average_order_value_change_pct；不应标记为百分点" if aov_fields_ok else "未发现正确的客单价金额变化字段，请使用更新后的 agent_tools.py")

    categories = get_category_performance(days=7)
    category_sorted = len(categories) > 0 and all(
        float(categories[i]["gmv"]) >= float(categories[i + 1]["gmv"]) for i in range(len(categories) - 1)
    )
    cat_gmv_sum = round(sum(float(item["gmv"]) for item in categories), 2)
    raw_cat_gmv = round(float(raw_recent.merge(products[["sku", "category"]], on="sku", how="left")["gmv"].sum()), 2)
    record("品类表现排序及汇总", category_sorted and approx_equal(cat_gmv_sum, raw_cat_gmv),
           f"品类数={len(categories)}，品类 GMV 汇总=¥{cat_gmv_sum:,.2f}，7 天总 GMV=¥{raw_cat_gmv:,.2f}")

    declines = get_declining_skus(days=7, top_n=10)
    declining_ok = all(float(item["gmv_change"]) < 0 for item in declines) and all(
        float(declines[i]["gmv_change"]) <= float(declines[i + 1]["gmv_change"])
        for i in range(len(declines) - 1)
    )
    record("下滑 SKU 仅包含负增长且按损失排序", declining_ok,
           f"返回 {len(declines)} 条；所有 GMV 变化均为负且按损失从大到小排序={declining_ok}")

    price_gaps = get_competitor_price_gaps(top_n=10, min_gap_pct=0)
    price_ok = all(float(item["price_gap_pct"]) >= 0 for item in price_gaps) and all(
        float(price_gaps[i]["price_gap_pct"]) >= float(price_gaps[i + 1]["price_gap_pct"])
        for i in range(len(price_gaps) - 1)
    )
    if price_ok:
        price_ok = all(approx_equal(item["price_gap_pct"], round((item["current_price"] - item["competitor_price"]) / item["competitor_price"] * 100, 2), tol=0.02) for item in price_gaps)
    record("竞品价差公式与排序", price_ok, f"检查 {len(price_gaps)} 条价差记录，公式与降序排序一致={price_ok}")

    inventory_risks = get_inventory_risks(top_n=100)
    inventory_ok = all(item["inventory_status"] in {"缺货风险", "滞销风险"} for item in inventory_risks) and all(
        float(inventory_risks[i]["stock_cover_days"]) <= float(inventory_risks[i + 1]["stock_cover_days"])
        for i in range(len(inventory_risks) - 1)
    )
    record("库存风险过滤与排序", inventory_ok,
           f"返回 {len(inventory_risks)} 条风险 SKU；仅含缺货/滞销且覆盖天数升序={inventory_ok}")

    # 4. 促销模拟算术一致性：固定 SKU0021、销量提升 20%，比较 5% 与 25% 折扣。
    target_sku = "SKU0021"
    latest = sales["date"].max().normalize()
    start = latest - pd.Timedelta(days=6)
    item_recent = sales[(sales["sku"] == target_sku) & (sales["date"] >= start) & (sales["date"] <= latest)]
    product_rows = products[products["sku"] == target_sku]
    if not item_recent.empty and not product_rows.empty and int(item_recent["units_sold"].sum()) > 0:
        baseline_units = int(item_recent["units_sold"].sum())
        baseline_gmv = float(item_recent["gmv"].sum())
        baseline_gp = float(item_recent["gross_profit"].sum())
        avg_price = baseline_gmv / baseline_units
        unit_cost = float(product_rows.iloc[0]["unit_cost"])
        projected_units = max(0, int(round(baseline_units * 1.20)))

        def scenario(discount: float) -> dict[str, float | bool]:
            price = avg_price * (1 - discount / 100)
            unit_profit = price - unit_cost
            gmv = projected_units * price
            gp = projected_units * unit_profit
            margin = gp / gmv if gmv > 0 else 0.0
            promo_spend = max(0.0, avg_price - price) * projected_units
            return {"gmv": gmv, "gp": gp, "margin": margin, "spend": promo_spend,
                    "budget_feasible": promo_spend <= 5000.0, "unit_profit": unit_profit}

        low = scenario(5)
        high = scenario(25)
        promo_math_ok = float(high["spend"]) > float(low["spend"]) and float(high["gp"]) < float(low["gp"]) and float(high["margin"]) < float(low["margin"])
        # 用两档投入之间的预算作边界，检查预算布尔值是否会随投入跨越阈值而变化。
        midpoint_budget = (float(low["spend"]) + float(high["spend"])) / 2
        low_budget_ok = float(low["spend"]) <= midpoint_budget
        high_budget_ok = float(high["spend"]) <= midpoint_budget
        promo_math_ok = promo_math_ok and low_budget_ok and not high_budget_ok
        record("促销模拟敏感性与预算约束", promo_math_ok,
               f"SKU0021：5% 折扣毛利额=¥{float(low['gp']):,.2f}、投入=¥{float(low['spend']):,.2f}；25% 折扣毛利额=¥{float(high['gp']):,.2f}、投入=¥{float(high['spend']):,.2f}；25% 折扣毛利率应更低")
    else:
        record("促销模拟敏感性与预算约束", False, f"无法找到 {target_sku} 的近 7 天基线数据")

    # 5. 工具白名单检查
    unknown_tool_rejected = False
    try:
        run_tool("delete_all_data")
    except ValueError:
        unknown_tool_rejected = True
    record("未知工具名称被拒绝", unknown_tool_rejected, "run_tool 不允许调用白名单以外的工具" if unknown_tool_rejected else "未知工具意外被接受")

    passed = sum(row["status"] == "PASS" for row in results)
    failed = sum(row["status"] == "FAIL" for row in results)
    REPORT_DIR.mkdir(exist_ok=True)
    out_csv = REPORT_DIR / "quality_evaluation.csv"
    out_txt = REPORT_DIR / "quality_evaluation.txt"
    pd.DataFrame(results).to_csv(out_csv, index=False, encoding="utf-8-sig")
    lines = [
        "3C 数码电商经营分析项目｜本地质量检查报告",
        "数据说明：全部为练习用模拟数据，不代表真实平台或商家。",
        f"检查总数：{len(results)}，通过：{passed}，失败：{failed}",
        "",
    ]
    lines.extend([f"[{row['status']}] {row['check']}：{row['detail']}" for row in results])
    lines.extend(["", "注意：该报告验证本地 CSV、工具计算和促销算术逻辑；不会验证浏览器视觉表现或大模型推理，因为本版本未调用大模型 API。"])
    out_txt.write_text("\n".join(lines), encoding="utf-8-sig")

    print("\n" + "=" * 68)
    print(f"检查完成：{passed}/{len(results)} 项通过，{failed} 项失败。")
    print(f"CSV 报告：{out_csv.relative_to(BASE_DIR)}")
    print(f"文本报告：{out_txt.relative_to(BASE_DIR)}")
    if failed:
        print("存在失败项，请根据上面的提示修复后再运行一次。")
        return 1
    print("全部检查通过。下一步可把报告摘要和代表性截图整理进 README / 作品集。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
