
# agent_eval_v2.py

import os
import re
import json
import time

from datetime import date
from pathlib import Path

from openai import OpenAI, OpenAIError

from benchmark import CASES
from db import save_run, get_run_results


MODEL_NAME = "deepseek-flash"
MAX_ROUNDS = 4


# ========================================
# 1. 声明三个 Agent 工具
# ========================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_alarm",
            "description": "创建闹钟",
            "parameters": {
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "24小时制 HH:MM"
                    },
                    "label": {
                        "type": "string",
                        "description": "闹钟备注，未指定时为空字符串"
                    }
                },
                "required": ["time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "创建会议或日历事件",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {
                        "type": "string",
                        "description": "YYYY-MM-DD"
                    },
                    "time": {
                        "type": "string",
                        "description": "HH:MM"
                    }
                },
                "required": ["title", "date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "创建提醒事项",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "time": {
                        "type": "string",
                        "description": "HH:MM"
                    }
                },
                "required": ["text", "time"]
            }
        }
    }
]


# ========================================
# 2. 创建和验证模拟环境
# ========================================

def empty_state():
    return {
        "alarms": [],
        "events": [],
        "reminders": []
    }


def validate_time(value):
    pattern = r"(?:[01]\d|2[0-3]):[0-5]\d"

    if not isinstance(value, str):
        raise ValueError("INVALID_TIME")

    if not re.fullmatch(pattern, value):
        raise ValueError("INVALID_TIME")

    return value


def validate_date(value):
    if not isinstance(value, str):
        raise ValueError("INVALID_DATE")

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("INVALID_DATE")

    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("INVALID_DATE")

    return value


def validate_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("INVALID_TEXT")

    return value


def check_args(args, required, optional=()):
    if not isinstance(args, dict):
        raise ValueError("INVALID_ARGUMENTS")

    keys = set(args)
    required = set(required)
    optional = set(optional)

    if not required.issubset(keys):
        raise ValueError("MISSING_ARGUMENT")

    if keys - required - optional:
        raise ValueError("UNKNOWN_ARGUMENT")


# ========================================
# 3. 真正执行模型选择的工具
# ========================================

def execute_tool(name, args, state):

    if name == "create_alarm":
        check_args(args, ["time"], ["label"])

        alarm_time = validate_time(args["time"])
        label = args.get("label", "")

        if not isinstance(label, str):
            raise ValueError("INVALID_LABEL")

        state["alarms"].append({
            "time": alarm_time,
            "label": label
        })

    elif name == "create_event":
        check_args(args, ["title", "date", "time"])

        title = validate_text(args["title"])
        event_date = validate_date(args["date"])
        event_time = validate_time(args["time"])

        state["events"].append({
            "title": title,
            "date": event_date,
            "time": event_time
        })

    elif name == "create_reminder":
        check_args(args, ["text", "time"])

        reminder_text = validate_text(args["text"])
        reminder_time = validate_time(args["time"])

        state["reminders"].append({
            "text": reminder_text,
            "time": reminder_time
        })

    else:
        raise ValueError("UNKNOWN_TOOL")

    return {"ok": True, "tool": name}


# ========================================
# 4. 评测最终状态
# ========================================

def normalize(items):
    # 忽略列表顺序，但保留重复操作
    return sorted(
        json.dumps(item, sort_keys=True, ensure_ascii=False)
        for item in items
    )


def evaluate_case(case, state, trace, errors):

    if errors:
        return "FAIL", "; ".join(errors)

    if case.get("expect_no_tools", False):
        if trace:
            return "FAIL", "UNEXPECTED_TOOL_CALL"

        if state != case["expected"]:
            return "FAIL", "FINAL_STATE_MISMATCH"

        return "PASS", "无"

    if not trace:
        return "FAIL", "NO_TOOL_CALL"

    for key in ("alarms", "events", "reminders"):

        actual = normalize(state[key])
        expected = normalize(case["expected"][key])

        if actual != expected:
            return "FAIL", f"FINAL_STATE_MISMATCH:{key}"

    return "PASS", "无"


# ========================================
# 5. 执行单条真实 Agent 评测
# ========================================

