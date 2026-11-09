
# test_agent_eval_v2.py

import pytest

from benchmark import CASES, expected
from agent_eval_v2 import (
    empty_state,
    execute_tool,
    evaluate_case
)


# 测试1：创建闹钟
def test_create_alarm():
    state = empty_state()

    execute_tool(
        "create_alarm",
        {"time": "07:00"},
        state
    )

    assert state["alarms"] == [
        {"time": "07:00", "label": ""}
    ]


# 测试2：禁止非法时间
def test_invalid_time():
    state = empty_state()

    with pytest.raises(ValueError):
        execute_tool(
            "create_alarm",
            {"time": "28:00"},
            state
        )

    assert state["alarms"] == []


# 测试3：多工具执行
def test_multiple_tools():
    state = empty_state()

    execute_tool(
        "create_alarm",
        {"time": "07:00"},
        state
    )

    execute_tool(
        "create_event",
        {
            "title": "组会",
            "date": "2026-11-12",
            "time": "09:00"
        },
        state
    )

    assert len(state["alarms"]) == 1
    assert len(state["events"]) == 1


# 测试4：测试用例隔离
def test_isolation():
    first = empty_state()
    second = empty_state()

    execute_tool(
        "create_alarm",
        {"time": "07:00"},
        first
    )

    assert len(first["alarms"]) == 1
    assert second["alarms"] == []


# 测试5：错误的最终状态必须 FAIL
def test_wrong_final_state():
    state = empty_state()

    execute_tool(
        "create_alarm",
        {"time": "08:00"},
        state
    )

    case = {
        "expected": expected(
            alarms=[{"time": "07:00", "label": ""}]
        )
    }

    status, reason = evaluate_case(
        case,
        state,
        [{"name": "create_alarm"}],
        []
    )

    assert status == "FAIL"
    assert "FINAL_STATE_MISMATCH" in reason


# 测试6：无需工具的任务
def test_no_tool_expected():
    case = {
        "expected": expected(),
        "expect_no_tools": True
    }

    status, reason = evaluate_case(
        case,
        empty_state(),
        [],
        []
    )

    assert status == "PASS"


# 测试7：禁止不必要的工具调用
def test_unexpected_tool_call():
    case = {
        "expected": expected(),
        "expect_no_tools": True
    }

    status, reason = evaluate_case(
        case,
        empty_state(),
        [{"name": "create_alarm"}],
        []
    )

    assert status == "FAIL"
    assert reason == "UNEXPECTED_TOOL_CALL"


# 测试8：确认 Benchmark 数量
def test_benchmark_count():
    assert len(CASES) == 12
    assert len({case["id"] for case in CASES}) == 12
