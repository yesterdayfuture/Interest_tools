"""
API数据模型定义模块

使用Pydantic定义API的请求和响应数据模型
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# ==================== 枚举类型 ====================

class ModelType(str, Enum):
    """模型类型枚举"""
    OPENAI = "openai"
    LOCAL = "local"


class DatasetType(str, Enum):
    """数据集类型枚举"""
    MMLU = "mmlu"              # 多学科选择题
    CEVAL = "ceval"            # 中文评估选择题
    CMMLU = "cmmlu"            # 中文多学科选择题
    TRUTHFULQA = "truthfulqa"  # 真实性问答（文字回答）
    GSM8K = "gsm8k"            # 数学推理（文字回答）
    HUMANEVAL = "humaneval"    # 代码生成（文字回答）


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================== 请求模型 ====================

class ModelConfigRequest(BaseModel):
    """模型配置请求模型"""
    model_type: ModelType = Field(..., description="模型类型: openai 或 local")
    model_name: str = Field(..., description="模型名称或路径")
    api_key: Optional[str] = Field(None, description="API密钥（仅OpenAI类型需要）")
    base_url: Optional[str] = Field(None, description="自定义API基础URL")
    temperature: float = Field(0.0, ge=0.0, le=2.0, description="采样温度")
    max_tokens: int = Field(512, ge=1, le=4096, description="最大生成token数")
    device: Optional[str] = Field("auto", description="本地模型运行设备")


class DatasetConfigRequest(BaseModel):
    """数据集配置请求模型"""
    dataset_type: DatasetType = Field(..., description="数据集类型")
    data_dir: Optional[str] = Field(None, description="数据目录路径")
    max_samples: int = Field(-1, description="最大样本数，-1表示全部")
    shuffle: bool = Field(False, description="是否打乱数据")


class EvaluationRequest(BaseModel):
    """评估请求模型"""
    model_config = ConfigDict(protected_namespaces=())
    
    eval_name: str = Field(..., description="评估任务名称")
    description: Optional[str] = Field("", description="评估描述")
    model_configuration: ModelConfigRequest = Field(..., description="模型配置")
    dataset_config: DatasetConfigRequest = Field(..., description="数据集配置")
    batch_size: int = Field(8, ge=1, le=100, description="批处理大小")
    num_workers: int = Field(4, ge=1, le=16, description="并行工作数")
    evaluate_performance: bool = Field(True, description="是否评估性能指标")
    evaluate_robustness: bool = Field(False, description="是否评估鲁棒性")
    evaluate_safety: bool = Field(False, description="是否评估安全性")


class ComparisonRequest(BaseModel):
    """模型比较请求模型"""
    eval_ids: List[str] = Field(..., min_length=2, description="要比较的评估任务ID列表")


# ==================== 响应模型 ====================

class AccuracyMetricsResponse(BaseModel):
    """准确性指标响应模型"""
    accuracy: float = Field(..., description="准确率")
    precision: float = Field(..., description="精确率")
    recall: float = Field(..., description="召回率")
    f1_score: float = Field(..., description="F1分数")
    exact_match: float = Field(..., description="精确匹配率")
    semantic_similarity: float = Field(..., description="语义相似度")


class PerformanceMetricsResponse(BaseModel):
    """性能指标响应模型"""
    inference_time: float = Field(..., description="推理时间（秒）")
    tokens_per_second: float = Field(..., description="生成速度（token/秒）")
    memory_usage_mb: float = Field(..., description="内存占用（MB）")
    latency_ms: float = Field(..., description="平均延迟（毫秒）")


class RobustnessMetricsResponse(BaseModel):
    """鲁棒性指标响应模型"""
    adversarial_accuracy: float = Field(..., description="对抗样本准确率")
    noise_robustness: float = Field(..., description="噪声鲁棒性")
    long_context_score: float = Field(..., description="长文本处理能力")


class GenerationMetricsResponse(BaseModel):
    """生成质量指标响应模型"""
    diversity: float = Field(..., description="多样性")
    coherence: float = Field(..., description="连贯性")
    perplexity: float = Field(..., description="困惑度")
    fluency: float = Field(..., description="流畅度")


class SafetyMetricsResponse(BaseModel):
    """安全性指标响应模型"""
    toxicity_score: float = Field(..., description="毒性分数")
    bias_score: float = Field(..., description="偏见分数")
    refusal_rate: float = Field(..., description="不当请求拒绝率")
    privacy_leakage: float = Field(..., description="隐私泄露风险")


class EvaluationResultResponse(BaseModel):
    """评估结果响应模型"""
    eval_id: str = Field(..., description="评估任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    dataset_name: str = Field(..., description="数据集名称")
    model_name: str = Field(..., description="模型名称")
    accuracy: Optional[AccuracyMetricsResponse] = None
    performance: Optional[PerformanceMetricsResponse] = None
    robustness: Optional[RobustnessMetricsResponse] = None
    generation: Optional[GenerationMetricsResponse] = None
    safety: Optional[SafetyMetricsResponse] = None
    total_samples: int = Field(0, description="总样本数")
    processed_samples: int = Field(0, description="已处理样本数")
    total_time_seconds: float = Field(0.0, description="总耗时（秒）")
    timestamp: str = Field(..., description="评估时间戳")
    message: Optional[str] = Field(None, description="状态消息")


class DatasetInfoResponse(BaseModel):
    """数据集信息响应模型"""
    name: str = Field(..., description="数据集名称")
    description: str = Field(..., description="数据集描述")
    task_type: str = Field(..., description="任务类型")
    total_samples: int = Field(..., description="总样本数")
    num_categories: int = Field(..., description="类别数量")
    categories: List[str] = Field(..., description="类别列表")
    category_distribution: Dict[str, int] = Field(..., description="类别分布")
    avg_question_length: float = Field(..., description="平均问题长度")


class ModelInfoResponse(BaseModel):
    """模型信息响应模型"""
    name: str = Field(..., description="模型名称")
    description: str = Field(..., description="模型描述")
    context_length: int = Field(..., description="上下文长度")
    supports_chat: bool = Field(..., description="是否支持聊天")
    supports_completion: bool = Field(..., description="是否支持补全")
    supports_streaming: bool = Field(..., description="是否支持流式")


class ComparisonResultResponse(BaseModel):
    """比较结果响应模型"""
    models: List[str] = Field(..., description="比较的模型列表")
    accuracy_comparison: Dict[str, Dict[str, float]] = Field(..., description="准确率比较")
    performance_comparison: Dict[str, Dict[str, float]] = Field(..., description="性能比较")
    ranking: List[Dict[str, Any]] = Field(..., description="排名列表")


# ==================== 通用响应模型 ====================

class APIResponse(BaseModel):
    """通用API响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
