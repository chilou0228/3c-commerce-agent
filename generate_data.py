"""为 3C 数码电商经营分析 Agent 生成练习用模拟数据。
注意：这些均为合成数据，不代表任何真实平台或商家的经营情况。
"""
from pathlib import Path
from datetime import date, timedelta
import random
import pandas as pd

# 固定随机种子，保证每次生成的数据结构和模式基本可复现。
random.seed(42)
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CATEGORY_CONFIG = {
    "手机": {
        "brands": ["星云", "远航", "极光", "云帆"],
        "price_range": (999, 6999),
        "visitors_range": (220, 700),
        "conversion_range": (0.020, 0.035),
    },
    "笔记本电脑": {
        "brands": ["凌峰", "北辰", "远航", "星云"],
        "price_range": (2999, 9999),
        "visitors_range": (120, 420),
        "conversion_range": (0.012, 0.025),
    },
    "耳机": {
        "brands": ["声浪", "蓝鲸", "极光", "云帆"],
        "price_range": (99, 1999),
        "visitors_range": (160, 520),
        "conversion_range": (0.025, 0.045),
    },
    "平板电脑": {
        "brands": ["星云", "凌峰", "北辰", "远航"],
        "price_range": (799, 5999),
        "visitors_range": (100, 360),
        "conversion_range": (0.015, 0.030),
    },
}

# 1. 生成商品主数据：4 个品类，每个品类 25 个 SKU，共 100 个 SKU。
products = []
sku_number = 1
for category, config in CATEGORY_CONFIG.items():
    for i in range(25):
        sku = f"SKU{sku_number:04d}"
        brand = random.choice(config["brands"])
        current_price = float(round(random.uniform(*config["price_range"]) / 10) * 10)
        unit_cost = round(current_price * random.uniform(0.68, 0.88), 2)
        products.append({
            "sku": sku,
            "product_name": f"{brand}{category}模拟款{i + 1:02d}",
            "category": category,
            "brand": brand,
            "current_price": current_price,
            "unit_cost": unit_cost,
            "supplier_lead_days": random.randint(2, 12),
            # 以下两个字段用于生成模拟销售记录，暂不写入商品表。
            "_base_visitors": random.randint(*config["visitors_range"]),
            "_base_conversion_rate": random.uniform(*config["conversion_range"]),
        })
        sku_number += 1

# 设置一些可被后续分析发现的模拟问题：流量下滑、转化下降、竞品更便宜、库存风险。
traffic_issue_skus = {products[i]["sku"] for i in [4, 18, 30, 55, 82, 94]}
conversion_issue_skus = {products[i]["sku"] for i in [10, 24, 43, 66, 88, 97]}
price_disadvantaged_skus = {products[i]["sku"] for i in [7, 28, 49, 63, 78, 92]}
low_stock_skus = {products[i]["sku"] for i in [10, 28, 45, 61, 89]}
oversupply_skus = {products[i]["sku"] for i in [16, 41, 72, 86, 97]}

# 2. 生成最近 90 天的销售和流量记录（截至昨天，避免当天数据不完整）。
end_date = date.today() - timedelta(days=1)
dates = [end_date - timedelta(days=i) for i in range(89, -1, -1)]
sales_rows = []

for product in products:
    for day_index, current_day in enumerate(dates):
        is_weekend = current_day.weekday() in (5, 6)
        weekend_factor = 1.12 if is_weekend else 1.0
        gradual_trend = 0.96 + 0.08 * day_index / max(1, len(dates) - 1)
        traffic_factor = weekend_factor * gradual_trend * random.uniform(0.82, 1.18)
        is_recent_14_days = day_index >= len(dates) - 14

        if product["sku"] in traffic_issue_skus and is_recent_14_days:
            traffic_factor *= 0.55

        visitors = max(20, int(product["_base_visitors"] * traffic_factor))
        add_to_cart_rate = product["_base_conversion_rate"] * random.uniform(2.4, 3.2)
        add_to_cart = min(visitors, int(round(visitors * add_to_cart_rate)))

        conversion_rate = product["_base_conversion_rate"] * random.uniform(0.80, 1.20)
        if product["sku"] in conversion_issue_skus and is_recent_14_days:
            conversion_rate *= 0.55
        if product["sku"] in price_disadvantaged_skus:
            conversion_rate *= 0.82

        orders = min(add_to_cart, max(0, int(round(visitors * conversion_rate))))
        units_sold = orders

        # 周末做轻微折扣；其他日期少量随机促销日。
        discount_factor = 0.98 if is_weekend else 1.0
        if not is_weekend and random.random() < 0.04:
            discount_factor = random.uniform(0.92, 0.97)

        sale_price = round(product["current_price"] * discount_factor, 2)
        gmv = round(units_sold * sale_price, 2)
        gross_profit = round(units_sold * (sale_price - product["unit_cost"]), 2)

        sales_rows.append({
            "date": current_day.isoformat(),
            "sku": product["sku"],
            "visitors": visitors,
            "add_to_cart": add_to_cart,
            "orders": orders,
            "units_sold": units_sold,
            "sale_price": sale_price,
            "gmv": gmv,
            "gross_profit": gross_profit,
        })

