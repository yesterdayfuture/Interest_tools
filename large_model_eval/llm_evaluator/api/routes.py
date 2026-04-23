"""
FastAPI路由模块

定义所有API端点，包括：
- 评估任务管理
- 模型管理
- 数据集管理
- 结果查询和比较
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse

from .models import (
    EvaluationRequest,
    ComparisonRequest,
    APIResponse,
    ErrorResponse,
    EvaluationResultResponse,
    DatasetInfoResponse,
    ModelInfoResponse,
    ComparisonResultResponse,
    TaskStatus,
    DatasetType
)

from ..core.evaluator import Evaluator, EvaluationConfig
from ..core.metrics import EvaluationResult as CoreEvaluationResult
from ..datasets import (
    MMLUDataset, CEvalDataset, TruthfulQADataset, 
    GSM8KDataset, HumanEvalDataset, DatasetConfig
)
from ..models import OpenAIModel, LocalModel, ModelConfig, ModelType


# 创建路由
router = APIRouter(prefix="/api/v1", tags=["LLM Evaluator"])

# 内存存储（生产环境应使用数据库）
# 存储正在运行和已完成的任务
evaluation_tasks: Dict[str, dict] = {}
evaluation_results: Dict[str, CoreEvaluationResult] = {}


# ==================== 评估任务管理 ====================

@router.post("/evaluate", response_model=APIResponse)
async def create_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks
):
    """
    创建新的评估任务
    
    提交评估请求后，任务将在后台异步执行
    """
    try:
        # 生成任务ID
        eval_id = str(uuid.uuid4())
        
        # 初始化任务状态
        evaluation_tasks[eval_id] = {
            "id": eval_id,
            "status": TaskStatus.PENDING,
            "name": request.eval_name,
            "created_at": datetime.now().isoformat(),
            "progress": {"current": 0, "total": 0, "message": "等待开始"}
        }
        
        # 启动后台评估任务
        background_tasks.add_task(
            run_evaluation_task,
            eval_id,
            request
        )
        
        return APIResponse(
            success=True,
            message="评估任务已创建",
            data={
                "eval_id": eval_id,
                "status": TaskStatus.PENDING,
                "name": request.eval_name
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_evaluation_task(eval_id: str, request: EvaluationRequest):
    """
    执行评估任务（后台任务）
    
    Args:
        eval_id: 评估任务ID
        request: 评估请求
    """
    try:
        # 更新任务状态为运行中
        evaluation_tasks[eval_id]["status"] = TaskStatus.RUNNING
        evaluation_tasks[eval_id]["progress"]["message"] = "初始化模型和数据集"
        
        # 1. 创建模型实例
        # 支持配置优先级：显式配置 > 环境变量 > config.yaml > 默认值
        model_cfg = request.model_configuration
        if model_cfg.model_type == ModelType.OPENAI:
            model = OpenAIModel(
                api_key=model_cfg.api_key,      # 显式传入（优先级最高）
                base_url=model_cfg.base_url,    # 显式传入（优先级最高）
                model_name=model_cfg.model_name,
                config_path="config.yaml"          # 同时读取YAML配置文件
            )
        else:  # LOCAL
            model = LocalModel(
                model_path=model_cfg.model_name,
                device=model_cfg.device
            )
        
        # 更新模型配置
        model.config.temperature = model_cfg.temperature
        model.config.max_tokens = model_cfg.max_tokens
        
        # 2. 创建数据集实例
        dataset_config = request.dataset_config
        ds_config = DatasetConfig(
            name=dataset_config.dataset_type.value,
            description=f"Dataset: {dataset_config.dataset_type.value}",
            data_dir=dataset_config.data_dir or f"./data/{dataset_config.dataset_type.value}",
            max_samples=dataset_config.max_samples,
            shuffle=dataset_config.shuffle
        )
        
        if dataset_config.dataset_type == DatasetType.MMLU:
            dataset = MMLUDataset(ds_config)
        elif dataset_config.dataset_type == DatasetType.CEVAL:
            dataset = CEvalDataset(ds_config)
        elif dataset_config.dataset_type == DatasetType.TRUTHFULQA:
            dataset = TruthfulQADataset(ds_config)
        elif dataset_config.dataset_type == DatasetType.GSM8K:
            dataset = GSM8KDataset(ds_config)
        elif dataset_config.dataset_type == DatasetType.HUMANEVAL:
            dataset = HumanEvalDataset(ds_config)
        else:
            raise ValueError(f"不支持的数据集类型: {dataset_config.dataset_type}")
        
        # 3. 创建评估器
        eval_config = EvaluationConfig(
            name=request.eval_name,
            description=request.description,
            batch_size=request.batch_size,
            num_workers=request.num_workers,
            evaluate_performance=request.evaluate_performance,
            evaluate_robustness=request.evaluate_robustness,
            evaluate_safety=request.evaluate_safety
        )
        evaluator = Evaluator(eval_config)
        
        # 进度回调函数
        def progress_callback(current: int, total: int, message: str):
            evaluation_tasks[eval_id]["progress"] = {
                "current": current,
                "total": total,
                "message": message,
                "percentage": round(current / total * 100, 2) if total > 0 else 0
            }
        
        # 4. 执行评估
        result = await evaluator.evaluate(model, dataset, progress_callback)
        
        # 5. 保存结果
        evaluation_results[eval_id] = result
        evaluation_tasks[eval_id]["status"] = TaskStatus.COMPLETED
        evaluation_tasks[eval_id]["progress"]["message"] = "评估完成"
        evaluation_tasks[eval_id]["completed_at"] = datetime.now().isoformat()
        
        # 6. 关闭模型
        await model.close()
        
    except Exception as e:
        evaluation_tasks[eval_id]["status"] = TaskStatus.FAILED
        evaluation_tasks[eval_id]["error"] = str(e)
        evaluation_tasks[eval_id]["progress"]["message"] = f"评估失败: {str(e)}"


@router.get("/evaluate/{eval_id}/status", response_model=APIResponse)
async def get_evaluation_status(eval_id: str):
    """
    获取评估任务状态
    
    查询指定评估任务的当前状态和进度
    """
    if eval_id not in evaluation_tasks:
        raise HTTPException(status_code=404, detail="评估任务不存在")
    
    task = evaluation_tasks[eval_id]
    
    return APIResponse(
        success=True,
        message="获取状态成功",
        data={
            "eval_id": eval_id,
            "status": task["status"],
            "name": task["name"],
            "progress": task.get("progress", {}),
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at")
        }
    )


@router.get("/evaluate/{eval_id}/result", response_model=EvaluationResultResponse)
async def get_evaluation_result(eval_id: str):
    """
    获取评估结果
    
    获取已完成评估任务的详细结果
    """
    if eval_id not in evaluation_tasks:
        raise HTTPException(status_code=404, detail="评估任务不存在")
    
    task = evaluation_tasks[eval_id]
    
    if task["status"] != TaskStatus.COMPLETED:
        return EvaluationResultResponse(
            eval_id=eval_id,
            status=task["status"],
            dataset_name="",
            model_name="",
            message=f"任务状态: {task['status']}"
        )
    
    if eval_id not in evaluation_results:
        raise HTTPException(status_code=404, detail="评估结果不存在")
    
    result = evaluation_results[eval_id]
    
    return EvaluationResultResponse(
        eval_id=eval_id,
        status=TaskStatus.COMPLETED,
        dataset_name=result.dataset_name,
        model_name=result.model_name,
        accuracy={
            "accuracy": result.accuracy.accuracy,
            "precision": result.accuracy.precision,
            "recall": result.accuracy.recall,
            "f1_score": result.accuracy.f1_score,
            "exact_match": result.accuracy.exact_match,
            "semantic_similarity": result.accuracy.semantic_similarity
        },
        performance={
            "inference_time": result.performance.inference_time,
            "tokens_per_second": result.performance.tokens_per_second,
            "memory_usage_mb": result.performance.memory_usage_mb,
            "latency_ms": result.performance.latency_ms
        },
        robustness={
            "adversarial_accuracy": result.robustness.adversarial_accuracy,
            "noise_robustness": result.robustness.noise_robustness,
            "long_context_score": result.robustness.long_context_score
        },
        generation={
            "diversity": result.generation.diversity,
            "coherence": result.generation.coherence,
            "perplexity": result.generation.perplexity,
            "fluency": result.generation.fluency
        },
        safety={
            "toxicity_score": result.safety.toxicity_score,
            "bias_score": result.safety.bias_score,
            "refusal_rate": result.safety.refusal_rate,
            "privacy_leakage": result.safety.privacy_leakage
        },
        total_samples=len(result.raw_predictions),
        processed_samples=len(result.raw_predictions),
        total_time_seconds=result.metadata.get("total_time_seconds", 0),
        timestamp=result.metadata.get("timestamp", ""),
        message="评估完成"
    )


@router.get("/evaluate", response_model=APIResponse)
async def list_evaluations(
    status: Optional[TaskStatus] = Query(None, description="按状态筛选")
):
    """
    列出所有评估任务
    
    可选按状态筛选任务
    """
    tasks = []
    for eval_id, task in evaluation_tasks.items():
        if status is None or task["status"] == status:
            tasks.append({
                "eval_id": eval_id,
                "name": task["name"],
                "status": task["status"],
                "created_at": task["created_at"],
                "completed_at": task.get("completed_at")
            })
    
    # 按时间倒序排列
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return APIResponse(
        success=True,
        message=f"找到 {len(tasks)} 个评估任务",
        data=tasks
    )


@router.delete("/evaluate/{eval_id}", response_model=APIResponse)
async def delete_evaluation(eval_id: str):
    """
    删除评估任务
    
    删除指定评估任务及其结果
    """
    if eval_id not in evaluation_tasks:
        raise HTTPException(status_code=404, detail="评估任务不存在")
    
    del evaluation_tasks[eval_id]
    if eval_id in evaluation_results:
        del evaluation_results[eval_id]
    
    return APIResponse(
        success=True,
        message="评估任务已删除",
        data={"eval_id": eval_id}
    )


# ==================== 结果比较 ====================

@router.post("/compare", response_model=ComparisonResultResponse)
async def compare_evaluations(request: ComparisonRequest):
    """
    比较多个评估结果
    
    对比不同模型或配置的评估表现
    """
    results = []
    for eval_id in request.eval_ids:
        if eval_id not in evaluation_results:
            raise HTTPException(status_code=404, detail=f"评估结果不存在: {eval_id}")
        results.append(evaluation_results[eval_id])
    
    # 使用Evaluator的比较功能
    evaluator = Evaluator(EvaluationConfig(name="comparison"))
    comparison = evaluator.compare_results(results)
    
    return ComparisonResultResponse(
        models=comparison["models"],
        accuracy_comparison=comparison["accuracy"],
        performance_comparison=comparison["performance"],
        ranking=comparison["ranking"]
    )


# ==================== 数据集管理 ====================

@router.get("/datasets", response_model=APIResponse)
async def list_datasets():
    """
    列出支持的数据集
    
    获取系统支持的所有数据集类型
    """
    datasets = [
        {
            "type": DatasetType.MMLU,
            "name": "MMLU",
            "description": "Massive Multi-task Language Understanding - 多学科选择题数据集",
            "languages": ["English"],
            "task_type": "multiple_choice"
        },
        {
            "type": DatasetType.CEVAL,
            "name": "C-Eval",
            "description": "Chinese Evaluation - 中文大模型评测数据集",
            "languages": ["Chinese"],
            "task_type": "multiple_choice"
        },
        {
            "type": DatasetType.CMMLU,
            "name": "CMMLU",
            "description": "Chinese Massive Multi-task Language Understanding",
            "languages": ["Chinese"],
            "task_type": "multiple_choice"
        },
        {
            "type": DatasetType.TRUTHFULQA,
            "name": "TruthfulQA",
            "description": "评估模型回答的真实性",
            "languages": ["English"],
            "task_type": "question_answering"
        }
    ]
    
    return APIResponse(
        success=True,
        message=f"支持 {len(datasets)} 个数据集",
        data=datasets
    )


@router.get("/datasets/{dataset_type}/info", response_model=DatasetInfoResponse)
async def get_dataset_info(dataset_type: DatasetType):
    """
    获取数据集信息
    
    获取指定数据集的详细信息，包括样本数、类别分布等
    """
    try:
        # 创建临时数据集实例获取信息
        if dataset_type == DatasetType.MMLU:
            dataset = MMLUDataset()
        elif dataset_type == DatasetType.CEVAL:
            dataset = CEvalDataset()
        else:
            raise HTTPException(status_code=400, detail=f"暂不支持的数据集: {dataset_type}")
        
        # 加载数据
        dataset.load_data()
        
        # 获取统计信息
        stats = dataset.get_statistics()
        
        return DatasetInfoResponse(
            name=stats["name"],
            description=stats["description"],
            task_type=stats["task_type"],
            total_samples=stats["total_samples"],
            num_categories=stats["num_categories"],
            categories=stats["categories"],
            category_distribution=stats["category_distribution"],
            avg_question_length=stats["avg_question_length"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/{dataset_type}/preview", response_model=APIResponse)
async def preview_dataset(
    dataset_type: DatasetType,
    n: int = Query(5, ge=1, le=20, description="预览样本数")
):
    """
    预览数据集样本
    
    获取数据集的前N个样本进行预览
    """
    try:
        if dataset_type == DatasetType.MMLU:
            dataset = MMLUDataset()
        elif dataset_type == DatasetType.CEVAL:
            dataset = CEvalDataset()
        else:
            raise HTTPException(status_code=400, detail=f"暂不支持的数据集: {dataset_type}")
        
        dataset.load_data()
        preview = dataset.preview(n)
        
        return APIResponse(
            success=True,
            message=f"成功获取 {len(preview)} 个样本",
            data=preview
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 模型管理 ====================

@router.get("/models/supported", response_model=APIResponse)
async def list_supported_models():
    """
    列出支持的模型类型
    
    获取系统支持的模型类型和示例
    """
    models = [
        {
            "type": "openai",
            "name": "OpenAI API",
            "description": "通过OpenAI API访问GPT系列模型",
            "examples": [
                "gpt-3.5-turbo",
                "gpt-4",
                "gpt-4-turbo"
            ]
        },
        {
            "type": "local",
            "name": "本地模型",
            "description": "使用HuggingFace Transformers加载本地模型",
            "examples": [
                "gpt2",
                "meta-llama/Llama-2-7b-hf",
                "THUDM/chatglm3-6b"
            ]
        }
    ]
    
    return APIResponse(
        success=True,
        message=f"支持 {len(models)} 种模型类型",
        data=models
    )


@router.post("/models/test", response_model=APIResponse)
async def test_model_connection(request: dict):
    """
    测试模型连接
    
    测试与指定模型的连接是否正常
    
    请求体示例:
    {
        "model_type": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": "your-api-key",
        "base_url": "optional-custom-url"
    }
    """
    try:
        model_type = request.get("model_type")
        
        if model_type == "openai":
            model = OpenAIModel(
                api_key=request.get("api_key"),
                base_url=request.get("base_url"),
                model_name=request.get("model_name", "gpt-3.5-turbo")
            )
        elif model_type == "local":
            model = LocalModel(
                model_path=request.get("model_name"),
                device=request.get("device", "auto")
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的模型类型: {model_type}")
        
        # 测试连接
        await model.initialize()
        is_healthy = await model.health_check()
        
        # 获取模型信息
        model_info = await model.get_model_info()
        
        # 关闭连接
        await model.close()
        
        return APIResponse(
            success=is_healthy,
            message="模型连接测试成功" if is_healthy else "模型连接测试失败",
            data={
                "model_type": model_type,
                "model_name": request.get("model_name"),
                "healthy": is_healthy,
                "model_info": {
                    "name": model_info.name,
                    "description": model_info.description,
                    "context_length": model_info.context_length,
                    "supports_chat": model_info.supports_chat,
                    "supports_completion": model_info.supports_completion,
                    "supports_streaming": model_info.supports_streaming
                }
            }
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"模型连接测试失败: {str(e)}",
            data={"error": str(e)}
        )


# ==================== 系统信息 ====================

@router.get("/health", response_model=APIResponse)
async def health_check():
    """
    健康检查
    
    检查API服务是否正常运行
    """
    return APIResponse(
        success=True,
        message="服务正常运行",
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_tasks": sum(1 for t in evaluation_tasks.values() if t["status"] == TaskStatus.RUNNING),
            "completed_tasks": sum(1 for t in evaluation_tasks.values() if t["status"] == TaskStatus.COMPLETED)
        }
    )
