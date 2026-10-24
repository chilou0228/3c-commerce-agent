"""验证 agent_tools.py 是否能读取数据并调用六个分析工具。"""
import json
from agent_tools import (
    get_business_overview,
    compare_sales_periods,
    get_category_performance,
    get_declining_skus,
    get_competitor_price_gaps,
    get_inventory_risks,
)


def show(title, data, limit=3):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    if isinstance(data, list):
        print(json.dumps(data[:limit], ensure_ascii=False, indent=2, default=str))
        print(f"（共 {len(data)} 条，以上展示前 {min(limit, len(data))} 条）")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def main():
    show("1. 最近 90 天经营概览", get_business_overview(days=90))
    show("2. 最近 7 天与前 7 天对比", compare_sales_periods(days=7))
    show("3. 最近 7 天品类表现", get_category_performance(days=7))
    show("4. GMV 下降较多的 SKU", get_declining_skus(days=7, top_n=5))
    show("5. 价格高于竞品的 SKU", get_competitor_price_gaps(top_n=5, min_gap_pct=0))
    show("6. 库存风险 SKU", get_inventory_risks(top_n=10))
    print("\n工具测试完成！以上函数可以被后续 Agent 调用。")


if __name__ == "__main__":
    main()
