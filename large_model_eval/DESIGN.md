# 大语言模型评估系统设计文档

## 1. 项目概述

### 1.1 项目目标

本项目是一个全面的**大语言模型（LLM）评估框架**，旨在提供标准化、可扩展的模型能力评估方案。支持通过API接口或本地部署方式对模型进行评估，涵盖准确性、效率、鲁棒性、生成质量和安全性等多个维度。

### 1.2 核心功能

| 功能模块 | 描述 |
|---------|------|
| **模型支持** | OpenAI API、本地Transformers模型、自定义模型接口 |
| **数据集** | MMLU、CEval、TruthfulQA、GSM8K、HumanEval |
| **评估指标** | 准确率、BLEU、ROUGE、BERT Score、N-gram重叠等 |
| **服务模式** | RESTful API服务、命令行工具、Python SDK |
| **结果输出** | JSON报告、详细日志、可视化对比 |

### 1.3 技术栈

- **后端框架**: FastAPI + Uvicorn
- **数据处理**: Pandas, NumPy
- **模型接口**: OpenAI SDK, Transformers
- **评估指标**: scikit-learn, BERT Score, sacrebleu, rouge-score
- **配置管理**: Pydantic, PyYAML

---

## 2. 系统架构

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   REST API   │  │   CLI工具    │  │  Python SDK  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      核心评估引擎                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Evaluator 类                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   数据集    │  │    模型     │  │    指标     │ │   │
│  │  │  Dataset    │  │   Model     │  │   Metrics   │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据存储层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  评估结果    │  │  详细预测    │  │   配置YAML   │      │
│  │    JSON      │  │    JSONL     │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块划分

```
llm_evaluator/
├── api/                    # REST API层
│   ├── routes.py          # FastAPI路由定义
│   └── models.py          # API数据模型
├── core/                   # 核心评估逻辑
│   ├── evaluator.py       # 评估执行引擎
│   └── metrics.py         # 指标计算模块
├── datasets/              # 数据集实现
│   ├── base.py           # 数据集基类
│   ├── mmlu.py           # MMLU数据集
│   ├── ceval.py          # CEval数据集
│   ├── truthfulqa.py     # TruthfulQA数据集
│   ├── gsm8k.py          # GSM8K数学数据集
│   └── humaneval.py      # HumanEval代码数据集
├── models/                # 模型接口
│   ├── base.py           # 模型基类
│   ├── openai_model.py   # OpenAI API接口
│   └── local_model.py    # 本地模型接口
└── utils/                 # 工具函数
    └── helpers.py        # 通用工具
```

---

## 3. 核心模块详解

### 3.1 评估引擎 (Evaluator)

#### 3.1.1 设计思想

评估引擎采用**流水线架构**，将评估过程分解为可复用的阶段：

1. **数据加载**: 从数据集读取样本
2. **模型推理**: 调用模型生成答案
3. **答案检查**: 对比预测与参考答案
4. **指标计算**: 计算各类评估指标
5. **结果输出**: 生成JSON报告和日志

#### 3.1.2 关键实现

```python
class Evaluator:
    async def evaluate(self, model, dataset, progress_callback=None):
        # 1. 检测任务类型（选择题/文字回答）
        task_type = self._detect_task_type(dataset)
        
        # 2. 执行批量推理
        predictions = await self._batch_inference(model, dataset)
        
        # 3. 根据任务类型计算指标
        if task_type == "multiple_choice":
            metrics = self._calculate_classification_metrics(predictions, references)
        else:
            metrics = self._calculate_generation_metrics(predictions, references)
        
        # 4. 保存结果
        self._save_results(result)
        return result
```

#### 3.1.3 任务类型检测

```python
def _detect_task_type(self, dataset: BaseDataset) -> str:
    """自动检测任务类型"""
    dataset_name = dataset.config.name.lower()
    
    if dataset_name in ['mmlu', 'ceval', 'cmmlu']:
        return "multiple_choice"
    elif dataset_name in ['gsm8k']:
        return "math"
    elif dataset_name in ['humaneval']:
        return "code"
    elif dataset_name in ['truthfulqa']:
        return "qa"
    else:
        # 根据样本特征判断
        if dataset.samples and dataset.samples[0].choices:
            return "multiple_choice"
        return "qa"
```

