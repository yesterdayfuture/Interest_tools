"""
评估系统测试脚本

用于测试评估系统的基本功能
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm_evaluator.core.evaluator import Evaluator, EvaluationConfig
from llm_evaluator.core.metrics import MetricsCalculator
from llm_evaluator.datasets import MMLUDataset, CEvalDataset, DatasetConfig


async def test_metrics_calculator():
    """测试指标计算器"""
    print("\n" + "="*60)
    print("测试指标计算器")
    print("="*60)
    
    calculator = MetricsCalculator()
    
    # 测试分类指标
    predictions = ["A", "B", "C", "A", "B"]
    references = ["A", "B", "C", "B", "B"]
    
    metrics = calculator.calculate_classification_metrics(predictions, references)
    
    print(f"\n分类指标:")
    print(f"  准确率: {metrics.accuracy:.4f}")
    print(f"  精确匹配: {metrics.exact_match:.4f}")
    print(f"  F1分数: {metrics.f1_score:.4f}")
    
    # 测试多样性计算
    texts = [
        "这是一个测试文本",
        "这是另一个测试文本",
        "完全不同的内容"
    ]
    diversity = calculator.calculate_diversity(texts, n=2)
    print(f"\n多样性得分: {diversity:.4f}")
    
    print("\n✓ 指标计算器测试通过")


def test_datasets():
    """测试数据集加载"""
    print("\n" + "="*60)
    print("测试数据集")
    print("="*60)
    
    # 测试MMLU数据集
    print("\n1. 测试 MMLU 数据集")
    mmlu_config = DatasetConfig(
        name="mmlu",
        description="MMLU Test",
        data_dir="./data"
    )
    mmlu_dataset = MMLUDataset(mmlu_config)
    mmlu_dataset.load_data()
    
    stats = mmlu_dataset.get_statistics()
    print(f"  样本数: {stats['total_samples']}")
    print(f"  类别数: {stats['num_categories']}")
    print(f"  类别: {stats['categories']}")
    
    # 显示第一个样本
    if len(mmlu_dataset) > 0:
        sample = mmlu_dataset[0]
        print(f"\n  样本示例:")
        print(f"    问题: {sample.question[:50]}...")
        print(f"    答案: {sample.answer}")
        print(f"    类别: {sample.category}")
    
    # 测试C-Eval数据集
    print("\n2. 测试 C-Eval 数据集")
    ceval_config = DatasetConfig(
        name="ceval",
        description="C-Eval Test",
        data_dir="./data"
    )
    ceval_dataset = CEvalDataset(ceval_config)
    ceval_dataset.load_data()
    
    stats = ceval_dataset.get_statistics()
    print(f"  样本数: {stats['total_samples']}")
    print(f"  类别数: {stats['num_categories']}")
    
    print("\n✓ 数据集测试通过")


async def test_evaluator():
    """测试评估器"""
    print("\n" + "="*60)
    print("测试评估器")
    print("="*60)
    
    # 创建评估配置
    config = EvaluationConfig(
        name="test_eval",
        batch_size=2,
        max_samples=5
    )
    
    evaluator = Evaluator(config)
    print(f"\n评估器配置:")
    print(f"  名称: {config.name}")
    print(f"  批大小: {config.batch_size}")
    print(f"  最大样本数: {config.max_samples}")
    
    print("\n✓ 评估器测试通过")


async def test_model_interface():
    """测试模型接口"""
    print("\n" + "="*60)
    print("测试模型接口")
    print("="*60)
    
    from llm_evaluator.models import ModelConfig, ModelType
    
    # 测试模型配置
    config = ModelConfig(
        name="gpt-3.5-turbo",
        model_type=ModelType.OPENAI,
        temperature=0.0,
        max_tokens=512
    )
    
    print(f"\n模型配置:")
    print(f"  名称: {config.name}")
    print(f"  类型: {config.model_type.value}")
    print(f"  温度: {config.temperature}")
    print(f"  最大Token: {config.max_tokens}")
    
    # 注意：实际测试模型需要API密钥
    print("\n  提示: 实际模型测试需要配置API密钥")
    
    print("\n✓ 模型接口测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("大语言模型评估系统 - 测试套件")
    print("="*60)
    
    try:
        # 运行异步测试
        asyncio.run(test_metrics_calculator())
        test_datasets()
        asyncio.run(test_evaluator())
        asyncio.run(test_model_interface())
        
        print("\n" + "="*60)
        print("所有测试通过! ✓")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
