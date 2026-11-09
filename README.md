
# AgentEvalLab

基于 Python 的 LLM Agent 工具调用自动化评测项目。

## 项目介绍

通过真实大模型 Function Calling、模拟工具执行和最终状态验证，
评估 Agent 在任务执行中的正确性与可靠性。

## 已实现功能

- DeepSeek API Function Calling
- 闹钟工具模拟执行
- 多条测试用例顺序评测
- PASS / FAIL / ERROR 结果分类
- 基础错误归因
- 模型 API 调用耗时统计
- 工具调用轨迹记录
- SQLite 评测结果持久化

## 技术栈

Python、DeepSeek API、OpenAI Python SDK、SQLite

## 快速开始

安装依赖：

    py -m pip install -r requirements.txt

设置 DEEPSEEK_API_KEY 环境变量后运行：

    py real_agent.py

## 当前限制

- 仅支持单轮闹钟工具调用
- 评测任务顺序执行
- 尚未支持多模型 A/B 对比
- 尚未实现并发调度与可视化报告

## 后续计划

- 扩展 Benchmark 测试集
- pytest 自动化测试
- 多工具 Agent
- asyncio 并发评测
- 模型版本回归检测
