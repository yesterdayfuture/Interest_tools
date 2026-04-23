#!/usr/bin/env python3
"""
大语言模型评估系统 - 启动脚本

支持两种运行模式:
1. API模式: 启动FastAPI服务
2. CLI模式: 命令行执行评估任务

用法:
    python run.py api              # 启动API服务
    python run.py eval             # 执行评估任务
    python run.py test             # 测试配置
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from llm_evaluator.utils import setup_logging, load_yaml_config


def run_api_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    启动FastAPI服务
    
    Args:
        host: 监听地址
        port: 监听端口
        reload: 是否开启热重载
    """
    import uvicorn
    
    print(f"\n{'='*60}")
    print("启动 LLM Evaluator API 服务")
    print(f"{'='*60}")
    print(f"API文档地址: http://{host}:{port}/docs")
    print(f"服务地址: http://{host}:{port}")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        "llm_evaluator.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


async def run_evaluation(
    model_type: str,
    model_name: str,
    dataset_type: str,
    api_key: str = None,
    max_samples: int = -1
):
    """
    执行评估任务
    
    Args:
        model_type: 模型类型(openai/local)
        model_name: 模型名称或路径
        dataset_type: 数据集类型(mmlu/ceval)
        api_key: API密钥(OpenAI模型需要)
        max_samples: 最大样本数
    """
    from llm_evaluator.core.evaluator import Evaluator, EvaluationConfig
    from llm_evaluator.datasets import (
        MMLUDataset, CEvalDataset, TruthfulQADataset,
        GSM8KDataset, HumanEvalDataset, DatasetConfig
    )
    from llm_evaluator.models import OpenAIModel, LocalModel
    
    print(f"\n{'='*60}")
    print("大语言模型评估系统")
    print(f"{'='*60}\n")

    print(f"正在加载配置文件: config.yaml")
    config = load_yaml_config("config.yaml")
    
    # 1. 创建模型
    base_url = os.getenv("OPENAI_BASE_URL", None) or config.get("models", {}).get("openai", {}).get("base_url")
    model_name = os.getenv("OPENAI_MODEL_NAME", None) or config.get("models", {}).get("openai", {}).get(
        "default_model")
    print(f"正在初始化模型: {base_url} {model_name} ({model_type})")
    if model_type == "openai":
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", None) or config.get("models", {}).get("openai", {}).get("api_key")
            if not api_key:
                print("错误: 请提供OpenAI API密钥")
                return
        model = OpenAIModel(api_key=api_key, base_url=base_url, model_name=model_name)
    else:  # local
        model = LocalModel(model_path=model_name)
    
    # 2. 创建数据集
    print(f"正在加载数据集: {dataset_type}")
    ds_config = DatasetConfig(
        name=dataset_type,
        data_dir=f"./data",
        max_samples=max_samples
    )
    
    if dataset_type == "mmlu":
        dataset = MMLUDataset(ds_config)
    elif dataset_type == "ceval":
        dataset = CEvalDataset(ds_config)
    elif dataset_type == "truthfulqa":
        dataset = TruthfulQADataset(ds_config)
    elif dataset_type == "gsm8k":
        dataset = GSM8KDataset(ds_config)
    elif dataset_type == "humaneval":
        dataset = HumanEvalDataset(ds_config)
    else:
        print(f"错误: 不支持的数据集类型: {dataset_type}")
        return
    
    # 3. 创建评估器并执行
    eval_config = EvaluationConfig(
        name=f"{model_name}_{dataset_type}",
        batch_size=4,
        max_samples=max_samples
    )
    evaluator = Evaluator(eval_config)
    
    result = await evaluator.evaluate(model, dataset)
    
    # 4. 清理
    await model.close()
    
    print(f"\n{'='*60}")
    print("评估完成!")
    print(f"{'='*60}\n")


def test_configuration():
    """测试配置和环境"""
    print(f"\n{'='*60}")
    print("测试配置和环境")
    print(f"{'='*60}\n")
    
    # 检查Python版本
    import sys
    print(f"Python版本: {sys.version}")
    
    # 检查关键依赖
    dependencies = [
        ("fastapi", "FastAPI"),
        ("openai", "OpenAI"),
        ("transformers", "Transformers"),
        ("torch", "PyTorch"),
        ("numpy", "NumPy"),
        ("sklearn", "Scikit-learn"),
    ]
    
    print("\n依赖检查:")
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} (未安装)")
    
    # 检查配置文件
    config_path = Path("config.yaml")
    if config_path.exists():
        print(f"\n✓ 配置文件存在: {config_path}")
        try:
            config = load_yaml_config(str(config_path))
            print(f"  应用名称: {config.get('app', {}).get('name', 'N/A')}")
        except Exception as e:
            print(f"  ✗ 配置文件读取失败: {e}")
    else:
        print(f"\n✗ 配置文件不存在: {config_path}")
    
    # 检查数据目录
    data_dir = Path("data")
    if data_dir.exists():
        print(f"\n✓ 数据目录存在: {data_dir}")
        json_files = list(data_dir.glob("*.json"))
        print(f"  数据文件数量: {len(json_files)}")
    else:
        print(f"\n✗ 数据目录不存在: {data_dir}")
    
    # 检查OpenAI API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"\n✓ OPENAI_API_KEY 环境变量已设置")
    else:
        print(f"\n✗ OPENAI_API_KEY 环境变量未设置")
    
    print(f"\n{'='*60}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="大语言模型评估系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动API服务
  python run.py api

  # 使用OpenAI模型评估
  python run.py eval --model-type openai --model-name gpt-3.5-turbo --dataset mmlu

  # 测试配置
  python run.py test
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # API服务命令
    api_parser = subparsers.add_parser("api", help="启动API服务")
    api_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    api_parser.add_argument("--port", type=int, default=8000, help="监听端口")
    api_parser.add_argument("--reload", action="store_true", help="开启热重载")
    
    # 评估命令
    eval_parser = subparsers.add_parser("eval", help="执行评估任务")
    eval_parser.add_argument(
        "--model-type",
        choices=["openai", "local"],
        default="openai",
        help="模型类型"
    )
    eval_parser.add_argument(
        "--model-name",
        default="gpt-3.5-turbo",
        help="模型名称或路径"
    )
    eval_parser.add_argument(
        "--dataset",
        choices=["mmlu", "ceval", "truthfulqa", "gsm8k", "humaneval"],
        default="mmlu",
        help="数据集类型 (mmlu/ceval: 选择题, truthfulqa/gsm8k/humaneval: 文字回答)"
    )
    eval_parser.add_argument(
        "--api-key",
        default=None,
        help="OpenAI API密钥"
    )
    eval_parser.add_argument(
        "--max-samples",
        type=int,
        default=-1,
        help="最大样本数，-1表示全部"
    )
    
    # 测试命令
    subparsers.add_parser("test", help="测试配置和环境")
    
    args = parser.parse_args()
    
    if args.command == "api":
        run_api_server(args.host, args.port, args.reload)
    
    elif args.command == "eval":
        asyncio.run(run_evaluation(
            model_type=args.model_type,
            model_name=args.model_name,
            dataset_type=args.dataset,
            api_key=args.api_key,
            max_samples=args.max_samples
        ))
    
    elif args.command == "test":
        test_configuration()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    setup_logging()
    main()
