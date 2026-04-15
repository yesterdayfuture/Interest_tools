"""
Example: N-gram Similarity for Correctness Evaluation

This example demonstrates how to use the enhanced Correctness metric
with jieba tokenization and n-gram similarity calculation.
"""

from agent_eval import AgentEvaluator, EvaluationConfig
from agent_eval.models import AgentExecution, ExpectedResult
from agent_eval.text_similarity import (
    NGramSimilarity,
    calculate_text_similarity,
    SimilarityCalculators
)
from agent_eval.metrics import Correctness


def example_1_basic_similarity():
    """Example 1: Basic n-gram similarity calculation"""
    print("=" * 70)
    print("Example 1: Basic N-gram Similarity Calculation")
    print("=" * 70)
    
    # Create a similarity calculator
    calculator = NGramSimilarity(
        ngram_weights={1: 0.25, 2: 0.35, 3: 0.25, 4: 0.15},
        use_jieba=True
    )
    
    # Compare two Chinese texts
    actual = "人工智能是计算机科学的一个分支，它致力于创造能够模拟人类智能的系统。"
    expected = "人工智能是计算机科学的一个分支，旨在创建能够模仿人类智能的机器。"
    
    score, details = calculator.calculate_similarity(actual, expected, return_details=True)
    
    print(f"\nActual:   {actual}")
    print(f"Expected: {expected}")
    print(f"\nSimilarity Score: {score:.4f}")
    print("\nN-gram Breakdown:")
    for ngram_type, info in details['ngram_scores'].items():
        print(f"  {ngram_type}: {info['score']:.4f} (weight: {info['weight']:.2f})")


def example_2_correctness_metric():
    """Example 2: Using Correctness metric with n-gram similarity"""
    print("\n" + "=" * 70)
    print("Example 2: Correctness Metric with N-gram Similarity")
    print("=" * 70)
    
    # Create evaluator with default configuration
    evaluator = AgentEvaluator()
    
    # Simulate an agent execution
    execution = AgentExecution(
        execution_id="exec-001",
        query="什么是深度学习？",
        final_output="深度学习是机器学习的一个子领域，它使用多层神经网络来学习数据的表示。",
        step_count=3,
        tool_call_count=0,
        success=True
    )
    
    # Define expected output
    expected = ExpectedResult(
        expected_output="深度学习是机器学习的一个分支，它利用深层神经网络从数据中学习特征表示。"
    )
    
    # Evaluate
    result = evaluator.evaluate(execution, expected)
    
    print(f"\nQuery: {execution.query}")
    print(f"\nActual Output:\n  {execution.final_output}")
    print(f"\nExpected Output:\n  {expected.expected_output}")
    print(f"\nCorrectness Score: {result.get_metric_score('Correctness'):.4f}")
    print(f"Overall Score: {result.overall_score:.4f}")
    
    # Show detailed correctness info
    for metric in result.metric_scores:
        if metric.metric_name == "Correctness":
            print(f"\nDetailed Correctness Info:")
            print(f"  Match Type: {metric.details.get('match_type')}")
            print(f"  Similarity Score: {metric.details.get('similarity_score')}")
            if 'ngram_details' in metric.details:
                print("  N-gram Scores:")
                for ngram_type, info in metric.details['ngram_details'].get('ngram_scores', {}).items():
                    print(f"    {ngram_type}: {info['score']:.4f}")


def example_3_different_scenarios():
    """Example 3: Different similarity scenarios"""
    print("\n" + "=" * 70)
    print("Example 3: Different Similarity Scenarios")
    print("=" * 70)
    
    calculator = SimilarityCalculators.chinese()
    
    scenarios = [
        ("完全匹配", 
         "自然语言处理是人工智能的重要方向",
         "自然语言处理是人工智能的重要方向"),
        
        ("高度相似",
         "自然语言处理是人工智能的重要方向",
         "自然语言处理是人工智能的核心领域"),
        
        ("部分相似",
         "自然语言处理是人工智能的重要方向",
         "计算机视觉也是人工智能的应用领域"),
        
        ("低度相似",
         "自然语言处理是人工智能的重要方向",
         "深度学习需要大量的训练数据"),
        
        ("完全不相关",
         "自然语言处理是人工智能的重要方向",
         "今天天气很好，适合去公园散步"),
    ]
    
    print()
    for name, text1, text2 in scenarios:
        score = calculator.calculate_similarity(text1, text2)
        print(f"{name:12s}: {score:.4f}")
        print(f"  文本1: {text1}")
        print(f"  文本2: {text2}\n")


