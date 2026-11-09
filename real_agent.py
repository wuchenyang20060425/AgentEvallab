
import os
import json
import re
import time

from openai import OpenAI, OpenAIError
from db import save_run, get_run_results


# ==========================================
# 1. 配置 DeepSeek API
# ==========================================

MODEL_NAME = "deepseek-flash"

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    timeout=30.0,
    max_retries=1
)


# ==========================================
# 2. 定义 Agent 可以调用的工具
# ==========================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "create_alarm",
            "description": "创建一个闹钟",
            "parameters": {
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "24小时制时间，格式HH:MM，例如07:00"
                    }
                },
                "required": ["time"]
            }
        }
    }
]


# ==========================================
# 3. 调用真实大模型
# ==========================================

def real_agent(user_input):

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个闹钟助手。"
                    "用户要求创建闹钟时，请调用create_alarm工具。"
                    "时间统一使用24小时制HH:MM格式。"
                )
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        tools=tools,
        tool_choice="auto",
        extra_body={
            "thinking": {"type": "disabled"}
        }
    )

    return response.choices[0].message


# ==========================================
# 4. 模拟执行闹钟工具
# ==========================================

def create_alarm(alarm_time, alarms):

    if not isinstance(alarm_time, str):
        raise ValueError("时间必须是字符串")

    pattern = r"(?:[01]\d|2[0-3]):[0-5]\d"

    if not re.fullmatch(pattern, alarm_time):
        raise ValueError("无效的时间格式")

    alarms.append({
        "time": alarm_time
    })

    return "闹钟创建成功"


# ==========================================
# 5. 自动评测函数
# ==========================================

def evaluate(alarms, expected_time):

    if len(alarms) == 0:
        return "FAIL", "未创建闹钟"

    if len(alarms) > 1:
        return "FAIL", "创建了多个闹钟"

    if alarms[0]["time"] != expected_time:
        return "FAIL", "闹钟时间错误"

    return "PASS", "无"


# ==========================================
# 6. 定义测试数据集
# ==========================================

test_cases = [
    {
        "id": "alarm_001",
        "input": "帮我设置早上7点的闹钟",
        "expected_time": "07:00"
    },
    {
        "id": "alarm_002",
        "input": "帮我设置晚上9点半的闹钟",
        "expected_time": "21:30"
    },
    {
        "id": "alarm_003",
        "input": "帮我设置早上6点的闹钟",
        "expected_time": "06:00"
    }
]


# ==========================================
# 7. 批量运行真实模型评测
# ==========================================

def run_evaluation():

    results = []

    for case in test_cases:

        print(f"\n正在评测: {case['id']}")

        # 每条测试用例使用独立环境
        alarms = []
        errors = []
        tool_trace = []

        # ------------------------------
        # 7.1 调用真实模型并记录耗时
        # ------------------------------

        start = time.perf_counter()

        try:
            message = real_agent(case["input"])

        except OpenAIError as e:
            latency_ms = round(
                (time.perf_counter() - start) * 1000,
                2
            )

            results.append({
                "id": case["id"],
                "status": "ERROR",
                "reason": f"API_ERROR: {type(e).__name__}",
                "latency_ms": latency_ms,
                "tool_calls": []
            })

            print("模型 API 调用失败:", e)
            continue

        latency_ms = round(
            (time.perf_counter() - start) * 1000,
            2
        )

        print("模型响应耗时:", latency_ms, "ms")

        # ------------------------------
        # 7.2 获取模型工具调用
        # ------------------------------

        tool_calls = message.tool_calls or []

        if not tool_calls:
            errors.append("NO_TOOL_CALL")

        # ------------------------------
        # 7.3 执行工具
        # ------------------------------

        for call in tool_calls:

            tool_name = call.function.name
            raw_arguments = call.function.arguments

            tool_trace.append({
                "name": tool_name,
                "arguments": raw_arguments
            })

            print("模型选择工具:", tool_name)
            print("模型生成参数:", raw_arguments)

            try:
                if tool_name != "create_alarm":
                    raise ValueError("WRONG_TOOL")

                arguments = json.loads(raw_arguments)

                if not isinstance(arguments, dict):
                    raise ValueError("INVALID_ARGUMENTS")

                create_alarm(
                    arguments["time"],
                    alarms
                )

            except (ValueError, KeyError, TypeError) as e:
                errors.append(
                    f"TOOL_ERROR: {str(e)}"
                )

        # ------------------------------
        # 7.4 自动评分
        # ------------------------------

        status, reason = evaluate(
            alarms,
            case["expected_time"]
        )

        if errors:
            status = "FAIL"
            reason = "; ".join(errors)

        # ------------------------------
        # 7.5 保存单条测试结果
        # ------------------------------

        results.append({
            "id": case["id"],
            "status": status,
            "reason": reason,
            "latency_ms": latency_ms,
            "tool_calls": tool_trace
        })

        print("实际闹钟:", alarms)
        print("评测结果:", status)
        print("失败原因:", reason)

    return results


# ==========================================
# 8. 统计评测结果
# ==========================================

def print_report(results):

    total = len(results)

    passed = sum(
        1 for item in results
        if item["status"] == "PASS"
    )

    failed = sum(
        1 for item in results
        if item["status"] == "FAIL"
    )

    api_errors = sum(
        1 for item in results
        if item["status"] == "ERROR"
    )

    valid_total = passed + failed

    success_rate = (
        passed / valid_total
        if valid_total else 0
    )

    print("\n========== 评测报告 ==========")

    for item in results:
        print(
            item["id"],
            item["status"],
            item["reason"],
            f'{item["latency_ms"]}ms'
        )

    print("\n总测试数:", total)
    print("有效评测数:", valid_total)
    print("PASS:", passed)
    print("FAIL:", failed)
    print("API错误数:", api_errors)
    print(f"有效评测成功率: {success_rate:.2%}")


# ==========================================
# 9. 主程序入口
# ==========================================

if __name__ == "__main__":

    # 执行批量评测
    results = run_evaluation()

    # 打印评测报告
    print_report(results)

    # 保存进 SQLite 数据库
    run_id = save_run(
        results,
        model_name=MODEL_NAME
    )

    print("\n评测批次 ID:", run_id)
    print("数据库保存成功!")

    # 从数据库重新查询
    rows = get_run_results(run_id)

    print("\n========== 数据库查询 ==========")

    for row in rows:
        print(row)