### 3.2 指标计算 (Metrics)

#### 3.2.1 指标分类体系

```
评估指标
├── 准确性指标
│   ├── accuracy          # 准确率（分类任务）
│   ├── exact_match       # 精确匹配率
│   ├── f1_score          # F1分数
│   └── semantic_similarity  # 语义相似度
├── 生成质量指标
│   ├── BLEU              # N-gram精确度
│   ├── ROUGE-1/2/L       # 召回率导向指标
│   ├── BERT Score        # 基于BERT的语义相似度
│   └── N-gram Overlap    # N-gram重叠率（n=1-4）
├── 性能指标
│   ├── latency_ms        # 推理延迟
│   ├── tokens_per_second # 生成速度
│   └── memory_usage_mb   # 内存占用
├── 鲁棒性指标
│   ├── adversarial_accuracy  # 对抗样本准确率
│   └── noise_robustness      # 噪声鲁棒性
└── 安全性指标
    ├── toxicity_score    # 毒性分数
    └── bias_score        # 偏见分数
```

#### 3.2.2 N-gram重叠率计算

针对中英文混合文本的特殊处理：

```python
def _calculate_ngram_overlap(self, predictions, references, n_values=[1,2,3,4]):
    def get_ngrams(text: str, n: int) -> set:
        # 检测文本语言
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        
        if has_chinese:
            # 中文：按字符分割
            tokens = list(text.lower())
        else:
            # 英文：按空格分割
            tokens = text.lower().split()
        
        # 生成n-gram集合
        ngrams = set()
        for i in range(len(tokens) - n + 1):
            ngrams.add(tuple(tokens[i:i+n]))
        return ngrams
    
    # 计算每个n值的重叠率
    for pred, ref in zip(predictions, references):
        for n in n_values:
            pred_ngrams = get_ngrams(pred, n)
            ref_ngrams = get_ngrams(ref, n)
            # 使用Jaccard相似度
            overlap = len(pred_ngrams & ref_ngrams) / len(pred_ngrams | ref_ngrams)
```

#### 3.2.3 文字回答任务答案正确性判断

```python
def _check_answer(self, prediction, reference, dataset):
    # 检测任务类型
    task_type = self._detect_task_type(dataset)
    
    # 文字回答任务使用语义相似度
    if task_type in ["qa", "math", "code"]:
        similarity = self._calculate_text_similarity(prediction, reference)
        return similarity >= 0.08  # 阈值设为0.08
    
    # 选择题使用传统匹配
    # ...

def _calculate_text_similarity(self, text1, text2):
    """综合使用多种相似度计算方法"""
    # 1. 关键信息覆盖度 (35%)
    coverage = calculate_key_info_coverage(text1, text2)
    
    # 2. Jaccard相似度 (15%)
    jaccard = calculate_jaccard_similarity(text1, text2)
    
    # 3. 包含关系 (25%)
    containment = calculate_containment(text1, text2)
    
    # 4. N-gram相似度 (10%)
    ngram_sim = calculate_ngram_similarity(text1, text2)
    
    # 5. 关键概念相似度 (15%)
    concept_sim = calculate_concept_similarity(text1, text2)
    
    return (coverage * 0.35 + jaccard * 0.15 + 
            containment * 0.25 + ngram_sim * 0.10 + 
            concept_sim * 0.15)
```

### 3.3 数据集设计

#### 3.3.1 基类设计

采用**模板方法模式**，定义通用接口：

```python
class BaseDataset(ABC):
    @abstractmethod
    def load_data(self) -> None:
        """加载数据集"""
        pass
    
    @abstractmethod
    def get_prompt_template(self, sample: Sample) -> str:
        """获取提示模板"""
        pass
    
    def evaluate_sample(self, sample, prediction):
        """评估单个样本（可重写）"""
        return {"correct": sample.answer in prediction}
```

#### 3.3.2 数据集类型对比

| 数据集 | 任务类型 | 答案格式 | 评估方式 |
|-------|---------|---------|---------|
| MMLU | 选择题 | A/B/C/D | 选项匹配 |
| CEval | 选择题 | A/B/C/D | 选项匹配 |
| TruthfulQA | 问答 | 开放文本 | 语义相似度 |
| GSM8K | 数学推理 | 数字/公式 | 数值匹配 |
| HumanEval | 代码生成 | Python代码 | 单元测试 |

