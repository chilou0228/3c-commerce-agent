# 第 4 阶段：接入大模型和工具调用

## 文件
- `agent_tools.py`：可复核的本地数据分析工具（已修正客单价变化指标的命名与计算）。
- `agent_cli.py`：基于 OpenAI Responses API 的命令行 Agent。
- `.env.example`：环境变量模板。请复制为 `.env` 并填写 API Key。
- `.gitignore`：防止密钥、虚拟环境和本地模拟数据被误上传。

## 运行前提
1. 将这些文件放到项目根目录，和 `data/` 文件夹同级。
2. 项目虚拟环境中已安装 `openai`、`python-dotenv`、`pandas`。
3. 配置了可用的 API Key，并确认 API 账户可以调用所选模型。API 用量单独计费。

## Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade openai python-dotenv
Copy-Item .env.example .env
# 用 VS Code 打开 .env，填写 OPENAI_API_KEY，保存
python agent_cli.py
```

## 测试问题
- `请查询最近7天各品类的GMV排名，并总结前三名。`
- `比较最近7天和前7天的整体经营表现。`
- `列出手机品类GMV下降最多的5个SKU。`
- `哪些SKU的价格高于竞品最多？请提醒我调价风险。`
- `有哪些缺货风险商品？`

这套数据为合成数据，不代表任何真实平台或商家经营情况。
