"""
文本相似度计算模块 - 使用jieba分词和n-gram匹配

本模块提供基于n-gram的文本相似度计算功能，特别针对中文文本优化。
使用jieba进行中文分词，支持中英文混合文本的相似度计算。

主要功能：
- NGramSimilarity: n-gram相似度计算器，支持自定义权重
- calculate_text_similarity: 便捷的相似度计算函数
- SimilarityCalculators: 预配置的相似度计算器集合

算法说明：
- 使用jieba进行中文分词，空格分隔进行英文分词
- 支持1-4 gram的加权组合
- 使用精确率、召回率和F1分数的组合计算相似度

使用示例：
    # 基础用法
    >>> similarity = calculate_text_similarity("人工智能", "AI人工智能")
    >>> print(f"相似度: {similarity:.2%}")
    
    # 使用NGramSimilarity类
    >>> calculator = NGramSimilarity(ngram_weights={1: 0.1, 2: 0.3, 3: 0.4, 4: 0.2})
    >>> score = calculator.calculate_similarity("文本1", "文本2")
    
    # 使用预配置的计算器
    >>> calculator = SimilarityCalculators.chinese()
    >>> result = calculator.calculate_with_all_metrics("文本1", "文本2")
"""

from typing import List, Tuple, Dict, Any, Union
import jieba
from collections import Counter


# =============================================================================
# N-gram相似度计算器
# =============================================================================

