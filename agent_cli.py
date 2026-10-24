"""命令行版 3C 电商经营分析 Agent（Responses API + 工具调用）。

使用前：在项目根目录创建 .env 文件并设置 OPENAI_API_KEY。
本程序只允许调用 agent_tools.py 中白名单内的本地分析工具。
所有数据均为模拟数据，不代表任何真实商家的经营情况。
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from agent_tools import run_tool, TOOL_FUNCTIONS

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-6-astra")

SYSTEM_INSTRUCTIONS = """你是一名严谨的 3C 数码电商经营分析助手。
你可以调用已提供的本地数据分析工具，从 CSV 模拟数据中获取结果。
要求：
1. 涉及具体指标、商品排名、价格差异或库存状态时，先调用合适的工具，不要凭空编造数值。
2. 所有数据都是模拟数据，必须明确说明结果仅用于练习，不代表真实平台经营情况。
3. 将“观察到的指标变化”和“变化原因”区分开。没有证据时，不要把相关性说成因果关系。
4. 用中文回答，先给结论，再列关键数据和建议动作；建议应可执行，但不要直接下真实调价/采购指令。
5. 价格工具给出的毛利只是售价减单位成本的简单测算，未考虑佣金、优惠、物流等成本，不可据此断言最终利润。
6. 如果现有工具不能回答问题，明确指出缺少哪些数据，不要假装已验证原因。
"""

# JSON Schema 供模型判断何时、以什么参数调用工具。未填写的参数由 Python 函数使用默认值。
TOOLS = [
    {
        "type": "function",
        "name": "get_business_overview",
        "description": "查询最近若干天整体经营概览，包括 GMV、毛利、访客、订单、转化率和客单价。默认 90 天。",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "查询天数，1 到 90；不指定时使用 90。", "minimum": 1, "maximum": 90}
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "compare_sales_periods",
        "description": "比较最近一个周期与紧邻的前一个同长度周期。默认比较最近 7 天与前 7 天。",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "每个周期的天数，1 到 90；默认 7。", "minimum": 1, "maximum": 90}
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_category_performance",
        "description": "查询最近若干天各品类 GMV、毛利、销量和毛利率排名。默认 7 天。",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "查询天数，1 到 90；默认 7。", "minimum": 1, "maximum": 90}
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_declining_skus",
        "description": "查询 GMV 下降最多的商品，可限定品类。默认取最近 7 天对比前 7 天、最多 10 个商品。",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "每个对比周期的天数，1 到 90；默认 7。", "minimum": 1, "maximum": 90},
                "top_n": {"type": "integer", "description": "返回商品数量，1 到 100；默认 10。", "minimum": 1, "maximum": 100},
                "category": {"type": "string", "description": "可选品类名称，例如手机、耳机、平板电脑或笔记本电脑。省略表示全部品类。"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_competitor_price_gaps",
        "description": "查询本商品标价高于竞品的 SKU，并返回价格差百分比及简单单位毛利测算。默认取差价最大的 10 个。",
        "parameters": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "返回商品数量，1 到 100；默认 10。", "minimum": 1, "maximum": 100},
                "min_gap_pct": {"type": "number", "description": "最小高价幅度百分比；默认 0。", "minimum": 0},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_inventory_risks",
        "description": "查询缺货风险或滞销风险商品。默认返回风险商品，优先展示库存覆盖天数短的 SKU。",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["缺货风险", "滞销风险", "正常"], "description": "可选状态；省略时返回所有风险商品。"},
                "top_n": {"type": "integer", "description": "返回商品数量，1 到 100；默认 20。", "minimum": 1, "maximum": 100},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]


def _make_client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "没有找到 OPENAI_API_KEY。请在项目根目录创建 .env 文件，设置 OPENAI_API_KEY=你的密钥，然后重试。"
        )
    return OpenAI()


def ask_agent(client: OpenAI, question: str, max_tool_rounds: int = 5) -> str:
    """提交问题，由模型选择工具；工具只能从 TOOL_FUNCTIONS 白名单中执行。"""
    input_items: list[Any] = [{"role": "user", "content": question}]

    for _ in range(max_tool_rounds):
        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_INSTRUCTIONS,
            tools=TOOLS,
            input=input_items,
        )
        calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]

        if not calls:
            return response.output_text or "模型没有返回文本，请换一个更明确的问题再试。"

        # 保留模型本轮的输出项目，之后再补充本地工具结果。
        input_items.extend(response.output)

        for call in calls:
            tool_name = call.name
            try:
                if tool_name not in TOOL_FUNCTIONS:
                    raise ValueError(f"不允许调用的工具：{tool_name}")
                arguments = json.loads(call.arguments or "{}")
                if not isinstance(arguments, dict):
                    raise ValueError("工具参数必须是 JSON 对象。")
                print(f"\n[工具调用] {tool_name}({json.dumps(arguments, ensure_ascii=False)})")
                result = run_tool(tool_name, **arguments)
                tool_output = {"ok": True, "data": result}
            except Exception as exc:
                # 将可读错误反馈给模型；不执行未知工具，也不允许任意代码执行。
                tool_output = {"ok": False, "error": str(exc)}

            input_items.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(tool_output, ensure_ascii=False, default=str),
            })

    # 达到调用轮数限制后，让模型仅根据已有工具结果作总结，不再申请新工具。
    final_response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_INSTRUCTIONS + "\n本次工具调用次数已达到上限。请只根据已返回的工具结果作答，不要声称执行过未执行的查询。",
        tools=TOOLS,
        tool_choice="none",
        input=input_items,
    )
    return final_response.output_text or "已达到工具调用次数上限，请把问题拆小后重试。"


def main() -> None:
    try:
        client = _make_client()
    except Exception as exc:
        print(f"配置错误：{exc}")
        sys.exit(1)

    print("=" * 65)
    print("3C 数码电商经营分析 Agent（命令行版）")
    print(f"模型：{MODEL}")
    print("输入业务问题后按回车；输入 exit 或 quit 退出。")
    print("注意：数据为模拟数据；调用模型 API 可能产生费用。")
    print("=" * 65)

    while True:
        try:
            question = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            break
        if question.lower() in {"exit", "quit", "退出"}:
            print("已退出。")
            break
        if not question:
            continue
        try:
            print("\nAgent 正在分析……\n")
            answer = ask_agent(client, question)
            print("Agent：\n" + answer)
        except Exception as exc:
            print(f"\n调用失败：{exc}")
            print("请检查 API 密钥、模型名称、网络和 API 账户额度；不要把密钥发给他人。")


if __name__ == "__main__":
    main()