# 3. 生成竞品价格快照。部分 SKU 被刻意设置为竞品价格更低，方便练习价格分析。
competitor_rows = []
for product in products:
    if product["sku"] in price_disadvantaged_skus:
        competitor_price = product["current_price"] * random.uniform(0.82, 0.90)
    else:
        competitor_price = product["current_price"] * random.uniform(0.94, 1.06)
    competitor_rows.append({
        "snapshot_date": end_date.isoformat(),
        "sku": product["sku"],
        "competitor_name": random.choice(["竞品平台A", "竞品平台B", "竞品平台C"]),
        "competitor_price": round(competitor_price, 2),
    })

# 4. 根据最近 7 天销量，生成当前库存快照和库存风险标签。
sales_df = pd.DataFrame(sales_rows)
recent_start = (end_date - timedelta(days=6)).isoformat()
recent_sales = sales_df[sales_df["date"] >= recent_start]
avg_daily_sales = recent_sales.groupby("sku")["units_sold"].mean().to_dict()
inventory_rows = []

for product in products:
    sku = product["sku"]
    average = float(avg_daily_sales.get(sku, 0))

    if sku in low_stock_skus:
        current_stock = max(1, int(average * random.uniform(1.0, 2.0)))
    elif sku in oversupply_skus:
        current_stock = max(1, int(average * random.uniform(50, 70)))
    else:
        current_stock = max(1, int(average * random.uniform(7, 35)))

    cover_days = round(current_stock / average, 1) if average > 0 else 999.0
    safety_stock = max(1, int(round(average * 3)))

    if cover_days < product["supplier_lead_days"]:
        status = "缺货风险"
    elif cover_days > 45:
        status = "滞销风险"
    else:
        status = "正常"

    inventory_rows.append({
        "snapshot_date": end_date.isoformat(),
        "sku": sku,
        "current_stock": current_stock,
        "avg_daily_sales_7d": round(average, 2),
        "stock_cover_days": cover_days,
        "supplier_lead_days": product["supplier_lead_days"],
        "safety_stock": safety_stock,
        "inventory_status": status,
    })

# 5. 导出 CSV 文件。utf-8-sig 方便使用 Excel 打开中文字段。
products_df = pd.DataFrame(products)[[
    "sku", "product_name", "category", "brand", "current_price", "unit_cost", "supplier_lead_days"
]]
products_df["gross_margin_rate"] = (
    (products_df["current_price"] - products_df["unit_cost"]) / products_df["current_price"]
).round(4)
competitor_df = pd.DataFrame(competitor_rows)
inventory_df = pd.DataFrame(inventory_rows)

products_df.to_csv(DATA_DIR / "products.csv", index=False, encoding="utf-8-sig")
sales_df.to_csv(DATA_DIR / "sales_daily.csv", index=False, encoding="utf-8-sig")
competitor_df.to_csv(DATA_DIR / "competitor_prices.csv", index=False, encoding="utf-8-sig")
inventory_df.to_csv(DATA_DIR / "inventory.csv", index=False, encoding="utf-8-sig")

print("\n数据生成成功！")
print(f"数据日期范围：{dates[0].isoformat()} 至 {dates[-1].isoformat()}")
print(f"商品数量：{len(products_df)}")
print(f"销售记录数：{len(sales_df)}")
print(f"竞品价格记录数：{len(competitor_df)}")
print(f"库存记录数：{len(inventory_df)}")
print("生成的文件：")
for filename in ["products.csv", "sales_daily.csv", "competitor_prices.csv", "inventory.csv"]:
    print(f"  data/{filename}")
print(f"90 天 GMV 合计：{sales_df['gmv'].sum():,.2f}")
print("注意：以上均为练习用模拟数据，不代表任何真实平台或商家的经营情况。")