class NGramSimilarity:
    """
    基于n-gram的文本相似度计算器
    
    使用jieba进行中文分词，支持1-4 gram的加权组合计算相似度。
    相似度计算基于精确率、召回率和F1分数的组合。
    
    Attributes:
        ngram_weights: n-gram权重字典，key为n值，value为权重
        use_jieba: 是否使用jieba进行中文分词
    
    Example:
        >>> # 使用默认权重
        >>> calculator = NGramSimilarity()
        >>> score = calculator.calculate_similarity("人工智能", "AI人工智能")
        >>> print(f"相似度: {score:.2%}")
        
        >>> # 自定义权重
        >>> calculator = NGramSimilarity(
        ...     ngram_weights={1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
        ... )
        >>> score, details = calculator.calculate_similarity(
        ...     "文本1", "文本2", return_details=True
        ... )
    """
    
    def __init__(
        self,
        ngram_weights: Dict[int, float] = None,
        use_jieba: bool = True
    ):
        """
        初始化N-gram相似度计算器
        
        Args:
            ngram_weights: n-gram权重字典，默认为{1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
            use_jieba: 是否使用jieba进行中文分词，默认为True
        """
        self.ngram_weights = ngram_weights or {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
        self.use_jieba = use_jieba
        
        # 归一化权重，使其总和为1.0
        total_weight = sum(self.ngram_weights.values())
        if total_weight > 0:
            self.ngram_weights = {k: v / total_weight for k, v in self.ngram_weights.items()}
    
    def tokenize(self, text: str) -> List[str]:
        """
        分词函数
        
        使用jieba进行中文分词，或使用空格分隔进行英文分词。
        
        Args:
            text: 输入文本
            
        Returns:
            分词后的token列表
            
        Example:
            >>> calculator = NGramSimilarity()
            >>> tokens = calculator.tokenize("人工智能")
            >>> print(tokens)  # ['人工', '智能'] 或 ['人工智能']
        """
        if not text:
            return []
        
        if self.use_jieba:
            # 使用jieba进行中文分词
            tokens = list(jieba.cut(text.strip()))
            # 过滤空token和空白字符
            tokens = [t.strip() for t in tokens if t.strip()]
        else:
            # 简单的空格分隔，适用于英文
            tokens = text.strip().split()
        
        return tokens
    
    def generate_ngrams(self, tokens: List[str], n: int) -> List[Tuple[str, ...]]:
        """
        生成n-gram
        
        从token列表生成指定大小的n-gram。
        
        Args:
            tokens: token列表
            n: n-gram大小
            
        Returns:
            n-gram元组列表
            
        Example:
            >>> calculator = NGramSimilarity()
            >>> tokens = ["人工", "智能", "技术"]
            >>> ngrams = calculator.generate_ngrams(tokens, 2)
            >>> print(ngrams)  # [('人工', '智能'), ('智能', '技术')]
        """
        if len(tokens) < n:
            return []
        
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i + n])
            ngrams.append(ngram)
        
        return ngrams
    
    def calculate_ngram_similarity(
        self,
        tokens1: List[str],
        tokens2: List[str],
        n: int
    ) -> float:
        """
        计算两个token列表的n-gram相似度
        
        使用精确率、召回率和F1分数的组合计算相似度。
        
        Args:
            tokens1: 第一个token列表（实际输出）
            tokens2: 第二个token列表（预期输出）
            n: n-gram大小
            
        Returns:
            相似度分数，范围0.0-1.0
            
        Example:
            >>> calculator = NGramSimilarity()
            >>> tokens1 = ["人工", "智能"]
            >>> tokens2 = ["人工", "智能", "技术"]
            >>> score = calculator.calculate_ngram_similarity(tokens1, tokens2, 2)
        """
        ngrams1 = self.generate_ngrams(tokens1, n)
        ngrams2 = self.generate_ngrams(tokens2, n)
        
        if not ngrams1 and not ngrams2:
            return 1.0  # 两者都为空，认为完全相同
        
        if not ngrams1 or not ngrams2:
            return 0.0  # 一个为空，无相似度
        
        # 统计n-gram出现次数
        counter1 = Counter(ngrams1)
        counter2 = Counter(ngrams2)
        
        # 计算交集
        intersection = counter1 & counter2
        intersection_count = sum(intersection.values())
        
        # 计算精确率、召回率和F1分数
        precision = intersection_count / len(ngrams1) if ngrams1 else 0.0
        recall = intersection_count / len(ngrams2) if ngrams2 else 0.0
        
        # F1分数（精确率和召回率的调和平均）
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)
        
        # 加权组合：0.3 * 精确率 + 0.3 * 召回率 + 0.4 * F1
        # 给予F1更高的权重，同时考虑精确率和召回率
        return 0.3 * precision + 0.3 * recall + 0.4 * f1
    
    def calculate_similarity(
        self,
        text1: str,
        text2: str,
        return_details: bool = False
    ) -> Union[float, Tuple[float, Dict[str, Any]]]:
        """
        计算两个文本的加权n-gram相似度
        
        Args:
            text1: 第一个文本（实际输出）
            text2: 第二个文本（预期输出）
            return_details: 是否返回详细分解信息
            
        Returns:
            如果return_details为False，返回相似度分数
            如果return_details为True，返回(分数, 详细信息)元组
            
        Example:
            >>> calculator = NGramSimilarity()
            >>> score = calculator.calculate_similarity("人工智能", "AI人工智能")
            >>> print(f"相似度: {score:.2%}")
            
            >>> score, details = calculator.calculate_similarity(
            ...     "文本1", "文本2", return_details=True
            ... )
            >>> print(details['ngram_scores'])
        """
        # 对两个文本进行分词
        tokens1 = self.tokenize(text1)
        tokens2 = self.tokenize(text2)
        
        if not tokens1 and not tokens2:
            if return_details:
                return 1.0, {"message": "Both texts are empty", "ngram_scores": {}}
            return 1.0
        
        if not tokens1 or not tokens2:
            if return_details:
                return 0.0, {"message": "One text is empty", "ngram_scores": {}}
            return 0.0
        
        # 计算每个n-gram级别的相似度
        ngram_scores = {}
        weighted_sum = 0.0
        
        for n, weight in self.ngram_weights.items():
            if n < 1 or n > 4:
                continue
            
            score = self.calculate_ngram_similarity(tokens1, tokens2, n)
            ngram_scores[f"{n}-gram"] = {
                "score": round(score, 4),
                "weight": round(weight, 4)
            }
            weighted_sum += score * weight
        
        final_score = min(1.0, max(0.0, weighted_sum))
        
        if return_details:
            details = {
                "final_score": round(final_score, 4),
                "ngram_scores": ngram_scores,
                "tokens1_count": len(tokens1),
                "tokens2_count": len(tokens2),
                "ngram_weights": self.ngram_weights
            }
            return final_score, details
        
        return final_score
    
    def calculate_with_all_metrics(
        self,
        text1: str,
        text2: str
    ) -> Dict[str, Any]:
        """
        计算全面的相似度指标
        
        除了n-gram相似度外，还计算精确匹配、token重叠率、长度比率等指标。
        
        Args:
            text1: 第一个文本（实际输出）
            text2: 第二个文本（预期输出）
            
        Returns:
            包含所有相似度指标的字典
            
        Example:
            >>> calculator = NGramSimilarity()
            >>> metrics = calculator.calculate_with_all_metrics("文本1", "文本2")
            >>> print(f"n-gram相似度: {metrics['ngram_similarity']}")
            >>> print(f"精确匹配: {metrics['exact_match']}")
            >>> print(f"token重叠: {metrics['token_overlap']}")
        """
        score, details = self.calculate_similarity(text1, text2, return_details=True)
        
        # 添加其他指标
        tokens1 = self.tokenize(text1)
        tokens2 = self.tokenize(text2)
        
        # 精确匹配
        exact_match = text1.strip() == text2.strip()
        
        # token重叠率
        set1 = set(tokens1)
        set2 = set(tokens2)
        if set1 or set2:
            token_overlap = len(set1 & set2) / len(set1 | set2) if (set1 | set2) else 1.0
        else:
            token_overlap = 1.0
        
        # 长度比率
        len1, len2 = len(text1), len(text2)
        length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 1.0
        
        return {
            "ngram_similarity": round(score, 4),
            "exact_match": exact_match,
            "token_overlap": round(token_overlap, 4),
            "length_ratio": round(length_ratio, 4),
            "details": details
        }


