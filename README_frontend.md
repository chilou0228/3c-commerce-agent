# 3C 数码电商经营工作台：前端优化版

本版本使用京东红为主色，重新设计了导航、标题区、经营指标卡片、图表、表格、筛选控件和下载报告按钮。它继续使用已有的 `agent_tools.py` 与 `data/*.csv`，不需要大模型 API。

## 替换步骤（Windows + VS Code）

1. 先停止旧网页：在运行 Streamlit 的终端里按 `Ctrl + C`。
2. 下载 `app.py`，将其复制到你的 `3c-commerce-agent` 项目根目录，与 `agent_tools.py`、`generate_data.py` 放在同一级。出现同名文件时选择覆盖。建议先把旧版另存为 `app_old.py` 以便回滚。
3. 确认项目目录下已有 `data` 文件夹，里面包含 `products.csv`、`sales_daily.csv`、`competitor_prices.csv`、`inventory.csv` 四张表。
4. 在 VS Code 选择 `Terminal` → `New Terminal`。
5. 如果终端前面没有 `(.venv)`，运行：

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

6. 启动网页：

   ```powershell
   python -m streamlit run app.py
   ```

7. 浏览器未自动打开时，在浏览器地址栏访问终端输出的 `Local URL`，通常是 `http://localhost:8501`。

## 本版本页面

- **总览驾驶舱：** 90 天 GMV、毛利额、毛利率、转化率、访客、订单、客单价、每日 GMV 趋势及品类构成。
- **周期经营对比：** 最近 7 天与前 7 天的关键指标和变化幅度。
- **品类经营分析：** 品类 GMV 排名、毛利率对比和数据明细。
- **商品下滑诊断：** 可以筛选品类，查看 GMV 下滑 SKU，并下载 CSV。
- **竞品价格分析：** 调整价格差阈值，查看价格差异、简单单位毛利和下载结果。
- **库存风险预警：** 按缺货风险/滞销风险筛选库存清单并下载 CSV。

## 说明

- 数据均为练习用模拟数据，不代表京东或任何真实商家。
- 本地问题路由采用关键词规则，不是大模型自主推理。
- 价格与库存模块用于决策辅助，不会自动调整真实售价或下采购单。
- 若出现缺少 Streamlit / Pandas / Plotly 的错误，在已激活 `.venv` 的终端运行：

  ```powershell
  python -m pip install streamlit pandas plotly
  ```
