# 大语言模型评估系统 (LLM Evaluator)

一个全面的大语言模型评估框架，支持多种数据集、模型接口和评估指标。

## 特性

- **全面的评估指标体系**
  - 基础性能指标：准确性、效率、鲁棒性
  - 高级能力指标：生成质量、多样性、连贯性
  - 伦理安全指标：偏见、毒性、隐私保护

- **多数据集支持**
  - MMLU (Massive Multi-task Language Understanding)
  - C-Eval (中文大模型评测数据集)
  - 易于扩展自定义数据集

- **灵活的模型接口**
  - OpenAI API (GPT-3.5, GPT-4)
  - 本地 HuggingFace Transformers 模型
  - 支持自定义模型接口

- **RESTful API**
  - 异步评估任务管理
  - 实时进度监控
  - 结果查询与比较

## 项目结构

```
llm_evaluator/
├── core/                 # 核心评估模块
│   ├── metrics.py       # 评估指标计算
│   └── evaluator.py     # 评估执行引擎
├── datasets/            # 数据集管理
│   ├── base.py         # 数据集基类
│   ├── mmlu.py         # MMLU数据集
│   └── ceval.py        # C-Eval数据集
├── models/              # 模型接口
│   ├── base.py         # 模型基类
│   ├── openai_model.py # OpenAI API接口
│   └── local_model.py  # 本地模型接口
├── api/                 # FastAPI接口
│   ├── models.py       # Pydantic数据模型
│   └── routes.py       # API路由
├── utils/               # 工具函数
│   └── helpers.py      # 辅助功能
└── main.py             # FastAPI应用入口

data/                   # 示例数据集
├── sample_mmlu.json
└── sample_ceval.json
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# OpenAI API密钥（如使用OpenAI模型）
export OPENAI_API_KEY="your-api-key"

# 或创建 .env 文件
echo "OPENAI_API_KEY=your-api-key" > .env
```

### 3. 启动API服务

```bash
python run.py api
# 或使用 uvicorn
uvicorn llm_evaluator.main:app --reload
```

API文档地址: http://localhost:8000/docs

### 4. 执行评估任务

```bash
# 使用OpenAI模型评估
python run.py eval --model-type openai --model-name gpt-3.5-turbo --dataset mmlu

# 使用本地模型评估
python run.py eval --model-type local --model-name gpt2 --dataset ceval
```

## API使用示例

### 创建评估任务

```bash
curl -X POST "http://localhost:8000/api/v1/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "eval_name": "GPT-3.5 MMLU评估",
    "description": "使用MMLU数据集评估GPT-3.5",
    "model_config": {
      "model_type": "openai",
      "model_name": "gpt-3.5-turbo",
      "api_key": "your-api-key",
      "temperature": 0.0,
      "max_tokens": 512
    },
    "dataset_config": {
      "dataset_type": "mmlu",
      "max_samples": 100
    },
    "batch_size": 8
  }'
```

### 查询任务状态

```bash
curl "http://localhost:8000/api/v1/evaluate/{eval_id}/status"
```

### 获取评估结果

```bash
curl "http://localhost:8000/api/v1/evaluate/{eval_id}/result"
```

## 评估指标体系

### 基础性能指标

| 指标 | 描述 | 计算方法 |
|------|------|----------|
| Accuracy | 准确率 | 正确预测数 / 总样本数 |
| Exact Match | 精确匹配率 | 完全匹配数 / 总样本数 |
| F1 Score | F1分数 | 2 * 精确率 * 召回率 / (精确率 + 召回率) |
| Latency | 延迟 | 平均推理时间（毫秒） |
| Throughput | 吞吐量 | Tokens/秒 |

### 高级能力指标

| 指标 | 描述 | 计算方法 |
|------|------|----------|
| Diversity | 多样性 | Distinct n-gram比例 |
| ROUGE | 召回率导向的评估 | ROUGE-1/2/L |
| BLEU | 双语评估替补 | BLEU分数 |
| Semantic Similarity | 语义相似度 | BERT Score |

### 伦理安全指标

| 指标 | 描述 |
|------|------|
| Toxicity Score | 毒性分数 |
| Bias Score | 偏见分数 |
| Refusal Rate | 不当请求拒绝率 |
| Privacy Leakage | 隐私泄露风险 |

## 自定义扩展

### 添加自定义数据集

```python
from llm_evaluator.datasets.base import BaseDataset, DatasetConfig, Sample

class MyDataset(BaseDataset):
    def load_data(self):
        # 实现数据加载逻辑
        pass
    
    def get_prompt_template(self, sample: Sample) -> str:
        # 实现提示模板
        pass
```

### 添加自定义模型

```python
from llm_evaluator.models.base import BaseModel, ModelConfig, GenerationResult

class MyModel(BaseModel):
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        # 实现生成逻辑
        pass
```

## 配置说明

编辑 `config.yaml` 文件自定义配置：

```yaml
# 应用配置
app:
  host: "0.0.0.0"
  port: 8000

# 模型配置
models:
  openai:
    default_model: "gpt-3.5-turbo"
    timeout: 30
  local:
    device: "auto"

# 评估配置
evaluation:
  default:
    batch_size: 8
    max_samples: -1
```

## 开发指南

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black llm_evaluator/
isort llm_evaluator/
```

## 许可证

MIT License
