"""3C 数码电商经营分析：第一个数据分析程序
读取 data/ 下的四张模拟 CSV 表，输出基础经营指标和诊断结果。
注意：所有数据均为模拟数据，不代表任何真实平台或商家的经营情况。
"""
from pathlib import Path
import sys
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"


def load_csv(filename: str) -> pd.DataFrame:
    """读取 CSV；找不到文件时给出容易理解的报错。"""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"找不到文件：{path}\n请确认 data 文件夹与 analyze_data.py 位于同一项目目录，"
            "并且已经运行过 generate_data.py。"
        )
    return pd.read_csv(path, encoding="utf-8-sig")


def require_columns(df: pd.DataFrame, columns: list[str], filename: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{filename} 缺少必要字段：{missing}。请检查 CSV 表头是否完整。")


def money(value: float) -> str:
    return f"¥{value:,.2f}"


def pct_change(current: float, previous: float) -> float:
    """计算变化率；上一周期为 0 时返回空值，避免除以 0。"""
    if previous == 0:
        return float("nan")
    return (current - previous) / previous * 100


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)

    products = load_csv("products.csv")
    sales = load_csv("sales_daily.csv")
    competitors = load_csv("competitor_prices.csv")
    inventory = load_csv("inventory.csv")

    require_columns(products, ["sku", "product_name", "category", "brand", "current_price", "unit_cost"], "products.csv")
    require_columns(sales, ["date", "sku", "visitors", "orders", "units_sold", "gmv", "gross_profit"], "sales_daily.csv")
    require_columns(competitors, ["sku", "competitor_name", "competitor_price"], "competitor_prices.csv")
    require_columns(inventory, ["sku", "current_stock", "stock_cover_days", "supplier_lead_days", "inventory_status"], "inventory.csv")

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    if sales["date"].isna().any():
        raise ValueError("sales_daily.csv 中存在无法识别的日期，请检查 date 字段。")

    # 检查基础数据质量。
    print("=" * 62)
    print("3C 数码电商经营分析：数据检查")
    print("=" * 62)
    print(f"商品数：{products['sku'].nunique()} 个 SKU")
    print(f"销售记录：{len(sales):,} 条")
    print(f"竞品价格记录：{len(competitors):,} 条")
    print(f"库存记录：{len(inventory):,} 条")
    print(f"销售日期：{sales['date'].min():%Y-%m-%d} 至 {sales['date'].max():%Y-%m-%d}")
    print(f"销售表缺失值总数：{int(sales.isna().sum().sum())}")

    # 汇总整个数据周期的核心指标。
    total_gmv = float(sales["gmv"].sum())
    total_profit = float(sales["gross_profit"].sum())
    total_visitors = int(sales["visitors"].sum())
    total_orders = int(sales["orders"].sum())
    total_units = int(sales["units_sold"].sum())
    overall_conversion = total_orders / total_visitors if total_visitors else 0.0
    overall_margin = total_profit / total_gmv if total_gmv else 0.0
    overall_aov = total_gmv / total_orders if total_orders else 0.0

    print("\n" + "=" * 62)
    print("一、整个数据周期的经营概览")
    print("=" * 62)
    print(f"GMV（成交总额）：{money(total_gmv)}")
    print(f"毛利额：{money(total_profit)}")
    print(f"整体毛利率：{overall_margin:.2%}")
    print(f"总访客数：{total_visitors:,}")
    print(f"总订单数：{total_orders:,}")
    print(f"总销量：{total_units:,}")
    print(f"整体转化率（订单数 ÷ 访客数）：{overall_conversion:.2%}")
    print(f"平均订单金额（GMV ÷ 订单数）：{money(overall_aov)}")

    # 对比最近 7 天与之前 7 天，所有日期以数据里的最后一天为准。
    latest_date = sales["date"].max().normalize()
    recent_start = latest_date - pd.Timedelta(days=6)
    previous_start = latest_date - pd.Timedelta(days=13)
    previous_end = latest_date - pd.Timedelta(days=7)
    recent = sales[(sales["date"] >= recent_start) & (sales["date"] <= latest_date)]
    previous = sales[(sales["date"] >= previous_start) & (sales["date"] <= previous_end)]

    def period_metrics(frame: pd.DataFrame) -> dict[str, float]:
        gmv = float(frame["gmv"].sum())
        profit = float(frame["gross_profit"].sum())
        visitors = int(frame["visitors"].sum())
        orders = int(frame["orders"].sum())
        return {
            "gmv": gmv,
            "gross_profit": profit,
            "visitors": visitors,
            "orders": orders,
            "units_sold": int(frame["units_sold"].sum()),
            "conversion_rate": orders / visitors if visitors else 0.0,
            "gross_margin_rate": profit / gmv if gmv else 0.0,
        }

    recent_m = period_metrics(recent)
    previous_m = period_metrics(previous)

    print("\n" + "=" * 62)
    print("二、最近 7 天 vs 前一个 7 天")
    print("=" * 62)
    print(f"最近 7 天：{recent_start:%Y-%m-%d} 至 {latest_date:%Y-%m-%d}")
    print(f"前一个 7 天：{previous_start:%Y-%m-%d} 至 {previous_end:%Y-%m-%d}")
    for key, label in [("gmv", "GMV"), ("gross_profit", "毛利额"), ("units_sold", "销量")]:
        change = pct_change(recent_m[key], previous_m[key])
        change_text = "无法计算（前期为 0）" if pd.isna(change) else f"{change:+.2f}%"
        value = money(recent_m[key]) if key in ("gmv", "gross_profit") else f"{recent_m[key]:,} 件"
        print(f"{label}：最近 7 天 {value}；环比变化 {change_text}")
    print(f"转化率：最近 7 天 {recent_m['conversion_rate']:.2%}；前 7 天 {previous_m['conversion_rate']:.2%}")
    print(f"毛利率：最近 7 天 {recent_m['gross_margin_rate']:.2%}；前 7 天 {previous_m['gross_margin_rate']:.2%}")

    # 按品类汇总最近 7 天表现，并保存报告。
    product_fields = products[["sku", "product_name", "category", "brand", "current_price", "unit_cost"]]
    recent_by_sku = recent.groupby("sku", as_index=False).agg(
        recent_gmv=("gmv", "sum"), recent_profit=("gross_profit", "sum"), recent_units=("units_sold", "sum")
    )
    previous_by_sku = previous.groupby("sku", as_index=False).agg(
        previous_gmv=("gmv", "sum"), previous_profit=("gross_profit", "sum"), previous_units=("units_sold", "sum")
    )
    sku_comparison = product_fields.merge(recent_by_sku, on="sku", how="left").merge(previous_by_sku, on="sku", how="left")
    for col in ["recent_gmv", "recent_profit", "recent_units", "previous_gmv", "previous_profit", "previous_units"]:
        sku_comparison[col] = sku_comparison[col].fillna(0)
    sku_comparison["gmv_change"] = sku_comparison["recent_gmv"] - sku_comparison["previous_gmv"]
    sku_comparison["gmv_change_pct"] = sku_comparison.apply(
        lambda row: pct_change(row["recent_gmv"], row["previous_gmv"]), axis=1
    )

    category_report = sku_comparison.groupby("category", as_index=False).agg(
        recent_gmv=("recent_gmv", "sum"), recent_profit=("recent_profit", "sum"), recent_units=("recent_units", "sum")
    ).sort_values("recent_gmv", ascending=False)
    category_report.to_csv(REPORT_DIR / "category_last7d.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 62)
    print("三、最近 7 天各品类 GMV 排名")
    print("=" * 62)
    for _, row in category_report.iterrows():
        print(f"{row['category']}: GMV {money(row['recent_gmv'])}；销量 {int(row['recent_units']):,} 件；毛利 {money(row['recent_profit'])}")

    # 找出 GMV 环比下降最大的 SKU。
    declining = sku_comparison[sku_comparison["gmv_change"] < 0].sort_values("gmv_change").head(10)
    declining.to_csv(REPORT_DIR / "sku_gmv_declines.csv", index=False, encoding="utf-8-sig")
    print("\n" + "=" * 62)
    print("四、GMV 下降幅度最大的 10 个 SKU（与前一个 7 天比较）")
    print("=" * 62)
    if declining.empty:
        print("没有发现 GMV 下降的 SKU。")
    else:
        for _, row in declining.head(10).iterrows():
            change_pct = "前期 GMV 为 0，无法计算百分比" if pd.isna(row["gmv_change_pct"]) else f"{row['gmv_change_pct']:+.1f}%"
            print(f"{row['sku']} | {row['product_name']} | {row['category']} | GMV 变化 {money(row['gmv_change'])} ({change_pct})")

    # 竞品价格差：正值代表本商品当前标价高于竞品价格。
    price_report = product_fields.merge(competitors[["sku", "competitor_name", "competitor_price"]], on="sku", how="left")
    price_report["price_gap_pct"] = (price_report["current_price"] - price_report["competitor_price"]) / price_report["competitor_price"] * 100
    price_report = price_report.sort_values("price_gap_pct", ascending=False)
    price_report.to_csv(REPORT_DIR / "competitor_price_gap.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 62)
    print("五、当前标价高于竞品最多的 5 个 SKU")
    print("说明：这里只识别价格差，不代表直接降价一定能增加利润或销量。")
    print("=" * 62)
    for _, row in price_report.head(5).iterrows():
        print(f"{row['sku']} | {row['product_name']} | 本商品 {money(row['current_price'])} | 竞品 {money(row['competitor_price'])} | 高出 {row['price_gap_pct']:.1f}%")

    # 输出需要关注的库存风险清单。
    risk = inventory[inventory["inventory_status"].isin(["缺货风险", "滞销风险"])].merge(
        products[["sku", "product_name", "category"]], on="sku", how="left"
    )
    risk = risk.sort_values("stock_cover_days")
    risk.to_csv(REPORT_DIR / "inventory_risks.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 62)
    print("六、库存风险概览")
    print("=" * 62)
    print(inventory["inventory_status"].value_counts().to_string())
    if not risk.empty:
        print(f"已将 {len(risk)} 个风险 SKU 保存到 reports/inventory_risks.csv")

    print("\n分析完成！报告文件已保存到 reports 文件夹：")
    for filename in ["category_last7d.csv", "sku_gmv_declines.csv", "competitor_price_gap.csv", "inventory_risks.csv"]:
        print(f"  reports/{filename}")
    print("\n提醒：这是基于模拟数据的描述性分析。发现指标变化并不等于已经证明变化原因。")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"\n运行失败：{exc}")
        sys.exit(1)