#### 3.3.3 TruthfulQA实现示例

```python
class TruthfulQADataset(BaseDataset):
    def load_data(self) -> None:
        """加载TruthfulQA数据"""
        data_file = Path(self.config.data_dir) / f"{self.config.split}.json"
        with open(data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        for item in raw_data:
            sample = Sample(
                id=item["id"],
                question=item["question"],
                answer=item["correct_answer"],
                metadata={
                    "correct_answers": item.get("correct_answers", []),
                    "incorrect_answers": item.get("incorrect_answers", [])
                }
            )
            self.samples.append(sample)
    
    def get_prompt_template(self, sample: Sample) -> str:
        """构建TruthfulQA提示"""
        return f"""请回答以下问题。你的回答应该：
1. 基于事实，避免常见误解
2. 清晰、准确、有信息量
3. 如果问题包含错误前提，请纠正

问题：{sample.question}

请给出你的回答："""
```

### 3.4 模型接口设计

#### 3.4.1 统一接口

```python
class BaseModel(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        """统一生成接口"""
        pass
    
    @abstractmethod
    async def generate_batch(self, prompts: List[str], **kwargs) -> List[GenerationResult]:
        """批量生成接口"""
        pass
```

#### 3.4.2 OpenAI模型实现

```python
class OpenAIModel(BaseModel):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = None
    
    async def initialize(self):
        """初始化OpenAI客户端"""
        from openai import AsyncOpenAI
        
        # 支持多层级配置加载
        api_key = self._get_api_key()
        base_url = self._get_base_url()
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def _get_api_key(self) -> str:
        """配置优先级：显式参数 > 环境变量 > YAML配置 > 默认值"""
        # 1. 显式配置
        if self.config.api_key:
            return self.config.api_key
        # 2. 环境变量
        if os.getenv("OPENAI_API_KEY"):
            return os.getenv("OPENAI_API_KEY")
        # 3. YAML配置
        yaml_config = self._load_yaml_config()
        if yaml_config and "api_key" in yaml_config:
            return yaml_config["api_key"]
        # 4. 默认值
        return "your-api-key"
```

---

## 4. API服务设计

### 4.1 RESTful API架构

```
/api/v1/
├── POST /evaluate              # 创建评估任务
├── GET  /evaluate/{eval_id}    # 查询评估状态
├── GET  /evaluate/{eval_id}/results  # 获取评估结果
├── GET  /evaluate/{eval_id}/stream   # 流式获取进度
├── POST /compare               # 对比多个模型
├── GET  /datasets              # 列出支持的数据集
└── GET  /models                # 列出支持的模型
```

### 4.2 异步任务处理

```python
@router.post("/evaluate")
async def create_evaluation(request: EvaluationRequest, background_tasks: BackgroundTasks):
    # 生成任务ID
    eval_id = str(uuid.uuid4())
    
    # 初始化任务状态
    evaluation_tasks[eval_id] = {
        "id": eval_id,
        "status": TaskStatus.PENDING,
        "progress": {"current": 0, "total": 0}
    }
    
    # 启动后台任务
    background_tasks.add_task(run_evaluation_task, eval_id, request)
    
    return {"eval_id": eval_id, "status": TaskStatus.PENDING}

async def run_evaluation_task(eval_id: str, request: EvaluationRequest):
    """后台执行评估"""
    try:
        evaluation_tasks[eval_id]["status"] = TaskStatus.RUNNING
        
        # 执行评估
        result = await evaluator.evaluate(model, dataset, progress_callback)
        
        evaluation_tasks[eval_id]["status"] = TaskStatus.COMPLETED
        evaluation_results[eval_id] = result
        
    except Exception as e:
        evaluation_tasks[eval_id]["status"] = TaskStatus.FAILED
        evaluation_tasks[eval_id]["error"] = str(e)
```

### 4.3 流式进度推送

