# AgentEval 系统架构设计文档

[English Architecture Documentation](#agenteval-system-architecture)

---

## 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [核心模块详解](#核心模块详解)
4. [数据模型设计](#数据模型设计)
5. [设计模式与原则](#设计模式与原则)
6. [扩展点与接口](#扩展点与接口)
7. [性能与安全考虑](#性能与安全考虑)

---

## 系统概述

AgentEval 是一个全面的智能体评估系统，旨在为 AI Agent 提供科学、自动化的性能评估能力。系统支持多种评估指标、混合评分机制、多种存储后端，以及低侵入式的集成方式。

### 核心特性

- **零代码侵入**：通过装饰器实现无侵入集成
- **全面指标**：正确性、步骤率、工具调用率、解决率、延迟率
- **混合评分**：代码确定性检查 + LLM-as-Judge 评估
- **多存储后端**：JSON、CSV、SQLite、PostgreSQL
- **理想答案生成**：使用大模型生成预期执行路径
- **详细报告**：单条和批量评估报告生成

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AgentEval System                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Integration Layer (集成层)                                                   │
│  ├── decorators.py    - 零侵入装饰器 (@track_agent, @track_tool, @track_step) │
│  ├── tracker.py       - 上下文管理器追踪                                      │
│  └── recorders.py     - 传统录制接口                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Core Evaluation Layer (核心评估层)                                           │
│  ├── core.py               - AgentEvaluator (主协调器)                        │
│  ├── metrics.py            - 评估指标实现                                     │
│  ├── scorers.py            - 评分机制                                         │
│  └── text_similarity.py    - N-gram文本相似度计算 (jieba分词)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Data Layer (数据层)                                                          │
│  ├── models.py        - Pydantic 数据模型                                     │
│  ├── storages.py      - 存储后端实现                                          │
│  └── generators.py    - LLM 元数据生成                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Reporting Layer (报告层)                                                     │
│  └── reporting.py     - 报告生成器                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据流图

```
用户查询 → 智能体执行 → 执行追踪 → 数据存储 → 评估计算 → 报告生成
                ↓
            工具调用 → 工具追踪
                ↓
            步骤记录 → 步骤追踪
```

---

## 核心模块详解

### 1. models.py - 数据模型层

**设计思想**：

使用 Pydantic 进行严格的数据验证和序列化，确保数据一致性和类型安全。模型设计遵循"一次问答一条记录"的原则，完整记录智能体执行的各个方面。

**核心类设计**：

#### `AgentExecution` - 执行记录核心模型

```python
class AgentExecution(BaseModel):
    """Complete execution information of an agent - one Q&A as one record"""
    execution_id: str           # 唯一执行标识符
    query: str                  # 用户输入查询
    
    # 执行步骤摘要 - 格式化为"第一步执行...\n第二步执行..."
    steps_summary: str
    
    # 详细步骤信息
    steps_detail: List[StepDetail]
    
    # 工具调用信息
    tool_call_count: int
    tool_calls_detail: List[ToolCallDetail]
    
    # 执行统计
    step_count: int
    final_output: Optional[str]
    success: bool
    has_error: bool
    error_message: Optional[str]
    total_duration_ms: Optional[float]
    
    # 元数据
    metadata: Dict[str, Any]
    created_at: datetime
```

**设计亮点**：

1. **双格式存储**：同时提供 `steps_summary`（人类可读）和 `steps_detail`（机器可读）
2. **完整追踪**：记录每个步骤和工具调用的输入、输出、耗时、成功状态
3. **灵活元数据**：支持任意附加信息

#### `StepDetail` - 步骤详情模型

```python
class StepDetail(BaseModel):
    """Detailed information about an execution step"""
    step: int                   # 步骤序号 (1, 2, 3...)
    description: str            # 步骤描述
    input: Optional[Any]        # 步骤输入
    output: Optional[Any]       # 步骤输出
    time: Optional[float]       # 执行耗时（毫秒）
    success: bool               # 是否成功
    err_msg: Optional[str]      # 错误信息
    timestamp: datetime         # 时间戳
```

#### `ToolCallDetail` - 工具调用详情模型

```python
class ToolCallDetail(BaseModel):
    """Detailed information about a tool call"""
    name: str                   # 工具名称
    input: Dict[str, Any]       # 工具输入参数
    output: Optional[Any]       # 工具执行输出
    time: Optional[float]       # 执行耗时（毫秒）
    success: bool               # 是否成功
    err_msg: Optional[str]      # 错误信息
    timestamp: datetime         # 时间戳
```

#### `EvaluationResult` - 评估结果模型

```python
class EvaluationResult(BaseModel):
    """Complete evaluation result"""
    evaluation_id: str          # 评估唯一标识
    execution_id: str           # 关联的执行ID
    query: str                  # 原始查询
    overall_score: float        # 加权总分 (0.0 - 1.0)
    metric_scores: List[MetricScore]  # 各项指标得分
    agent_execution: AgentExecution   # 执行详情
    expected_result: Optional[ExpectedResult]  # 预期结果
    scorer_results: List[Dict[str, Any]]       # 评分器结果
    created_at: datetime
    metadata: Dict[str, Any]
```

---

### 2. metrics.py - 评估指标层

**设计思想**：

采用策略模式（Strategy Pattern），每个指标都是一个独立的策略类，便于扩展和维护。所有指标继承自 `BaseMetric`，实现统一的 `calculate` 接口。

**指标体系**：

#### 核心指标类

| 指标类 | 权重默认 | 评估内容 | 评分逻辑 |
|--------|----------|----------|----------|
| `Correctness` | 0.3 | 结果正确性 | **N-gram相似度**: 使用jieba分词，计算1-4 gram的加权相似度，综合考虑精确率、召回率和F1分数 |
| `StepRatio` | 0.2 | 步骤效率 | 实际步骤/最优步骤 ≤1(1.0) → ≤1.5(0.8) → ≤2.0(0.6) → ≤3.0(0.4) → >3.0(0.2) |
| `ToolCallRatio` | 0.2 | 工具调用效率 | 同步骤率逻辑 + 工具序列匹配度(F1分数) |
| `SolveRate` | 0.2 | 任务完成度 | 成功且有输出(1.0) → 成功无输出(0.7) → 失败(0.0) |
| `LatencyRatio` | 0.1 | 执行效率 | 实际耗时/预期耗时 ≤1(1.0) → ≤1.5(0.85) → ≤2.0(0.7) → ≤3.0(0.5) → ≤5.0(0.3) → >5.0(0.1) |

**设计亮点**：

1. **可配置权重**：通过 `MetricCalculator` 支持自定义指标权重
2. **渐进式评分**：使用阶梯式评分而非线性评分，更符合实际业务需求
3. **序列匹配**：`ToolCallRatio` 使用 F1 分数评估工具调用序列的准确性

#### `MetricCalculator` - 指标计算协调器

```python
class MetricCalculator:
    """Aggregates multiple metrics for evaluation"""
    
    def __init__(self, correctness_weight=0.3, step_ratio_weight=0.2, ...):
        self.metrics = {
            "Correctness": Correctness(weight=correctness_weight),
            "StepRatio": StepRatio(weight=step_ratio_weight),
            # ...
        }
    
    def calculate_all(self, execution, expected, enabled_metrics=None):
        """计算所有启用的指标并返回加权总分"""
```

---

### Metrics vs Scorers: 评估体系的双重维度

AgentEval 采用**双层评估架构**，`metrics.py` 和 `scorers.py` 分别承担不同层次的评估职责：

#### 核心区别

| 维度 | Metrics (metrics.py) | Scorers (scorers.py) |
|------|---------------------|---------------------|
| **评估层级** | 宏观性能指标 | 微观质量评分 |
| **评估对象** | 智能体整体执行表现 | 单次执行的具体质量 |
| **评估方式** | 多维度量化指标 | 确定性检查 + LLM主观评估 |
| **输出结果** | 结构化分数 (0-1) | 通过/失败 + 详细分析 |
| **使用场景** | 批量评估、性能监控 | 质量把关、详细诊断 |
| **调用时机** | 执行完成后综合计算 | 可随时对任意执行评分 |

#### 职责分工

**Metrics 层（性能评估）**：
- **Correctness**: 结果正确性（n-gram文本相似度）
- **StepRatio**: 步骤效率（实际步骤 vs 最优步骤）
- **ToolCallRatio**: 工具调用效率（数量 + 序列匹配）
- **SolveRate**: 任务解决率（成功状态 + 输出匹配）
- **LatencyRatio**: 执行延迟率（实际耗时 vs 预期耗时）

特点：
- 每个指标关注一个特定性能维度
- 通过 `MetricCalculator` 聚合为综合评分
- 适用于**批量评估**和**长期性能趋势分析**

**Scorers 层（质量评分）**：
- **CodeBasedScorer**: 确定性代码检查（工具序列、格式、精确匹配）
- **LLMJudgeScorer**: LLM主观质量评估（准确性、完整性、相关性、清晰度）
- **HybridScorer**: 混合评分（代码检查 + LLM评估）

特点：
- 灵活的评分策略组合
- 支持**实时质量监控**和**详细诊断分析**
- 可配置权重和检查规则

#### 协作关系

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentEval 评估流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  智能体执行 → Metrics层计算 → 综合性能评分                    │
│       ↓                                                      │
│  Scorers层评分 → 详细质量分析 → 通过/失败判定                │
│       ↓                                                      │
│  聚合结果 → 评估报告                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**典型使用场景**：

1. **日常监控**：使用 Metrics 进行批量评估，生成性能趋势报告
2. **质量把关**：使用 Scorers 对关键执行进行详细评分，确保质量标准
3. **问题诊断**：当 Metrics 发现异常时，使用 Scorers 进行根因分析
4. **A/B测试**：同时使用两者对比不同版本智能体的性能和质量

#### 选择指南

| 场景 | 推荐模块 | 原因 |
|------|---------|------|
| 批量评估1000+条记录 | Metrics | 计算高效，适合大规模统计 |
| CI/CD质量门禁 | Scorers | 精确判定通过/失败 |
| 性能优化分析 | Metrics | 多维度性能数据 |
| 内容质量审核 | Scorers | LLM主观评估更准确 |
| 长期趋势监控 | Metrics | 标准化指标便于对比 |
| 单次执行诊断 | Scorers | 详细分析具体问题 |
        scores = []
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric_name in enabled_metrics:
            metric = self.metrics[metric_name]
            score = metric.calculate(execution, expected)
            scores.append(score)
            weighted_sum += score.score * metric.weight
            total_weight += metric.weight
        
        overall_score = weighted_sum / total_weight
        return scores, overall_score
```

---

### 3. scorers.py - 评分机制层

**设计思想**：

支持多种评分机制，包括代码确定性检查和 LLM-as-Judge。采用组合模式支持混合评分，允许用户根据需求选择合适的评分策略。

#### `CodeBasedScorer` - 代码确定性评分

```python
class CodeBasedScorer(BaseScorer):
    """
    Deterministic code-based scorer for precise matching
    Fast and cost-effective for tool call paths, format checks, etc.
    """
    
    def __init__(
        self,
        check_tool_sequence: bool = True,    # 检查工具序列
        check_tool_count: bool = True,        # 检查工具数量
        check_output_format: bool = False,    # 检查输出格式
        check_exact_match: bool = False,      # 检查精确匹配
        custom_checks: Optional[List[Dict]] = None  # 自定义检查
    ):
```

**检查类型**：

1. **工具序列检查**：使用子序列匹配和 F1 分数评估
2. **工具数量检查**：比率阶梯评分
3. **输出格式检查**：JSON 格式、结构化内容、长度合理性
4. **精确匹配检查**：字符串完全匹配
5. **自定义检查**：支持正则、包含、等于等多种检查类型

#### `LLMJudgeScorer` - LLM 评估评分

```python
class LLMJudgeScorer(BaseScorer):
    """
    LLM-as-Judge scorer for quality assessment
    Uses a more powerful model to evaluate subjective content
    """
    
    async def score_async(self, execution, expected):
        """异步评分"""
        prompt = self._build_evaluation_prompt(execution, expected)
        response = await self._call_llm(prompt)
        return self._parse_response(response)
```

**评估维度**：

- 回答质量 (0-1 分)
- 相关性 (0-1 分)
- 完整性 (0-1 分)
- 准确性 (0-1 分)
- 总体评分 (0-1 分)

#### `HybridScorer` - 混合评分器

```python
class HybridScorer(BaseScorer):
    """Combines code-based and LLM-based scoring"""
    
    def __init__(
        self,
        code_scorer: CodeBasedScorer,
        llm_scorer: LLMJudgeScorer,
        code_weight: float = 0.4,
        llm_weight: float = 0.6
    ):
```

**设计亮点**：

- 结合确定性检查的速度和 LLM 评估的灵活性
- 可配置的权重分配
- 综合两种评分器的优势

---

### 4. text_similarity.py - 文本相似度计算层

**设计思想**：

使用 jieba 进行中文分词，结合 n-gram（n=1-4）匹配度计算文本相似度。相比传统的基于字符或简单词汇匹配的相似度计算，n-gram 能够更好地捕捉文本的语义结构和上下文信息。

#### `NGramSimilarity` - N-gram 相似度计算器

```python
class NGramSimilarity:
    """
    N-gram based text similarity calculator using jieba for Chinese tokenization
    Supports n-gram sizes from 1 to 4, with configurable weights for each n-gram level
    """
    
    def __init__(
        self,
        ngram_weights: Dict[int, float] = None,  # 例如: {1: 0.25, 2: 0.35, 3: 0.25, 4: 0.15}
        use_jieba: bool = True
    ):
```

**核心算法**：

1. **分词处理**：使用 jieba 对中文文本进行分词
   ```python
   text = "自然语言处理是人工智能的重要方向"
   tokens = ['自然语言', '处理', '是', '人工智能', '的', '重要', '方向']
   ```

2. **N-gram 生成**：生成 1-gram 到 4-gram
   ```python
   1-grams: [('自然语言',), ('处理',), ('是',), ...]
   2-grams: [('自然语言', '处理'), ('处理', '是'), ...]
   3-grams: [('自然语言', '处理', '是'), ...]
   4-grams: [('自然语言', '处理', '是', '人工智能'), ...]
   ```

3. **相似度计算**：综合精确率、召回率和 F1 分数
   ```python
   precision = intersection_count / len(ngrams1)
   recall = intersection_count / len(ngrams2)
   f1 = 2 * (precision * recall) / (precision + recall)
   similarity = 0.3 * precision + 0.3 * recall + 0.4 * f1
   ```

4. **加权融合**：根据配置的权重融合不同 n-gram 级别的相似度
   ```python
   final_score = Σ(similarity_n × weight_n) for n in [1, 2, 3, 4]
   ```

**默认权重配置（针对中文优化）**：

| N-gram | 权重 | 说明 |
|--------|------|------|
| 1-gram | 0.25 | 词汇级别匹配，捕捉关键词重叠 |
| 2-gram | 0.35 | 短语级别匹配，捕捉局部语义 |
| 3-gram | 0.25 | 短句级别匹配，捕捉上下文关系 |
| 4-gram | 0.15 | 句子级别匹配，捕捉整体结构 |

#### `SimilarityCalculators` - 预配置计算器

```python
class SimilarityCalculators:
    """Pre-configured similarity calculators for different scenarios"""
    
    @staticmethod
    def chinese() -> NGramSimilarity:
        """Optimized for Chinese text"""
        return NGramSimilarity(
            ngram_weights={1: 0.25, 2: 0.35, 3: 0.25, 4: 0.15},
            use_jieba=True
        )
    
    @staticmethod
    def strict() -> NGramSimilarity:
        """Strict matching emphasizing higher-order n-grams"""
        return NGramSimilarity(
            ngram_weights={1: 0.05, 2: 0.15, 3: 0.35, 4: 0.45},
            use_jieba=True
        )
    
    @staticmethod
    def lenient() -> NGramSimilarity:
        """Lenient matching emphasizing lower-order n-grams"""
        return NGramSimilarity(
            ngram_weights={1: 0.35, 2: 0.35, 3: 0.20, 4: 0.10},
            use_jieba=True
        )
```

**使用示例**：

```python
from agent_eval.text_similarity import calculate_text_similarity, SimilarityCalculators

# 便捷函数
score = calculate_text_similarity(
    actual="人工智能是计算机科学的一个分支",
    expected="人工智能属于计算机科学的分支领域"
)

# 使用预配置计算器
calculator = SimilarityCalculators.chinese()
score, details = calculator.calculate_similarity(text1, text2, return_details=True)

# 自定义权重
custom = NGramSimilarity(
    ngram_weights={1: 0.2, 2: 0.3, 3: 0.3, 4: 0.2},
    use_jieba=True
)
```

**设计亮点**：

1. **中文优化**：使用 jieba 分词，更适合中文语义理解
2. **多粒度匹配**：1-4 gram 综合评估，既考虑词汇重叠也考虑结构相似
3. **可配置性**：支持自定义 n-gram 权重，适应不同严格度要求
4. **详细反馈**：提供每个 n-gram 级别的详细得分，便于分析
5. **F1 综合**：综合考虑精确率和召回率，避免偏向性

---

### 5. generators.py - 元数据生成层

**设计思想**：

使用大语言模型（LLM）自动生成预期执行结果，解决手动编写测试用例预期结果的繁琐问题。通过模拟理想的执行过程，为评估提供基准参考。

#### `MetadataGenerator` - 元数据生成器

```python
class MetadataGenerator:
    """Generates expected results and metadata using LLM"""
    
    async def generate_expected_execution_async(
        self,
        query: str,
        available_tools: Optional[List[ToolInfo]] = None,
        context: Optional[str] = None
    ) -> GeneratedExpectedExecution:
        """Generate complete expected execution using LLM"""
```

**生成内容**：

1. **预期输出**：直接回答用户查询的完整结果
2. **执行步骤**：详细的执行步骤列表（3-7步）
3. **工具调用**：预测需要调用的工具及参数
4. **执行时间**：预估的总执行时长
5. **推理过程**：LLM的解题思路说明

**使用场景**：

- **自动创建测试用例**：为大量查询自动生成预期结果
- **基准参考生成**：为评估系统提供标准答案
- **训练数据生成**：生成模型微调所需的训练数据

**示例**：

```python
from agent_eval.generators import MetadataGenerator, ToolInfo
from agent_eval.models import LLMConfig

# 配置LLM
llm_config = LLMConfig(
    model="gpt-4",
    api_key="your-api-key"
)

# 创建生成器
generator = MetadataGenerator(llm_config)

# 定义可用工具
available_tools = [
    ToolInfo(
        name="weather_api",
        description="获取指定城市的天气信息",
        parameters={"city": {"type": "string"}}
    )
]

# 生成预期执行
result = await generator.generate_expected_execution_async(
    query="北京今天天气如何？",
    available_tools=available_tools
)

print(f"预期输出: {result.expected_output}")
print(f"执行步骤: {result.step_count}")
print(f"工具调用: {result.tool_call_count}")
```

**设计亮点**：

1. **无需真实工具调用**：LLM模拟执行过程，无需实际调用API
2. **结构化输出**：生成JSON格式的结构化数据，便于解析
3. **错误容错**：解析失败时返回fallback对象，不中断流程
4. **异步支持**：提供异步接口，支持高并发生成

---

### 6. storages.py - 存储层

**设计思想**：

采用抽象工厂模式，定义统一的 `BaseStorage` 接口，支持多种存储后端。用户可以根据需求选择合适的存储方式，无需修改业务代码。

#### 存储后端对比

| 存储类型 | 适用场景 | 优点 | 缺点 |
|----------|----------|------|------|
| `JSONStorage` | 开发测试、小规模数据 | 简单易用、可读性好 | 不适合大规模数据 |
| `CSVStorage` | 数据分析、表格处理 | 兼容性好、易于分析 | 不支持复杂嵌套结构 |
| `SQLiteStorage` | 单机应用、中等规模 | 轻量级、支持查询 | 不支持并发写入 |
| `PostgresStorage` | 生产环境、大规模数据 | 高性能、支持并发 | 需要额外配置 |

#### `BaseStorage` 抽象接口

```python
class BaseStorage(ABC):
    """Abstract base class for all storage backends"""
    
    @abstractmethod
    def save_execution(self, execution: AgentExecution) -> str:
        """Save an execution record"""
        pass
    
    @abstractmethod
    def save_evaluation(self, evaluation: EvaluationResult) -> str:
        """Save an evaluation result"""
        pass
    
    @abstractmethod
    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """Retrieve an execution by ID"""
        pass
    
    @abstractmethod
    def list_executions(self, limit: int = 100) -> List[AgentExecution]:
        """List recent executions"""
        pass
    
    @abstractmethod
    def save_expected_execution(self, expected: GeneratedExpectedExecution) -> str:
        """Save an expected execution (ideal answer)"""
        pass
```

#### 存储工厂函数

```python
def create_storage(config: StorageConfig) -> BaseStorage:
    """Factory function to create storage backend"""
    storage_map = {
        StorageType.JSON: JSONStorage,
        StorageType.CSV: CSVStorage,
        StorageType.SQLITE: SQLiteStorage,
        StorageType.POSTGRES: PostgresStorage,
    }
    
    storage_class = storage_map.get(config.storage_type)
    if not storage_class:
        raise ValueError(f"Unsupported storage type: {config.storage_type}")
    
    return storage_class(config)
```

---

### 6. decorators.py - 装饰器集成层

**设计思想**：

这是系统最重要的创新点之一。通过 Python 装饰器实现零代码侵入的集成方式，用户只需在现有函数上添加装饰器即可自动追踪执行。

#### 全局状态管理

```python
# Global storage for execution data
_execution_storage: Dict[str, AgentExecution] = {}
_active_executions: Dict[str, AgentExecution] = {}
_global_storage_backend: Optional[BaseStorage] = None
```

使用全局字典存储活跃的执行会话，支持嵌套调用和并发追踪。

#### `TrackedExecution` - 上下文管理器

```python
class TrackedExecution:
    """Context manager for tracking execution"""
    
    def __init__(self, query: str, metadata: Optional[Dict] = None, 
                 storage: Optional[BaseStorage] = None):
        self.query = query
        self.metadata = metadata or {}
        self.storage = storage or _global_storage_backend
        self.execution: Optional[AgentExecution] = None
    
    def __enter__(self):
        # 创建新的执行记录
        self.execution = AgentExecution(...)
        _active_executions[self.execution.execution_id] = self.execution
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 完成执行记录并保存
        self.execution.end_time = datetime.now()
        self.execution.success = exc_type is None
        if exc_val:
            self.execution.has_error = True
            self.execution.error_message = str(exc_val)
        
        # 保存到存储
        _execution_storage[self.execution.execution_id] = self.execution
        if self.storage:
            self.storage.save_execution(self.execution)
```

#### `@track_agent` - 智能体追踪装饰器

```python
def track_agent(query_arg: str = "query", storage: Optional[BaseStorage] = None):
    """
    Decorator to track agent execution
    
    Usage:
        @track_agent()
        def my_agent(query, **kwargs):
            # Agent logic
            return result
        
        result = my_agent("What is AI?")
        # Execution is automatically tracked and saved
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 从参数中提取 query
            query = kwargs.get(query_arg)
            if query is None and args:
                # 从位置参数中提取
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if query_arg in params:
                    idx = params.index(query_arg)
                    if idx < len(args):
                        query = args[idx]
            
            if query is None:
                query = "Unknown query"
            
            # 使用上下文管理器追踪执行
            with TrackedExecution(query, {"function": func.__name__}, 
                                  storage or _global_storage_backend) as exec:
                try:
                    result = func(*args, **kwargs)
                    exec.set_output(str(result) if result else "")
                    return result
                except Exception as e:
                    exec.execution.has_error = True
                    exec.execution.error_message = str(e)
                    raise
        return wrapper
    return decorator
```

#### `@track_tool` - 工具追踪装饰器

```python
def track_tool(tool_name: Optional[str] = None, storage: Optional[BaseStorage] = None):
    """
    Decorator to track tool execution
    
    Usage:
        @track_tool("search")
        def search_tool(query: str):
            # Search logic
            return results
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 查找活跃的执行会话
            active_exec = None
            if _active_executions:
                active_exec = list(_active_executions.values())[-1]
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # 记录工具调用
                if active_exec:
                    tool_input = _build_tool_input(args, kwargs, func)
                    active_exec.tool_calls_detail.append(ToolCallDetail(
                        name=tool_name or func.__name__,
                        input=tool_input,
                        output=result,
                        time=duration_ms,
                        success=True
                    ))
                    active_exec.tool_call_count = len(active_exec.tool_calls_detail)
                
                return result
            except Exception as e:
                # 记录失败的工具调用
                if active_exec:
                    active_exec.tool_calls_detail.append(ToolCallDetail(...))
                raise
        return wrapper
    return decorator
```

#### `@track_step` - 步骤追踪装饰器

```python
def track_step(step_name: Optional[str] = None, storage: Optional[BaseStorage] = None):
    """
    Decorator to track a specific step in execution
    
    Usage:
        @track_step("parse_query")
        def parse_query(query: str):
            # Parsing logic
            return parsed
    """
    # 类似 track_tool 的实现，但记录到 steps_detail
```

**设计亮点**：

1. **自动参数提取**：使用 `inspect` 模块自动从函数参数中提取 query
2. **嵌套支持**：通过 `_active_executions` 支持嵌套调用
3. **异常处理**：自动捕获异常并记录错误信息
4. **性能追踪**：自动计算执行耗时
5. **零侵入**：无需修改被装饰函数的内部逻辑

---

### 7. tracker.py - 追踪器层

**设计思想**：

提供多种追踪方式（上下文管理器、装饰器、手动追踪），满足不同场景的集成需求。

#### `ExecutionTracker` - 执行追踪器

```python
class ExecutionTracker:
    """
    Low-intrusive execution tracker for agent execution
    
    Usage:
        # Method 1: Context manager (recommended)
        with tracker.track("What is AI?") as exec:
            result = agent.run("What is AI?")
            exec.set_final_output(result)
        
        # Method 2: Decorator
        @tracker.wrap
        def my_agent(query):
            return agent.run(query)
        
        result, execution = my_agent("What is AI?")
        
        # Method 3: Manual tracking
        tracker.start("What is AI?")
        tracker.add_step(1, "Process query")
        tracker.add_tool_call("search", {"q": "AI"}, result, 100)
        tracker.set_final_output("AI is...")
        execution = tracker.finish()
    """
```

**三种使用模式**：

1. **上下文管理器模式**：最简洁的使用方式
2. **装饰器模式**：自动包装函数
3. **手动模式**：完全控制追踪过程

#### `SimpleTracker` - 简化追踪器

```python
class SimpleTracker:
    """
    Ultra-simple tracker with minimal API
    
    Usage:
        tracker = SimpleTracker()
        
        with tracker.start("What is AI?"):
            result = agent.run("What is AI?")
            tracker.record_result(result)
        
        execution = tracker.get_execution()
    """
```

---

### 8. recorders.py - 录制器层

**设计思想**：

传统的录制接口，提供更细粒度的控制。适合需要精确控制录制时机的场景。

#### `ExecutionRecord` - 执行记录

```python
class ExecutionRecord:
    """Represents a single execution record"""
    
    def __init__(self, execution_id=None, query="", metadata=None):
        self.execution_id = execution_id or str(uuid.uuid4())
        self.query = query
        self.steps_detail: List[StepDetail] = []
        self.tool_calls_detail: List[ToolCallDetail] = []
        self.steps_summary: str = ""
        self.final_output: Optional[str] = None
        self.success: bool = False
        # ...
    
    def add_step(self, description: str, step_input=None, step_output=None, 
                 metadata=None) -> StepDetail:
        """Add a new execution step"""
        self._step_counter += 1
        
        # 计算步骤耗时
        current_time = time.time()
        duration_ms = None
        if self._current_step_start:
            duration_ms = (current_time - self._current_step_start) * 1000
        self._current_step_start = current_time
        
        step = StepDetail(...)
        self.steps_detail.append(step)
        
        # 更新步骤摘要
        if self.steps_summary:
            self.steps_summary += f"\n第{self._step_counter}步执行{description}"
        else:
            self.steps_summary = f"第{self._step_counter}步执行{description}"
        
        return step
```

#### `ExecutionRecorder` - 执行录制器

```python
class ExecutionRecorder:
    """
    Records agent execution details automatically
    Can be used as a context manager or decorator
    """
    
    def __init__(self, storage=None, auto_save: bool = True, 
                 on_record_complete: Optional[Callable] = None):
        self.storage = storage
        self.auto_save = auto_save
        self.on_record_complete = on_record_complete
        self._current_record: Optional[ExecutionRecord] = None
        self._records: List[ExecutionRecord] = []
    
    @contextmanager
    def record(self, query: str, metadata: Optional[Dict] = None):
        """Context manager for recording execution"""
        self.start_recording(query, metadata)
        try:
            yield self._current_record
            self.end_recording(success=True)
        except Exception as e:
            self.end_recording(success=False, error_message=str(e))
            raise
```

---

### 9. core.py - 核心协调层

**设计思想**：

`AgentEvaluator` 是系统的主入口，负责协调各个模块的工作。采用外观模式（Facade Pattern）简化用户接口。

#### `AgentEvaluator` - 主评估器

```python
class AgentEvaluator:
    """
    Main evaluator class for assessing agent performance
    Integrates recording, metrics calculation, scoring, and storage
    """
    
    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or EvaluationConfig()
        
        # 初始化存储
        self.storage = self._init_storage()
        
        # 初始化录制器
        self.recorder = create_recorder(
            storage=self.storage if self.config.auto_record else None,
            auto_save=self.config.auto_record
        )
        
        # 初始化指标计算器
        self.metric_calculator = self._init_metric_calculator()
        
        # 初始化评分器
        self.scorers = self._init_scorers()
        
        # 初始化元数据生成器
        self.metadata_generator = None
        if self.config.llm_config:
            self.metadata_generator = MetadataGenerator(self.config.llm_config)
    
    def evaluate(
        self,
        execution: Optional[AgentExecution] = None,
        expected: Optional[ExpectedResult] = None,
        save_result: bool = True
    ) -> EvaluationResult:
        """
        Evaluate an agent execution
        
        Workflow:
        1. Get execution (from parameter or last recorded)
        2. Calculate metrics
        3. Apply scorers
        4. Create evaluation result
        5. Save to storage (if configured)
        """
        # 获取执行记录
        if execution is None:
            history = self.recorder.get_execution_history()
            if not history:
                raise ValueError("No execution provided and no recorded executions found")
            execution = history[-1]
        
        # 计算指标
        enabled_metrics = self._get_enabled_metrics()
        metric_scores, overall_score = self.metric_calculator.calculate_all(
            execution=execution,
            expected=expected,
            enabled_metrics=enabled_metrics
        )
        
        # 应用评分器
        scorer_results = []
        for scorer in self.scorers:
            scorer_result = scorer.score(execution, expected)
            scorer_results.append(scorer_result.to_dict())
        
        # 创建评估结果
        evaluation = EvaluationResult(
            evaluation_id=str(uuid.uuid4()),
            execution_id=execution.execution_id,
            query=execution.query,
            overall_score=overall_score,
            metric_scores=metric_scores,
            agent_execution=execution,
            expected_result=expected,
            scorer_results=scorer_results
        )
        
        # 保存结果
        if save_result and self.storage:
            self.storage.save_evaluation(evaluation)
        
        return evaluation
```

**核心方法**：

| 方法 | 功能 |
|------|------|
| `evaluate()` | 评估单个执行 |
| `evaluate_with_auto_expected()` | 使用自动生成的预期结果评估 |
| `batch_evaluate()` | 批量评估 |
| `get_evaluation_summary()` | 获取评估统计摘要 |
| `start_recording()` | 开始录制执行 |
| `end_recording()` | 结束录制执行 |
| `record_step()` | 记录执行步骤 |
| `record_tool_call()` | 记录工具调用 |

---

### 10. reporting.py - 报告层

**设计思想**：

支持生成多种类型的报告（单条评估、批量评估、对比报告），并支持多种输出格式。

#### `ReportGenerator` - 报告生成器

```python
class ReportGenerator:
    """Generates evaluation reports from execution and evaluation data"""
    
    def generate_single_report(
        self,
        execution: AgentExecution,
        evaluation: EvaluationResult,
        expected: Optional[ExpectedResult] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a report for a single evaluation"""
    
    def generate_batch_report(
        self,
        evaluations: List[EvaluationResult],
        executions: Optional[List[AgentExecution]] = None,
        expected_results: Optional[List[ExpectedResult]] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a report for batch evaluations"""
    
    def generate_comparison_report(
        self,
        query: str,
        expected_execution: GeneratedExpectedExecution,
        actual_execution: AgentExecution,
        evaluation: EvaluationResult,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a comparison report between expected and actual execution"""
```

**报告内容**：

1. **单条评估报告**：
   - 执行详情（查询、输出、步骤、工具调用）
   - 预期结果（如果有）
   - 评估结果（总分、各项指标得分）

2. **批量评估报告**：
   - 统计摘要（总数、平均分、分数分布）
   - 指标统计（各指标的平均、最小、最大）
   - 个体结果列表

3. **对比报告**：
   - 预期 vs 实际的详细对比
   - 差异分析（步骤数、工具调用数、耗时、输出相似度）
   - 评估得分

---

## 数据模型设计

### 数据关系图

```
AgentExecution (执行记录)
    ├── execution_id: 唯一标识
    ├── query: 用户查询
    ├── steps_summary: 步骤摘要
    ├── steps_detail: List[StepDetail]
    │       ├── step: 步骤序号
    │       ├── description: 描述
    │       ├── input/output: 输入输出
    │       ├── time: 耗时
    │       ├── success: 是否成功
    │       └── err_msg: 错误信息
    ├── tool_calls_detail: List[ToolCallDetail]
    │       ├── name: 工具名
    │       ├── input/output: 输入输出
    │       ├── time: 耗时
    │       ├── success: 是否成功
    │       └── err_msg: 错误信息
    ├── final_output: 最终输出
    ├── success/has_error: 状态
    └── total_duration_ms: 总耗时

EvaluationResult (评估结果)
    ├── evaluation_id: 唯一标识
    ├── execution_id: 关联执行ID
    ├── query: 查询
    ├── overall_score: 总分
    ├── metric_scores: List[MetricScore]
    │       ├── metric_name: 指标名
    │       ├── score: 得分
    │       ├── weight: 权重
    │       └── details: 详情
    ├── agent_execution: AgentExecution
    ├── expected_result: ExpectedResult
    └── scorer_results: 评分器结果
```

### 数据流转

```
用户查询
    ↓
智能体执行 → 被装饰器/追踪器拦截
    ↓
生成 AgentExecution
    ↓
存储到 Storage (JSON/CSV/SQLite/PostgreSQL)
    ↓
Evaluator.evaluate() 读取执行和预期结果
    ↓
MetricCalculator 计算各项指标
    ↓
Scorers 进行评分
    ↓
生成 EvaluationResult
    ↓
存储评估结果
    ↓
ReportGenerator 生成报告
```

---

## 设计模式与原则

### 1. 策略模式 (Strategy Pattern)

**应用**：指标计算 (`metrics.py`)

每个指标都是独立的策略类，实现统一的 `calculate` 接口：

```python
class BaseMetric(ABC):
    @abstractmethod
    def calculate(self, execution, expected) -> MetricScore:
        pass

class Correctness(BaseMetric): ...
class StepRatio(BaseMetric): ...
class ToolCallRatio(BaseMetric): ...
```

**优点**：
- 易于添加新指标
- 指标之间解耦
- 可独立测试

### 2. 抽象工厂模式 (Abstract Factory)

**应用**：存储后端 (`storages.py`)

```python
class BaseStorage(ABC):
    @abstractmethod
    def save_execution(self, execution): pass

def create_storage(config: StorageConfig) -> BaseStorage:
    storage_map = {
        StorageType.JSON: JSONStorage,
        StorageType.CSV: CSVStorage,
        ...
    }
    return storage_map[config.storage_type](config)
```

**优点**：
- 支持多种存储后端
- 切换存储无需修改业务代码
- 易于扩展新存储类型

### 3. 外观模式 (Facade Pattern)

**应用**：`AgentEvaluator` (`core.py`)

```python
class AgentEvaluator:
    """Simplified interface to the entire subsystem"""
    
    def __init__(self, config):
        self.storage = self._init_storage()
        self.recorder = create_recorder(...)
        self.metric_calculator = self._init_metric_calculator()
        self.scorers = self._init_scorers()
    
    def evaluate(self, execution, expected):
        # 协调各个子系统的工作
        ...
```

**优点**：
- 简化用户接口
- 隐藏内部复杂性
- 统一入口点

### 4. 装饰器模式 (Decorator Pattern)

**应用**：追踪装饰器 (`decorators.py`)

```python
def track_agent(query_arg="query"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with TrackedExecution(...) as exec:
                result = func(*args, **kwargs)
                exec.set_output(result)
                return result
        return wrapper
    return decorator
```

**优点**：
- 零代码侵入
- 可组合使用
- 透明增强功能

### 5. 上下文管理器模式 (Context Manager)

**应用**：`TrackedExecution`, `ExecutionTracker`

```python
class TrackedExecution:
    def __enter__(self):
        self.execution = AgentExecution(...)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.execution.end_time = datetime.now()
        self.storage.save_execution(self.execution)
```

**优点**：
- 自动资源管理
- 异常安全
- 代码简洁

### 6. 单一职责原则 (SRP)

每个模块只负责一个职责：

- `models.py`：数据定义
- `metrics.py`：指标计算
- `scorers.py`：评分机制
- `storages.py`：数据存储
- `generators.py`：元数据生成
- `decorators.py`：集成装饰器

### 7. 开闭原则 (OCP)

对扩展开放，对修改关闭：

- 添加新指标：继承 `BaseMetric`
- 添加新存储：继承 `BaseStorage`
- 添加新评分器：继承 `BaseScorer`

---

## 扩展点与接口

### 1. 自定义指标

```python
from agent_eval.metrics import BaseMetric

class MyCustomMetric(BaseMetric):
    def __init__(self, weight=0.2):
        super().__init__("MyCustom", weight)
    
    def calculate(self, execution, expected):
        # 自定义计算逻辑
        score = ...
        return self._create_metric_score(score, details={...})
```

### 2. 自定义存储

```python
from agent_eval.storages import BaseStorage

class MyStorage(BaseStorage):
    def save_execution(self, execution: AgentExecution) -> str:
        # 自定义存储逻辑
        pass
    
    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        # 自定义读取逻辑
        pass
```

### 3. 自定义评分器

```python
from agent_eval.scorers import BaseScorer

class MyScorer(BaseScorer):
    def score(self, execution, expected):
        # 自定义评分逻辑
        return ScorerResult(
            scorer_name="MyScorer",
            score=0.9,
            passed=True,
            details={...}
        )
```

### 4. 自定义报告格式

```python
from agent_eval.reporting import ReportGenerator

class MyReportGenerator(ReportGenerator):
    def generate_single_report(self, execution, evaluation, expected, output_path):
        # 自定义报告生成逻辑
        report = {...}
        return report
```

---

## 性能与安全考虑

### 性能优化

1. **异步支持**：LLM 调用支持异步 (`generate_expected_execution_async`)
2. **批量操作**：支持批量评估 (`batch_evaluate`)
3. **延迟加载**：存储后端按需加载数据
4. **内存管理**：使用生成器处理大量数据

### 安全考虑

1. **API 密钥管理**：LLM 配置中的 API 密钥不应硬编码
2. **数据验证**：Pydantic 模型自动验证数据类型
3. **错误处理**：完善的异常捕获和处理机制
4. **敏感信息**：避免在日志中记录敏感信息

### 最佳实践

1. **配置管理**：使用 `EvaluationConfig` 集中管理配置
2. **日志记录**：关键操作添加日志
3. **单元测试**：每个模块都有对应的测试文件
4. **文档完善**：详细的 docstring 和使用示例

---

## 完整使用示例

### 示例1：快速开始（装饰器方式）

```python
from agent_eval import track_agent, track_tool, configure_storage
from agent_eval.models import StorageConfig, StorageType

# 配置存储
configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="evaluations.json"
))

# 追踪工具
@track_tool(tool_name="search")
def search_api(query: str):
    """模拟搜索工具"""
    return f"搜索结果: {query}"

# 追踪智能体
@track_agent(query_arg="query")
def my_agent(query: str):
    """简单的智能体"""
    # 调用工具
    result = search_api(query)
    
    # 生成回答
    response = f"基于搜索结果: {result}"
    return response

# 使用
result = my_agent("什么是人工智能？")
print(result)
```

### 示例2：完整评估流程

```python
from agent_eval import AgentEvaluator, EvaluationConfig
from agent_eval.models import StorageType, LLMConfig

# 配置评估器
config = EvaluationConfig(
    storage_type=StorageType.SQLITE,
    file_path="evaluations.db",
    llm_config=LLMConfig(
        api_key="your-api-key",
        model="gpt-4"
    ),
    auto_record=True
)

evaluator = AgentEvaluator(config)

# 方式1：使用装饰器自动记录
@evaluator.record(query_arg="query")
def my_agent(query: str):
    # 智能体逻辑
    steps = ["理解查询", "检索信息", "生成回答"]
    result = f"回答: {query}"
    return result

# 执行
result = my_agent("什么是机器学习？")

# 获取最近的执行并评估
from agent_eval import get_last_execution
execution = get_last_execution()

# 生成预期结果
expected = evaluator.generate_expected_result(
    query="什么是机器学习？",
    available_tools=["search", "calculator"]
)

# 评估
evaluation = evaluator.evaluate(execution, expected)
print(f"总分: {evaluation.overall_score:.2%}")
print(f"正确性: {evaluation.metric_scores[0].score:.2%}")
```

### 示例3：批量评估

```python
from agent_eval import AgentEvaluator

# 准备测试用例
test_cases = [
    {"query": "北京天气", "expected_output": "今天北京晴朗"},
    {"query": "计算1+1", "expected_output": "2"},
    {"query": "翻译hello", "expected_output": "你好"},
]

# 批量执行和评估
evaluator = AgentEvaluator()
results = []

for case in test_cases:
    # 执行
    result = my_agent(case["query"])
    
    # 获取执行记录
    execution = get_last_execution()
    
    # 创建预期结果
    from agent_eval.models import ExpectedResult
    expected = ExpectedResult(
        expected_output=case["expected_output"],
        expected_steps=["理解", "处理", "回答"],
        expected_tool_calls=[],
        expected_tool_count=0
    )
    
    # 评估
    evaluation = evaluator.evaluate(execution, expected)
    results.append(evaluation)

# 生成批量报告
from agent_eval.reporting import ReportGenerator
report_gen = ReportGenerator()
report = report_gen.generate_batch_report(results)

print(f"平均得分: {report['summary']['average_score']:.2%}")
print(f"最高得分: {report['summary']['max_score']:.2%}")
print(f"最低得分: {report['summary']['min_score']:.2%}")
```

### 示例4：使用PostgreSQL存储（生产环境）

```python
from agent_eval import configure_storage, StorageConfig, StorageType

# 配置PostgreSQL存储
configure_storage(StorageConfig(
    storage_type=StorageType.POSTGRES,
    connection_string="postgresql://user:password@localhost:5432/agent_eval"
))

# 或使用独立参数
configure_storage(StorageConfig(
    storage_type=StorageType.POSTGRES,
    host="localhost",
    port=5432,
    database="agent_eval",
    user="username",
    password="password"
))

# 后续使用与JSON/SQLite相同
@track_agent()
def production_agent(query: str):
    return process_query(query)
```

### 示例5：自定义指标和评分器

```python
from agent_eval.metrics import BaseMetric, MetricScore
from agent_eval.scorers import BaseScorer, ScorerResult

# 自定义指标
class ResponseLengthMetric(BaseMetric):
    """评估回答长度是否适中"""
    
    def __init__(self, weight=0.1):
        super().__init__("ResponseLength", weight)
    
    def calculate(self, execution, expected):
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

# 自定义评分器
class KeywordScorer(BaseScorer):
    """检查回答中是否包含关键词"""
    
    def __init__(self, required_keywords: list):
        super().__init__("KeywordScorer")
        self.required_keywords = required_keywords
    
    def score(self, execution, expected):
        output = execution.final_output or ""
        found_keywords = [kw for kw in self.required_keywords if kw in output]
        
        score = len(found_keywords) / len(self.required_keywords)
        
        return ScorerResult(
            scorer_name=self.name,
            score=score,
            passed=score >= 0.8,
            details={
                "found": found_keywords,
                "required": self.required_keywords
            }
        )

# 使用自定义组件
evaluator = AgentEvaluator()
evaluator.metric_calculator.metrics["ResponseLength"] = ResponseLengthMetric(weight=0.1)
evaluator.scorers.append(KeywordScorer(["AI", "人工智能"]))
```

---

## 总结

AgentEval 系统采用模块化、可扩展的架构设计，通过多种设计模式实现了：

1. **低侵入集成**：装饰器和上下文管理器实现零代码侵入
2. **灵活配置**：支持多种指标、评分器、存储后端
3. **完整追踪**：详细记录执行步骤、工具调用、错误信息
4. **智能评估**：代码检查 + LLM 评估的混合评分机制
5. **文本相似度**：基于 jieba + n-gram 的智能文本匹配
6. **丰富报告**：单条、批量、对比多种报告类型

系统设计充分考虑了可扩展性、可维护性和易用性，可以方便地集成到各种智能体框架中。

---

# AgentEval System Architecture

[中文架构文档](#agenteval-系统架构设计文档)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Core Modules](#core-modules)
4. [Data Model Design](#data-model-design)
5. [Design Patterns](#design-patterns)
6. [Extension Points](#extension-points)
7. [Performance & Security](#performance--security)

---

## System Overview

AgentEval is a comprehensive agent evaluation system designed to provide scientific and automated performance evaluation capabilities for AI Agents. The system supports multiple evaluation metrics, hybrid scoring mechanisms, multiple storage backends, and low-intrusive integration methods.

### Core Features

- **Zero Code Intrusion**: Non-intrusive integration through decorators
- **Comprehensive Metrics**: Correctness, Step Ratio, Tool Call Ratio, Solve Rate, Latency Ratio
- **Hybrid Scoring**: Code deterministic checks + LLM-as-Judge evaluation
- **Multiple Storage Backends**: JSON, CSV, SQLite, PostgreSQL
- **Ideal Answer Generation**: Use LLM to generate expected execution paths
- **Detailed Reports**: Single and batch evaluation report generation

---

## Architecture Design

### Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AgentEval System                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Integration Layer                                                            │
│  ├── decorators.py    - Zero-intrusion decorators (@track_agent, etc.)       │
│  ├── tracker.py       - Context manager tracking                              │
│  └── recorders.py     - Traditional recording interface                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Core Evaluation Layer                                                        │
│  ├── core.py               - AgentEvaluator (main orchestrator)              │
│  ├── metrics.py            - Evaluation metrics implementation               │
│  ├── scorers.py            - Scoring mechanisms                               │
│  └── text_similarity.py    - N-gram text similarity (jieba tokenization)     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Data Layer                                                                   │
│  ├── models.py        - Pydantic data models                                  │
│  ├── storages.py      - Storage backend implementations                       │
│  └── generators.py    - LLM metadata generation                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Reporting Layer                                                              │
│  └── reporting.py     - Report generator                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Query → Agent Execution → Execution Tracking → Data Storage → Evaluation → Report Generation
                ↓
            Tool Calls → Tool Tracking
                ↓
            Step Recording → Step Tracking
```

---

## Core Modules

### 1. models.py - Data Model Layer

**Design Philosophy**:

Uses Pydantic for strict data validation and serialization, ensuring data consistency and type safety. Model design follows the principle of "one Q&A per record", completely recording all aspects of agent execution.

**Core Classes**:

#### `AgentExecution` - Core Execution Record Model

```python
class AgentExecution(BaseModel):
    """Complete execution information of an agent - one Q&A as one record"""
    execution_id: str           # Unique execution identifier
    query: str                  # User input query
    
    # Execution step summary - formatted as "Step 1: ...\nStep 2: ..."
    steps_summary: str
    
    # Detailed step information
    steps_detail: List[StepDetail]
    
    # Tool call information
    tool_call_count: int
    tool_calls_detail: List[ToolCallDetail]
    
    # Execution statistics
    step_count: int
    final_output: Optional[str]
    success: bool
    has_error: bool
    error_message: Optional[str]
    total_duration_ms: Optional[float]
    
    # Metadata
    metadata: Dict[str, Any]
    created_at: datetime
```

**Design Highlights**:

1. **Dual Format Storage**: Provides both `steps_summary` (human-readable) and `steps_detail` (machine-readable)
2. **Complete Tracking**: Records input, output, duration, success status for each step and tool call
3. **Flexible Metadata**: Supports arbitrary additional information

### 2. metrics.py - Evaluation Metrics Layer

**Design Philosophy**:

Adopts the Strategy Pattern, where each metric is an independent strategy class for easy extension and maintenance. All metrics inherit from `BaseMetric` and implement a unified `calculate` interface.

**Core Metrics**:

| Metric Class | Default Weight | Evaluation Content | Scoring Logic |
|--------------|----------------|-------------------|---------------|
| `Correctness` | 0.3 | Result correctness | **N-gram similarity**: Uses jieba tokenization, calculates weighted similarity of 1-4 grams, considering precision, recall, and F1 score |
| `StepRatio` | 0.2 | Step efficiency | Actual steps/optimal steps ≤1(1.0) → ≤1.5(0.8) → ≤2.0(0.6) → ≤3.0(0.4) → >3.0(0.2) |
| `ToolCallRatio` | 0.2 | Tool call efficiency | Same as step ratio + tool sequence matching (F1 score) |
| `SolveRate` | 0.2 | Task completion | Success with output(1.0) → Success without output(0.7) → Failure(0.0) |
| `LatencyRatio` | 0.1 | Execution efficiency | Actual/expected duration ≤1(1.0) → ≤1.5(0.85) → ≤2.0(0.7) → ≤3.0(0.5) → ≤5.0(0.3) → >5.0(0.1) |

### 3. scorers.py - Scoring Mechanism Layer

**Design Philosophy**:

Supports multiple scoring mechanisms, including code deterministic checks and LLM-as-Judge. Uses composition pattern to support hybrid scoring, allowing users to choose appropriate scoring strategies based on needs.

**Scorer Types**:

- **CodeBasedScorer**: Deterministic code-based checks (tool sequences, format, exact match)
- **LLMJudgeScorer**: LLM subjective quality assessment (accuracy, completeness, relevance, clarity)
- **HybridScorer**: Combines code-based and LLM-based scoring

### 4. decorators.py - Decorator Integration Layer

**Design Philosophy**:

One of the system's most important innovations. Achieves zero-code-intrusion integration through Python decorators. Users only need to add decorators to existing functions to automatically track execution.

**Key Features**:

- Uses ContextVars for thread-safe tracking
- Supports concurrent and nested executions
- Each execution has its own isolated context
- Automatic parameter extraction using `inspect` module
- Automatic performance tracking and error handling

### 5. core.py - Core Orchestration Layer

**Design Philosophy**:

`AgentEvaluator` is the system's main entry point, responsible for coordinating the work of various modules. Adopts the Facade Pattern to simplify user interfaces.

**Core Methods**:

| Method | Function |
|--------|----------|
| `evaluate()` | Evaluate a single execution |
| `evaluate_with_auto_expected()` | Evaluate using auto-generated expected results |
| `batch_evaluate()` | Batch evaluation |
| `get_evaluation_summary()` | Get evaluation statistics summary |
| `start_recording()` | Start recording execution |
| `end_recording()` | End recording execution |
| `record_step()` | Record execution step |
| `record_tool_call()` | Record tool call |

---

## Data Model Design

### Data Relationships

```
AgentExecution (Execution Record)
    ├── execution_id: Unique identifier
    ├── query: User query
    ├── steps_summary: Step summary
    ├── steps_detail: List[StepDetail]
    │       ├── step: Step number
    │       ├── description: Description
    │       ├── input/output: Input/Output
    │       ├── time: Duration
    │       ├── success: Success status
    │       └── err_msg: Error message
    ├── tool_calls_detail: List[ToolCallDetail]
    │       ├── name: Tool name
    │       ├── input/output: Input/Output
    │       ├── time: Duration
    │       ├── success: Success status
    │       └── err_msg: Error message
    ├── final_output: Final output
    ├── success/has_error: Status
    └── total_duration_ms: Total duration

EvaluationResult (Evaluation Result)
    ├── evaluation_id: Unique identifier
    ├── execution_id: Associated execution ID
    ├── query: Query
    ├── overall_score: Total score
    ├── metric_scores: List[MetricScore]
    │       ├── metric_name: Metric name
    │       ├── score: Score
    │       ├── weight: Weight
    │       └── details: Details
    ├── agent_execution: AgentExecution
    ├── expected_result: ExpectedResult
    └── scorer_results: Scorer results
```

---

## Design Patterns

### 1. Strategy Pattern

**Application**: Metric calculation (`metrics.py`)

Each metric is an independent strategy class implementing a unified `calculate` interface.

### 2. Abstract Factory Pattern

**Application**: Storage backends (`storages.py`)

Supports multiple storage backends through abstract `BaseStorage` interface.

### 3. Facade Pattern

**Application**: `AgentEvaluator` (`core.py`)

Simplified interface to the entire subsystem.

### 4. Decorator Pattern

**Application**: Tracking decorators (`decorators.py`)

Zero-code-intrusion through function decoration.

### 5. Context Manager Pattern

**Application**: `TrackedExecution`, `ExecutionTracker`

Automatic resource management and exception safety.

---

## Extension Points

### Custom Metrics

```python
from agent_eval.metrics import BaseMetric

class MyCustomMetric(BaseMetric):
    def __init__(self, weight=0.2):
        super().__init__("MyCustom", weight)
    
    def calculate(self, execution, expected):
        # Custom calculation logic
        score = ...
        return self._create_metric_score(score, details={...})
```

### Custom Storage

```python
from agent_eval.storages import BaseStorage

class MyStorage(BaseStorage):
    def save_execution(self, execution: AgentExecution) -> str:
        # Custom storage logic
        pass
    
    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        # Custom retrieval logic
        pass
```

### Custom Scorer

```python
from agent_eval.scorers import BaseScorer

class MyScorer(BaseScorer):
    def score(self, execution, expected):
        # Custom scoring logic
        return ScorerResult(
            scorer_name="MyScorer",
            score=0.9,
            passed=True,
            details={...}
        )
```

---

## Performance & Security

### Performance Optimization

1. **Async Support**: LLM calls support async (`generate_expected_execution_async`)
2. **Batch Operations**: Supports batch evaluation (`batch_evaluate`)
3. **Lazy Loading**: Storage backends load data on demand
4. **Memory Management**: Uses generators for large data processing
5. **ContextVars**: Thread-safe concurrent execution tracking

### Security Considerations

1. **API Key Management**: API keys in LLM config should not be hardcoded
2. **Data Validation**: Pydantic models automatically validate data types
3. **Error Handling**: Comprehensive exception capture and handling
4. **Sensitive Information**: Avoid logging sensitive information

---

## Summary

The AgentEval system adopts a modular, extensible architecture design, achieving through multiple design patterns:

1. **Low Intrusion Integration**: Decorators and context managers for zero-code-intrusion
2. **Flexible Configuration**: Support for multiple metrics, scorers, storage backends
3. **Complete Tracking**: Detailed recording of execution steps, tool calls, error information
4. **Intelligent Evaluation**: Code checks + LLM evaluation hybrid scoring mechanism
5. **Text Similarity**: jieba + n-gram based intelligent text matching
6. **Rich Reports**: Single, batch, comparison multiple report types

The system design fully considers scalability, maintainability, and usability, and can be easily integrated into various agent frameworks.