def example_4_custom_ngram_weights():
    """Example 4: Custom n-gram weights"""
    print("=" * 70)
    print("Example 4: Custom N-gram Weights")
    print("=" * 70)
    
    text1 = "机器学习算法可以从数据中学习模式"
    text2 = "机器学习技术能够从数据中发现规律"
    
    print(f"\nText 1: {text1}")
    print(f"Text 2: {text2}\n")
    
    # Different weight configurations
    configs = {
        "Strict (emphasize 3-4 grams)": {1: 0.1, 2: 0.2, 3: 0.35, 4: 0.35},
        "Balanced": {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25},
        "Lenient (emphasize 1-2 grams)": {1: 0.35, 2: 0.35, 3: 0.2, 4: 0.1},
    }
    
    for name, weights in configs.items():
        calculator = NGramSimilarity(ngram_weights=weights, use_jieba=True)
        score = calculator.calculate_similarity(text1, text2)
        print(f"{name:35s}: {score:.4f}")


def example_5_convenience_function():
    """Example 5: Using the convenience function"""
    print("\n" + "=" * 70)
    print("Example 5: Convenience Function")
    print("=" * 70)
    
    actual = "神经网络是深度学习的核心组件"
    expected = "神经网络构成了深度学习的核心"
    
    # Simple usage
    score = calculate_text_similarity(actual, expected)
    print(f"\nSimple calculation:")
    print(f"  Score: {score:.4f}")
    
    # With custom n-gram range
    score = calculate_text_similarity(actual, expected, ngram_range=(2, 4))
    print(f"\nWith n-gram range 2-4:")
    print(f"  Score: {score:.4f}")
    
    # Without jieba (for English)
    english_actual = "Machine learning is a subset of AI"
    english_expected = "Machine learning is part of artificial intelligence"
    score = calculate_text_similarity(english_actual, english_expected, use_jieba=False)
    print(f"\nEnglish text (no jieba):")
    print(f"  Score: {score:.4f}")


def example_6_batch_comparison():
    """Example 6: Batch comparison of multiple outputs"""
    print("\n" + "=" * 70)
    print("Example 6: Batch Comparison")
    print("=" * 70)
    
    expected = "自然语言处理技术广泛应用于搜索引擎、机器翻译和智能客服等领域。"
    
    candidates = [
        "自然语言处理技术被广泛应用于搜索引擎、机器翻译和智能客服等领域。",
        "NLP技术常用于搜索引擎、翻译系统和客服机器人等应用场景。",
        "计算机视觉技术在图像识别和自动驾驶中有重要应用。",
        "深度学习是机器学习的一个分支。",
    ]
    
    calculator = SimilarityCalculators.chinese()
    
    print(f"\nExpected: {expected}\n")
    print("Candidate Rankings:")
    print("-" * 50)
    
    results = []
    for i, candidate in enumerate(candidates, 1):
        score = calculator.calculate_similarity(candidate, expected)
        results.append((i, candidate, score))
    
    # Sort by score
    results.sort(key=lambda x: x[2], reverse=True)
    
    for rank, (i, candidate, score) in enumerate(results, 1):
        print(f"{rank}. [Score: {score:.4f}] {candidate[:40]}...")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("N-gram Similarity Examples for Agent Evaluation")
    print("=" * 70)
    
    example_1_basic_similarity()
    example_2_correctness_metric()
    example_3_different_scenarios()
    example_4_custom_ngram_weights()
    example_5_convenience_function()
    example_6_batch_comparison()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