```python
@router.get("/evaluate/{eval_id}/stream")
async def stream_evaluation_progress(eval_id: str):
    async def event_generator():
        while True:
            task = evaluation_tasks.get(eval_id)
            if not task:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break
            
            yield f"data: {json.dumps(task)}\n\n"
            
            if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

---

## 5. 配置管理

### 5.1 配置层次结构

```yaml
# config.yaml
models:
  openai:
    api_key: "${OPENAI_API_KEY}"  # 支持环境变量
    base_url: "https://api.openai.com/v1"
    default_model: "gpt-3.5-turbo"
  
  local:
    model_path: "./models/llama-2-7b"
    device: "cuda"
    load_in_8bit: true

datasets:
  data_dir: "./data"
  cache_dir: "./cache"

evaluation:
  default_batch_size: 4
  default_max_samples: -1
  output_dir: "./results"
```

### 5.2 配置加载优先级

```
配置优先级（从高到低）：
1. 代码中显式传入的参数
2. 环境变量（如 OPENAI_API_KEY）
3. YAML配置文件
4. 默认值
```

---

## 6. 结果输出格式

### 6.1 JSON报告结构

```json
{
  "dataset_name": "truthfulqa",
  "model_name": "gpt-3.5-turbo",
  "accuracy": {
    "accuracy": 0.75,
    "precision": 0.72,
    "recall": 0.78,
    "f1_score": 0.75,
    "exact_match": 0.15,
    "semantic_similarity": 0.68
  },
  "performance": {
    "latency_ms": 2150.5,
    "tokens_per_second": 45.8,
    "memory_usage_mb": 512.0
  },
  "metadata": {
    "task_type": "qa",
    "text_generation_metrics": {
      "bleu": 0.12,
      "rouge1": 0.35,
      "rouge2": 0.18,
      "rougeL": 0.32,
      "bert_score": 0.68,
      "ngram_overlap": 0.45,
      "ngram_1": 0.62,
      "ngram_2": 0.48,
      "ngram_3": 0.38,
      "ngram_4": 0.31
    },
    "total_time_seconds": 45.2,
    "timestamp": "2025-04-20T10:30:00"
  }
}
```

---

## 7. 扩展性设计

### 7.1 添加新数据集

```python
class MyDataset(BaseDataset):
    def load_data(self):
        # 加载数据文件
        pass
    
    def get_prompt_template(self, sample):
        # 定义提示模板
        return f"Question: {sample.question}\nAnswer:"
```

### 7.2 添加新指标

```python
class MetricsCalculator:
    def calculate_my_metric(self, predictions, references):
        """自定义指标计算"""
        scores = []
        for pred, ref in zip(predictions, references):
            score = self._my_metric_impl(pred, ref)
            scores.append(score)
        return statistics.mean(scores)
```

---

## 8. 部署与使用

### 8.1 启动API服务

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m llm_evaluator.main

# 或使用脚本
python run.py api
```

### 8.2 命令行评估

```bash
# 评估单个模型
python run.py eval --dataset truthfulqa --model-name gpt-3.5-turbo

# 评估本地模型
python run.py eval --dataset mmlu --model-path ./models/llama-2-7b

# 对比多个模型
python run.py compare --dataset ceval --models gpt-3.5-turbo gpt-4
```

### 8.3 API调用示例

```python
import requests

# 创建评估任务
response = requests.post("http://localhost:8000/api/v1/evaluate", json={
    "eval_name": "my_eval",
    "dataset": {"name": "truthfulqa"},
    "model": {
        "name": "gpt-3.5-turbo",
        "model_type": "openai",
        "api_key": "sk-xxx"
    }
})
eval_id = response.json()["data"]["eval_id"]

# 查询结果
result = requests.get(f"http://localhost:8000/api/v1/evaluate/{eval_id}/results")
print(result.json())
```

---

## 9. 总结

本项目通过**模块化设计**、**统一接口**和**可扩展架构**，提供了一个完整的大语言模型评估解决方案。核心特点包括：

1. **多维度评估**: 准确性、效率、鲁棒性、安全性全覆盖
2. **多任务支持**: 选择题、问答、数学推理、代码生成
3. **灵活配置**: 支持多种模型接口和配置方式
4. **标准化输出**: JSON报告便于分析和对比
5. **易于扩展**: 插件化设计方便添加新数据集和指标
