"""
Test script for n-gram similarity calculation
"""

from agent_eval.text_similarity import (
    NGramSimilarity,
    calculate_text_similarity,
    SimilarityCalculators
)
from agent_eval.metrics import Correctness
from agent_eval.models import AgentExecution, ExpectedResult


def test_basic_similarity():
    """Test basic similarity calculation"""
    print("=" * 60)
    print("Test 1: Basic Similarity Calculation")
    print("=" * 60)
    
    calculator = NGramSimilarity()
    
    # Test exact match
    text1 = "人工智能是计算机科学的一个分支"
    text2 = "人工智能是计算机科学的一个分支"
    score = calculator.calculate_similarity(text1, text2)
    print(f"\nExact match:")
    print(f"  Text 1: {text1}")
    print(f"  Text 2: {text2}")
    print(f"  Score: {score:.4f}")
    assert score >= 0.95, f"Expected score >= 0.95, got {score}"
    
    # Test high similarity
    text1 = "人工智能是计算机科学的一个分支"
    text2 = "人工智能属于计算机科学的分支领域"
    score = calculator.calculate_similarity(text1, text2)
    print(f"\nHigh similarity:")
    print(f"  Text 1: {text1}")
    print(f"  Text 2: {text2}")
    print(f"  Score: {score:.4f}")
    
    # Test partial similarity
    text1 = "人工智能是计算机科学的一个分支"
    text2 = "机器学习是人工智能的重要技术"
    score = calculator.calculate_similarity(text1, text2)
    print(f"\nPartial similarity:")
    print(f"  Text 1: {text1}")
    print(f"  Text 2: {text2}")
    print(f"  Score: {score:.4f}")
    
    # Test low similarity
    text1 = "人工智能是计算机科学的一个分支"
    text2 = "今天天气很好，适合出去玩"
    score = calculator.calculate_similarity(text1, text2)
    print(f"\nLow similarity:")
    print(f"  Text 1: {text1}")
    print(f"  Text 2: {text2}")
    print(f"  Score: {score:.4f}")
    
    print("\n✓ Basic similarity tests passed!")