# =============================================================================
# 便捷函数
# =============================================================================

def calculate_text_similarity(
    actual: str,
    expected: str,
    ngram_range: Tuple[int, int] = (1, 4),
    use_jieba: bool = True
) -> float:
    """
    便捷的文本相似度计算函数
    
    快速计算两个文本的n-gram相似度，使用默认权重配置。
    
    Args:
        actual: 实际输出文本
        expected: 预期输出文本
        ngram_range: n-gram范围，默认为(1, 4)
        use_jieba: 是否使用jieba分词，默认为True
        
    Returns:
        相似度分数，范围0.0-1.0
        
    Example:
        >>> similarity = calculate_text_similarity("人工智能", "AI人工智能")
        >>> print(f"相似度: {similarity:.2%}")
        
        >>> # 只使用2-3 gram
        >>> similarity = calculate_text_similarity(
        ...     "文本1", "文本2", ngram_range=(2, 3)
        ... )
    """
    # 根据ngram_range创建默认权重
    ngram_weights = {}
    start, end = ngram_range
    for n in range(start, end + 1):
        # 高阶n-gram获得更高权重（更具体）
        ngram_weights[n] = n
    
    calculator = NGramSimilarity(ngram_weights=ngram_weights, use_jieba=use_jieba)
    return calculator.calculate_similarity(actual, expected)


# =============================================================================
# 预配置的相似度计算器
# =============================================================================

class SimilarityCalculators:
    """
    预配置的相似度计算器集合
    
    提供针对不同场景的预配置NGramSimilarity实例。
    
    Example:
        >>> # 中文优化
        >>> calculator = SimilarityCalculators.chinese()
        >>> score = calculator.calculate_similarity("文本1", "文本2")
        
        >>> # 英文优化
        >>> calculator = SimilarityCalculators.english()
        >>> score = calculator.calculate_similarity("text1", "text2")
        
        >>> # 严格匹配
        >>> calculator = SimilarityCalculators.strict()
        >>> score = calculator.calculate_similarity("文本1", "文本2")
    """
    
    @staticmethod
    def chinese() -> NGramSimilarity:
        """
        针对中文文本优化的计算器
        
        给予2-gram更高权重，适合中文短文本匹配。
        
        Returns:
            NGramSimilarity实例
        """
        return NGramSimilarity(
            ngram_weights={1: 0.25, 2: 0.35, 3: 0.25, 4: 0.15},
            use_jieba=True
        )
    
    @staticmethod
    def english() -> NGramSimilarity:
        """
        针对英文文本优化的计算器
        
        给予3-4 gram更高权重，适合英文文本匹配。
        
        Returns:
            NGramSimilarity实例
        """
        return NGramSimilarity(
            ngram_weights={1: 0.1, 2: 0.25, 3: 0.35, 4: 0.3},
            use_jieba=False
        )
    
    @staticmethod
    def balanced() -> NGramSimilarity:
        """
        平衡配置，适合中英文混合内容
        
        Returns:
            NGramSimilarity实例
        """
        return NGramSimilarity(
            ngram_weights={1: 0.15, 2: 0.25, 3: 0.3, 4: 0.3},
            use_jieba=True
        )
    
    @staticmethod
    def strict() -> NGramSimilarity:
        """
        严格匹配，强调高阶n-gram
        
        给予4-gram最高权重，要求更高的文本相似度。
        
        Returns:
            NGramSimilarity实例
        """
        return NGramSimilarity(
            ngram_weights={1: 0.05, 2: 0.15, 3: 0.35, 4: 0.45},
            use_jieba=True
        )
    
    @staticmethod
    def lenient() -> NGramSimilarity:
        """
        宽松匹配，强调低阶n-gram
        
        给予1-2 gram更高权重，对文本差异更宽容。
        
        Returns:
            NGramSimilarity实例
        """
        return NGramSimilarity(
            ngram_weights={1: 0.3, 2: 0.3, 3: 0.25, 4: 0.15},
            use_jieba=True
        )