def run_case(client, case):

    state = empty_state()
    trace = []
    errors = []

    latency_ms = 0.0
    completed = False
    reply = ""

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个手机 AI 助手。"
                "可以创建闹钟、会议和提醒。"
                "请根据用户需求选择工具。"
                "时间统一用24小时制HH:MM，"
                "日期使用YYYY-MM-DD。"
                "不合法的时间不能创建任务。"
                "复合任务需要执行所有操作。"
                "没有工具需求时直接文字回答。"
                "闹钟无备注时使用空字符串。"
            )
        },
        {
            "role": "user",
            "content": case["input"]
        }
    ]

    try:
        for round_index in range(MAX_ROUNDS):

            start = time.perf_counter()

            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    extra_body={
                        "thinking": {"type": "disabled"}
                    }
                )
            finally:
                latency_ms += (
                    time.perf_counter() - start
                ) * 1000

            message = response.choices[0].message
            calls = message.tool_calls or []

            # 模型不再请求工具：结束
            if not calls:
                completed = True
                reply = message.content or ""
                break

            # 保存模型本轮工具调用请求
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments
                        }
                    }
                    for call in calls
                ]
            })

            # Python 执行每个工具
            for call in calls:

                name = call.function.name
                raw_args = call.function.arguments

                record = {
                    "name": name,
                    "arguments": raw_args,
                    "round": round_index + 1
                }

                try:
                    args = json.loads(raw_args)

                    tool_result = execute_tool(
                        name, args, state
                    )

                    record["status"] = "SUCCESS"

                except (ValueError, KeyError, TypeError) as e:
                    error_code = f"{name}:{e}"
                    errors.append(error_code)

                    record["status"] = "FAIL"
                    record["error"] = error_code

                    tool_result = {
                        "ok": False,
                        "error": error_code
                    }

                trace.append(record)

                # 把执行结果发回模型
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False
                    )
                })

        if not completed:
            errors.append("MAX_ROUNDS_REACHED")

    except OpenAIError as e:
        return {
            "id": case["id"],
            "category": case["category"],
            "status": "ERROR",
            "reason": f"API_ERROR:{type(e).__name__}",
            "latency_ms": round(latency_ms, 2),
            "tool_calls": trace,
            "expected_state": case["expected"],
            "actual_state": state,
            "assistant_reply": reply
        }

    status, reason = evaluate_case(
        case, state, trace, errors
    )

    return {
        "id": case["id"],
        "category": case["category"],
        "status": status,
        "reason": reason,
        "latency_ms": round(latency_ms, 2),
        "tool_calls": trace,
        "expected_state": case["expected"],
        "actual_state": state,
        "assistant_reply": reply
    }


# ========================================
# 6. 批量评测
# ========================================

def select_cases():

    case_id = os.getenv("CASE_ID", "").strip()

    if case_id:
        selected = [
            case for case in CASES
            if case["id"] == case_id
        ]

        if not selected:
            raise SystemExit(f"测试用例不存在: {case_id}")

        return selected

    limit = int(os.getenv("MAX_CASES", "3"))

    if limit <= 0:
        return CASES

    return CASES[:limit]


def main():

    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise SystemExit(
            "请先设置 DEEPSEEK_API_KEY 环境变量"
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=30.0,
        max_retries=1
    )

    cases = select_cases()
    results = []

    for case in cases:
        print(f"\n正在评测: {case['id']}")

        result = run_case(client, case)
        results.append(result)

        print("状态:", result["status"])
        print("原因:", result["reason"])
        print("实际状态:", result["actual_state"])

    passed = sum(
        r["status"] == "PASS" for r in results
    )

    failed = sum(
        r["status"] == "FAIL" for r in results
    )

    errors = sum(
        r["status"] == "ERROR" for r in results
    )

    valid = passed + failed
    rate = passed / valid if valid else None

    print("\n========== v0.2 评测报告 ==========")
    print("PASS:", passed)
    print("FAIL:", failed)
    print("ERROR:", errors)

    if rate is None:
        print("有效任务成功率: N/A")
    else:
        print(f"有效任务成功率: {rate:.2%}")

    # 使用你之前的 db.py 保存结果
    run_id = save_run(
        results,
        model_name=MODEL_NAME
    )

    # 保存完整 JSON 报告
    report_dir = Path(__file__).resolve().parent / "reports"
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / f"{run_id}.json"

    report_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "model": MODEL_NAME,
                "results": results
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("本次 run_id:", run_id)
    print("数据库记录数:", len(get_run_results(run_id)))
    print("JSON 报告:", report_path)


if __name__ == "__main__":
    main()