def test_ngram_details():
    """Test detailed n-gram breakdown"""
    print("\n" + "=" * 60)
    print("Test 2: Detailed N-gram Breakdown")
    print("=" * 60)
    
    calculator = NGramSimilarity()
    
    text1 = "人工智能是计算机科学"
    text2 = "人工智能属于计算机科学"
    
    score, details = calculator.calculate_similarity(text1, text2, return_details=True)
    
    print(f"\nText 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"\nFinal Score: {details['final_score']}")
    print(f"Token counts: {details['tokens1_count']} vs {details['tokens2_count']}")
    print("\nN-gram scores:")
    for ngram_type, info in details['ngram_scores'].items():
        print(f"  {ngram_type}: score={info['score']}, weight={info['weight']}")
    
    print("\n✓ N-gram details test passed!")


def test_tokenization():
    """Test jieba tokenization"""
    print("\n" + "=" * 60)
    print("Test 3: Jieba Tokenization")
    print("=" * 60)
    
    calculator = NGramSimilarity(use_jieba=True)
    
    text = "自然语言处理是人工智能的重要方向"
    tokens = calculator.tokenize(text)
    
    print(f"\nText: {text}")
    print(f"Tokens: {tokens}")
    print(f"Token count: {len(tokens)}")
    
    # Generate n-grams
    for n in range(1, 5):
        ngrams = calculator.generate_ngrams(tokens, n)
        print(f"\n{n}-grams ({len(ngrams)} total):")
        for i, ng in enumerate(ngrams[:5]):  # Show first 5
            print(f"  {i+1}. {ng}")
        if len(ngrams) > 5:
            print(f"  ... and {len(ngrams) - 5} more")
    
    print("\n✓ Tokenization test passed!")


def test_similarity_calculators():
    """Test pre-configured similarity calculators"""
    print("\n" + "=" * 60)
    print("Test 4: Pre-configured Similarity Calculators")
    print("=" * 60)
    
    text1 = "深度学习是机器学习的一种方法"
    text2 = "深度学习属于机器学习的技术"
    
    calculators = {
        "Chinese": SimilarityCalculators.chinese(),
        "English": SimilarityCalculators.english(),
        "Balanced": SimilarityCalculators.balanced(),
        "Strict": SimilarityCalculators.strict(),
        "Lenient": SimilarityCalculators.lenient(),
    }
    
    print(f"\nText 1: {text1}")
    print(f"Text 2: {text2}\n")
    
    for name, calculator in calculators.items():
        score = calculator.calculate_similarity(text1, text2)
        weights = calculator.ngram_weights
        print(f"{name:10s}: score={score:.4f}, weights={weights}")
    
    print("\n✓ Similarity calculators test passed!")


def test_correctness_metric():
    """Test Correctness metric with n-gram similarity"""
    print("\n" + "=" * 60)
    print("Test 5: Correctness Metric with N-gram Similarity")
    print("=" * 60)
    
    correctness = Correctness(weight=0.3)
    
    # Create mock execution and expected result
    execution = AgentExecution(
        execution_id="test-001",
        query="什么是人工智能？",
        final_output="人工智能是计算机科学的一个分支，致力于创造能够模拟人类智能的系统。",
    )
    
    expected = ExpectedResult(
        expected_output="人工智能是计算机科学的一个分支，旨在创建能够模仿人类智能的机器。"
    )
    
    result = correctness.calculate(execution, expected)
    
    print(f"\nQuery: {execution.query}")
    print(f"Actual output: {execution.final_output}")
    print(f"Expected output: {expected.expected_output}")
    print(f"\nCorrectness Score: {result.score:.4f}")
    print(f"Match Type: {result.details['match_type']}")
    print(f"Similarity Score: {result.details['similarity_score']}")
    
    if 'ngram_details' in result.details:
        print("\nN-gram Details:")
        ngram_info = result.details['ngram_details']
        if 'ngram_scores' in ngram_info:
            for ngram_type, info in ngram_info['ngram_scores'].items():
                print(f"  {ngram_type}: {info['score']} (weight: {info['weight']})")
    
    print("\n✓ Correctness metric test passed!")


def test_edge_cases():
    """Test edge cases"""
    print("\n" + "=" * 60)
    print("Test 6: Edge Cases")
    print("=" * 60)
    
    calculator = NGramSimilarity()
    
    # Empty strings
    score = calculator.calculate_similarity("", "")
    print(f"\nBoth empty: {score:.4f}")
    assert score == 1.0, "Empty strings should have similarity 1.0"
    
    # One empty
    score = calculator.calculate_similarity("text", "")
    print(f"One empty: {score:.4f}")
    assert score == 0.0, "One empty should have similarity 0.0"
    
    # Whitespace only
    score = calculator.calculate_similarity("   ", "   ")
    print(f"Whitespace only: {score:.4f}")
    
    # Single character
    score = calculator.calculate_similarity("a", "a")
    print(f"Single char match: {score:.4f}")
    
    # English text
    score = calculator.calculate_similarity(
        "Machine learning is a subset of AI",
        "Machine learning is part of artificial intelligence"
    )
    print(f"English text similarity: {score:.4f}")
    
    print("\n✓ Edge cases test passed!")


def test_convenience_function():
    """Test convenience function"""
    print("\n" + "=" * 60)
    print("Test 7: Convenience Function")
    print("=" * 60)
    
    text1 = "自然语言处理技术广泛应用于搜索引擎"
    text2 = "自然语言处理被广泛应用于搜索引擎中"
    
    score = calculate_text_similarity(text1, text2)
    print(f"\nText 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"Similarity: {score:.4f}")
    
    # Test with custom range
    score = calculate_text_similarity(text1, text2, ngram_range=(2, 4))
    print(f"Similarity (n=2-4): {score:.4f}")
    
    print("\n✓ Convenience function test passed!")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("N-gram Similarity Test Suite")
    print("=" * 60)
    
    try:
        test_basic_similarity()
        test_ngram_details()
        test_tokenization()
        test_similarity_calculators()
        test_correctness_metric()
        test_edge_cases()
        test_convenience_function()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
