
# benchmark.py
# AgentEvalLab v0.2 测试数据集

def expected(alarms=None, events=None, reminders=None):
    return {
        "alarms": alarms if alarms is not None else [],
        "events": events if events is not None else [],
        "reminders": reminders if reminders is not None else []
    }


CASES = [
    {
        "id": "alarm_001",
        "category": "basic",
        "input": "设置早上7点的闹钟",
        "expected": expected(
            alarms=[{"time": "07:00", "label": ""}]
        )
    },
    {
        "id": "alarm_002",
        "category": "basic",
        "input": "设置晚上9点半的闹钟",
        "expected": expected(
            alarms=[{"time": "21:30", "label": ""}]
        )
    },
    {
        "id": "alarm_003",
        "category": "chinese_time",
        "input": "明早七点半叫醒我",
        "expected": expected(
            alarms=[{"time": "07:30", "label": ""}]
        )
    },
    {
        "id": "alarm_004",
        "category": "boundary",
        "input": "设置凌晨零点的闹钟",
        "expected": expected(
            alarms=[{"time": "00:00", "label": ""}]
        )
    },
    {
        "id": "alarm_005",
        "category": "boundary",
        "input": "设置23点59分的闹钟",
        "expected": expected(
            alarms=[{"time": "23:59", "label": ""}]
        )
    },
    {
        "id": "alarm_006",
        "category": "multi_parameter",
        "input": "设置早上7点的闹钟，备注为去图书馆",
        "expected": expected(
            alarms=[{
                "time": "07:00",
                "label": "去图书馆"
            }]
        )
    },
    {
        "id": "event_001",
        "category": "calendar",
        "input": "创建2026年11月12日14:30的会议，标题是项目讨论",
        "expected": expected(
            events=[{
                "title": "项目讨论",
                "date": "2026-11-12",
                "time": "14:30"
            }]
        )
    },
    {
        "id": "reminder_001",
        "category": "reminder",
        "input": "18点20分提醒我喝水",
        "expected": expected(
            reminders=[{
                "text": "喝水",
                "time": "18:20"
            }]
        )
    },
    {
        "id": "multi_001",
        "category": "multi_tool",
        "input": (
            "设置早上7点的闹钟，"
            "再创建2026年11月12日上午9点的会议，"
            "标题是组会"
        ),
        "expected": expected(
            alarms=[{
                "time": "07:00",
                "label": ""
            }],
            events=[{
                "title": "组会",
                "date": "2026-11-12",
                "time": "09:00"
            }]
        )
    },
    {
        "id": "multi_002",
        "category": "multi_tool",
        "input": (
            "创建2026年11月12日14点的项目讨论会议，"
            "并在13点45分提醒我准备项目讨论"
        ),
        "expected": expected(
            events=[{
                "title": "项目讨论",
                "date": "2026-11-12",
                "time": "14:00"
            }],
            reminders=[{
                "text": "准备项目讨论",
                "time": "13:45"
            }]
        )
    },
    {
        "id": "invalid_001",
        "category": "invalid_input",
        "input": "设置28点的闹钟",
        "expected": expected(),
        "expect_no_tools": True
    },
    {
        "id": "chat_001",
        "category": "no_tool",
        "input": "你好，请简单介绍一下自己",
        "expected": expected(),
        "expect_no_tools": True
    }
]
