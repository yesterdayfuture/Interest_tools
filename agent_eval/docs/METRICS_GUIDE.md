# AgentEval 评估指标说明文档

[English Metrics Guide](#agenteval-metrics-guide)

---

## 目录

1. [指标概览](#指标概览)
2. [核心指标详解](#核心指标详解)
3. [默认权重配置](#默认权重配置)
4. [自定义指标](#自定义指标)

---

## 指标概览

AgentEval 提供了 **5个核心评估指标**，从多个维度全面评估智能体的执行质量：

| 指标名称 | 英文名称 | 默认权重 | 评估维度 |
|---------|---------|---------|---------|
| 正确性 | Correctness | 0.30 | 输出结果与预期的语义相似度 |
| 步骤效率 | StepRatio | 0.15 | 执行步骤数与最优步骤的比率 |
| 工具调用效率 | ToolCallRatio | 0.20 | 工具调用次数与最优次数的比率 |
| 任务解决率 | SolveRate | 0.25 | 任务是否成功完成 |
| 执行延迟率 | LatencyRatio | 0.10 | 执行时间与最优时间的比率 |

---

## 核心指标详解

### 1. 正确性 (Correctness)

**指标说明**

评估智能体输出与预期结果的匹配程度，使用 N-gram 文本相似度算法计算语义相似度。

**算法特点**

- 支持 1-4 gram 的多粒度匹配
- 使用 jieba 进行中文分词，更适合中文语义
- 综合精确率、召回率和 F1 分数
- 可配置的 n-gram 权重

**评分逻辑**

| 分数范围 | 匹配类型 | 说明 |
|---------|---------|------|
| ≥ 0.95 | exact | 精确匹配 |
| ≥ 0.70 | high_similarity | 高度相似 |
| ≥ 0.40 | partial | 部分匹配 |
| > 0 | low_similarity | 低度相似 |
| = 0 | no_match | 无匹配 |

**使用示例**

```python
from agent_eval import AgentEvaluator
from agent_eval.models import ExpectedResult

# 准备预期结果
expected = ExpectedResult(
    query="北京天气",
    expected_output="北京今天晴朗，气温20度"
)

# 执行评估
evaluator = AgentEvaluator()
execution = get_last_execution()  # 获取执行记录
result = evaluator.evaluate(execution, expected)

# 查看正确性分数
correctness_score = [s for s in result.metric_scores if s.metric_name == "Correctness"][0]
print(f"正确性分数: {correctness_score.score:.2%}")
print(f"匹配类型: {correctness_score.details['match_type']}")
```

---

### 2. 步骤效率 (StepRatio)

**指标说明**

评估智能体执行步骤数与最优步骤数的比率，用于衡量智能体的执行效率。

**评分标准**

| 步骤比率 | 分数 | 说明 |
|---------|------|------|
| ≤ 1.0 | 1.0 | 完美或更优 |
| ≤ 1.5 | 0.8 | 步骤略多 |
| ≤ 2.0 | 0.6 | 步骤较多 |
| ≤ 3.0 | 0.4 | 步骤多很多 |
| > 3.0 | 0.2 | 步骤过多 |

**使用示例**

```python
from agent_eval.models import ExpectedResult

# 准备预期结果，指定最优步骤
expected = ExpectedResult(
    query="查询天气",
    expected_steps=["解析地点", "获取数据", "格式化输出"],
    expected_step_count=3
)

# 评估时会自动比较实际步骤数与最优步骤数
```

---

### 3. 工具调用效率 (ToolCallRatio)

**指标说明**

评估智能体工具调用次数与最优次数的比率，同时考虑工具调用序列的匹配度。

**评分维度**

1. **数量效率**：实际调用次数 / 最优调用次数
2. **序列匹配**：实际调用序列与预期序列的 F1 分数

**综合分数** = (数量分数 + 序列匹配分数) / 2

**评分标准（数量维度）**

| 调用比率 | 分数 | 说明 |
|---------|------|------|
| ≤ 1.0 | 1.0 | 完美或更优 |
| ≤ 1.5 | 0.8 | 调用略多 |
| ≤ 2.0 | 0.6 | 调用较多 |
| ≤ 3.0 | 0.4 | 调用多很多 |
| > 3.0 | 0.2 | 调用过多 |

**使用示例**

```python
from agent_eval.models import ExpectedResult

# 准备预期结果，指定工具调用序列
expected = ExpectedResult(
    query="搜索信息",
    expected_tool_calls=["search_web", "extract_content", "summarize"],
    expected_tool_count=3
)
```

---

### 4. 任务解决率 (SolveRate)

**指标说明**

评估智能体是否成功完成任务，综合考虑执行状态、输出内容和预期结果匹配度。

**评分逻辑（无预期输出时）**

| 执行状态 | 输出 | 分数 | 说明 |
|---------|------|------|------|
| 成功 | 有输出 | 1.0 | 任务执行成功且有输出 |
| 成功 | 无输出 | 0.7 | 任务执行成功但无输出 |
| 失败 | - | 0.0 | 任务未成功执行 |

**评分逻辑（有预期输出时）**

| 匹配情况 | 分数 | 说明 |
|---------|------|------|
| 精确匹配 | 1.0 | 输出与预期完全一致 |
| 包含预期 | 0.9 | 输出包含预期内容 |
| 关键元素匹配度 ≥ 80% | 0.8 | 关键元素高度匹配 |
| 关键元素匹配度 ≥ 50% | 0.5 | 关键元素部分匹配 |
| 无匹配 | 0.2 | 输出与预期无匹配 |
| 无输出/执行失败 | 0.0 | 任务未完成 |

**使用示例**

```python
from agent_eval.models import ExpectedResult

# 简单场景：只检查执行成功
evaluator = AgentEvaluator()
result = evaluator.evaluate(execution)  # 不传递 expected

# 复杂场景：检查输出匹配
expected = ExpectedResult(
    query="计算问题",
    expected_output="答案是42"
)
result = evaluator.evaluate(execution, expected)
```

---

### 5. 执行延迟率 (LatencyRatio)

**指标说明**

评估智能体执行时间与最优时间的比率，用于衡量智能体的执行效率。

**评分标准**

| 时间比率 | 分数 | 说明 |
|---------|------|------|
| ≤ 1.0 | 1.0 | 完美或更优 |
| ≤ 1.5 | 0.85 | 略慢 |
| ≤ 2.0 | 0.7 | 较慢 |
| ≤ 3.0 | 0.5 | 慢很多 |
| ≤ 5.0 | 0.3 | 过慢 |
| > 5.0 | 0.1 | 极慢 |

**使用示例**

```python
from agent_eval.models import ExpectedResult

# 指定最优执行时间（毫秒）
expected = ExpectedResult(
    query="快速查询",
    expected_duration_ms=1000  # 期望1秒内完成
)
```

---

## 默认权重配置

AgentEval 的默认权重配置如下：

```python
DEFAULT_METRIC_WEIGHTS = {
    "Correctness": 0.30,      # 正确性：最重要的指标
    "SolveRate": 0.25,        # 解决率：任务完成度
    "ToolCallRatio": 0.20,    # 工具调用效率
    "StepRatio": 0.15,        # 步骤效率
    "LatencyRatio": 0.10      # 延迟率：相对次要的指标
}
```

**权重调整建议**

- **对话型智能体**：提高 Correctness 和 SolveRate 权重
- **工具型智能体**：提高 ToolCallRatio 权重
- **实时型智能体**：提高 LatencyRatio 权重
- **复杂任务智能体**：提高 StepRatio 权重

---

## 自定义指标

AgentEval 支持自定义评估指标，只需继承 `BaseMetric` 类：

```python
from agent_eval.metrics import BaseMetric
from agent_eval.models import AgentExecution, ExpectedResult, MetricScore

class ResponseLengthMetric(BaseMetric):
    """评估回答长度是否适中"""
    
    def __init__(self, weight=0.1):
        super().__init__("ResponseLength", weight)
    
    def calculate(self, execution: AgentExecution, expected: ExpectedResult = None) -> MetricScore:
        output_len = len(execution.final_output or "")
        
        # 理想长度：100-500字符
        if 100 <= output_len <= 500:
            score = 1.0
        elif output_len < 100:
            score = output_len / 100
        else:
            score = max(0, 1 - (output_len - 500) / 500)
        
        return self._create_metric_score(
            score=score,
            details={"length": output_len, "ideal_range": "100-500"}
        )

# 使用自定义指标
evaluator = AgentEvaluator()
evaluator.metric_calculator.metrics["ResponseLength"] = ResponseLengthMetric(weight=0.1)
```

---

# AgentEval Metrics Guide

[中文指标说明](#agenteval-评估指标说明文档)

---

## Table of Contents

1. [Metrics Overview](#metrics-overview)
2. [Core Metrics Details](#core-metrics-details)
3. [Default Weight Configuration](#default-weight-configuration)
4. [Custom Metrics](#custom-metrics)

---

## Metrics Overview

AgentEval provides **5 core evaluation metrics** to comprehensively assess agent execution quality from multiple dimensions:

| Metric Name | Chinese Name | Default Weight | Evaluation Dimension |
|------------|--------------|----------------|---------------------|
| Correctness | 正确性 | 0.30 | Semantic similarity between output and expected result |
| StepRatio | 步骤效率 | 0.15 | Ratio of actual steps to optimal steps |
| ToolCallRatio | 工具调用效率 | 0.20 | Ratio of tool calls to optimal count |
| SolveRate | 任务解决率 | 0.25 | Whether the task was completed successfully |
| LatencyRatio | 执行延迟率 | 0.10 | Ratio of execution time to optimal time |

---

## Core Metrics Details

### 1. Correctness

**Description**

Evaluates the match between agent output and expected result using N-gram text similarity algorithm.

**Algorithm Features**

- Supports multi-granularity matching with 1-4 grams
- Uses jieba for Chinese word segmentation, better for Chinese semantics
- Combines precision, recall, and F1 scores
- Configurable n-gram weights

**Scoring Logic**

| Score Range | Match Type | Description |
|------------|-----------|-------------|
| ≥ 0.95 | exact | Exact match |
| ≥ 0.70 | high_similarity | High similarity |
| ≥ 0.40 | partial | Partial match |
| > 0 | low_similarity | Low similarity |
| = 0 | no_match | No match |

**Usage Example**

```python
from agent_eval import AgentEvaluator
from agent_eval.models import ExpectedResult

# Prepare expected result
expected = ExpectedResult(
    query="Beijing weather",
    expected_output="Beijing is sunny today, 20 degrees"
)

# Execute evaluation
evaluator = AgentEvaluator()
execution = get_last_execution()  # Get execution record
result = evaluator.evaluate(execution, expected)

# View correctness score
correctness_score = [s for s in result.metric_scores if s.metric_name == "Correctness"][0]
print(f"Correctness: {correctness_score.score:.2%}")
print(f"Match type: {correctness_score.details['match_type']}")
```

---

### 2. StepRatio

**Description**

Evaluates the ratio of actual steps to optimal steps, measuring agent execution efficiency.

**Scoring Criteria**

| Step Ratio | Score | Description |
|-----------|-------|-------------|
| ≤ 1.0 | 1.0 | Perfect or better |
| ≤ 1.5 | 0.8 | Slightly more steps |
| ≤ 2.0 | 0.6 | More steps |
| ≤ 3.0 | 0.4 | Many more steps |
| > 3.0 | 0.2 | Too many steps |

**Usage Example**

```python
from agent_eval.models import ExpectedResult

# Prepare expected result with optimal steps
expected = ExpectedResult(
    query="Query weather",
    expected_steps=["Parse location", "Fetch data", "Format output"],
    expected_step_count=3
)

# Evaluation automatically compares actual vs optimal steps
```

---

### 3. ToolCallRatio

**Description**

Evaluates the ratio of tool calls to optimal count, considering both quantity and sequence matching.

**Scoring Dimensions**

1. **Quantity Efficiency**: Actual calls / Optimal calls
2. **Sequence Matching**: F1 score of actual vs expected sequence

**Combined Score** = (Quantity Score + Sequence Match Score) / 2

**Scoring Criteria (Quantity)**

| Call Ratio | Score | Description |
|-----------|-------|-------------|
| ≤ 1.0 | 1.0 | Perfect or better |
| ≤ 1.5 | 0.8 | Slightly more calls |
| ≤ 2.0 | 0.6 | More calls |
| ≤ 3.0 | 0.4 | Many more calls |
| > 3.0 | 0.2 | Too many calls |

**Usage Example**

```python
from agent_eval.models import ExpectedResult

# Prepare expected result with tool call sequence
expected = ExpectedResult(
    query="Search information",
    expected_tool_calls=["search_web", "extract_content", "summarize"],
    expected_tool_count=3
)
```

---

### 4. SolveRate

**Description**

Evaluates whether the agent successfully completed the task, considering execution status, output content, and expected result matching.

**Scoring Logic (No Expected Output)**

| Status | Output | Score | Description |
|--------|--------|-------|-------------|
| Success | Has output | 1.0 | Task succeeded with output |
| Success | No output | 0.7 | Task succeeded without output |
| Failed | - | 0.0 | Task failed |

**Scoring Logic (With Expected Output)**

| Match Condition | Score | Description |
|----------------|-------|-------------|
| Exact match | 1.0 | Output exactly matches expected |
| Contains expected | 0.9 | Output contains expected content |
| Key elements ≥ 80% | 0.8 | Key elements highly matched |
| Key elements ≥ 50% | 0.5 | Key elements partially matched |
| No match | 0.2 | No match between output and expected |
| No output/Failed | 0.0 | Task incomplete |

**Usage Example**

```python
from agent_eval.models import ExpectedResult

# Simple scenario: only check execution success
evaluator = AgentEvaluator()
result = evaluator.evaluate(execution)  # Don't pass expected

# Complex scenario: check output matching
expected = ExpectedResult(
    query="Calculate",
    expected_output="The answer is 42"
)
result = evaluator.evaluate(execution, expected)
```

---

### 5. LatencyRatio

**Description**

Evaluates the ratio of execution time to optimal time, measuring agent execution efficiency.

**Scoring Criteria**

| Time Ratio | Score | Description |
|-----------|-------|-------------|
| ≤ 1.0 | 1.0 | Perfect or better |
| ≤ 1.5 | 0.85 | Slightly slow |
| ≤ 2.0 | 0.7 | Slow |
| ≤ 3.0 | 0.5 | Much slower |
| ≤ 5.0 | 0.3 | Too slow |
| > 5.0 | 0.1 | Extremely slow |

**Usage Example**

```python
from agent_eval.models import ExpectedResult

# Specify optimal execution time (milliseconds)
expected = ExpectedResult(
    query="Quick query",
    expected_duration_ms=1000  # Expect completion within 1 second
)
```

---

## Default Weight Configuration

AgentEval's default weight configuration:

```python
DEFAULT_METRIC_WEIGHTS = {
    "Correctness": 0.30,      # Correctness: Most important metric
    "SolveRate": 0.25,        # Solve rate: Task completion
    "ToolCallRatio": 0.20,    # Tool call efficiency
    "StepRatio": 0.15,        # Step efficiency
    "LatencyRatio": 0.10      # Latency: Relatively less important
}
```

**Weight Adjustment Recommendations**

- **Conversational Agents**: Increase Correctness and SolveRate weights
- **Tool-based Agents**: Increase ToolCallRatio weight
- **Real-time Agents**: Increase LatencyRatio weight
- **Complex Task Agents**: Increase StepRatio weight

---

## Custom Metrics

AgentEval supports custom evaluation metrics by inheriting from `BaseMetric`:

```python
from agent_eval.metrics import BaseMetric
from agent_eval.models import AgentExecution, ExpectedResult, MetricScore

class ResponseLengthMetric(BaseMetric):
    """Evaluate if response length is appropriate"""
    
    def __init__(self, weight=0.1):
        super().__init__("ResponseLength", weight)
    
    def calculate(self, execution: AgentExecution, expected: ExpectedResult = None) -> MetricScore:
        output_len = len(execution.final_output or "")
        
        # Ideal length: 100-500 characters
        if 100 <= output_len <= 500:
            score = 1.0
        elif output_len < 100:
            score = output_len / 100
        else:
            score = max(0, 1 - (output_len - 500) / 500)
        
        return self._create_metric_score(
            score=score,
            details={"length": output_len, "ideal_range": "100-500"}
        )

# Use custom metric
evaluator = AgentEvaluator()
evaluator.metric_calculator.metrics["ResponseLength"] = ResponseLengthMetric(weight=0.1)
```
