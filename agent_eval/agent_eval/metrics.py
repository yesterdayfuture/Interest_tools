"""
核心评估指标模块 - 用于智能体性能评估

本模块定义了评估智能体执行质量的各种指标，包括：
- Correctness: 结果正确性（基于n-gram文本相似度）
- StepRatio: 步骤效率
- ToolCallRatio: 工具调用效率
- SolveRate: 任务解决率
- LatencyRatio: 执行延迟率

每个指标继承自BaseMetric，实现统一的calculate接口

作者: AgentEval Team
创建日期: 2024
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from agent_eval.models import (
    AgentExecution,
    ExpectedResult,
    MetricScore,
)
from agent_eval.text_similarity import SimilarityCalculators, calculate_text_similarity, NGramSimilarity


class BaseMetric(ABC):
    """
    指标抽象基类
    
    所有评估指标必须继承此类并实现calculate方法
    提供统一的指标计算接口，便于扩展新的评估指标
    
    属性:
        name: 指标名称
        weight: 指标权重（用于加权总分计算）
    
    子类需要实现:
        calculate(): 计算指标分数并返回MetricScore
    """

    def __init__(self, name: str, weight: float = 1.0):
        """
        初始化指标
        
        参数:
            name: 指标名称，用于标识
            weight: 指标权重，影响最终加权总分
        """
        self.name = name
        self.weight = weight

    @abstractmethod
    def calculate(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> MetricScore:
        """
        计算指标分数
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            MetricScore: 包含分数、权重和详细信息的指标结果
        """
        pass

    def _create_metric_score(
        self,
        score: float,
        details: Dict[str, Any] = None
    ) -> MetricScore:
        """
        辅助方法：创建MetricScore对象
        
        自动将分数限制在0.0-1.0范围内
        
        参数:
            score: 原始分数
            details: 详细信息字典（可选）
            
        返回:
            MetricScore: 标准化的指标分数对象
        """
        return MetricScore(
            metric_name=self.name,
            score=max(0.0, min(1.0, score)),
            weight=self.weight,
            details=details or {}
        )


class Correctness(BaseMetric):
    """
    正确性指标 - 评估智能体输出与预期结果的匹配程度
    
    使用n-gram文本相似度算法，结合jieba中文分词，
    计算实际输出与预期输出之间的语义相似度
    
    算法特点:
    - 支持1-4 gram的多粒度匹配
    - 使用jieba进行中文分词，更适合中文语义
    - 综合精确率、召回率和F1分数
    - 可配置的n-gram权重
    
    匹配类型:
    - exact: 精确匹配（score >= 0.95）
    - high_similarity: 高度相似（score >= 0.7）
    - partial: 部分匹配（score >= 0.4）
    - low_similarity: 低度相似（score > 0）
    - no_match: 无匹配（score = 0）
    
    示例:
        >>> correctness = Correctness(weight=0.3)
        >>> result = correctness.calculate(execution, expected)
        >>> print(f"相似度: {result.score:.2f}, 匹配类型: {result.details['match_type']}")
    """

    def __init__(self, weight: float = 0.3, use_jieba: bool = True):
        """
        初始化正确性指标
        
        参数:
            weight: 指标权重（默认0.3）
            use_jieba: 是否使用jieba进行中文分词（默认True）
        """
        super().__init__("Correctness", weight)
        self.use_jieba = use_jieba
        # 初始化相似度计算器，使用针对中文优化的权重配置
        # 1-gram和2-gram权重较高，更好地捕捉中文语义
        self.similarity_calculator = NGramSimilarity(
            ngram_weights={1: 0.25, 2: 0.35, 3: 0.25, 4: 0.15},
            use_jieba=use_jieba
        )

    def calculate(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> MetricScore:
        """
        计算正确性分数
        
        使用n-gram相似度比较实际输出与预期输出
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            MetricScore: 包含相似度分数和详细分析的结果
        """
        # 如果没有提供预期输出，返回中性分数
        if expected is None or expected.expected_output is None:
            return self._create_metric_score(
                score=0.5,
                details={"message": "未提供预期输出，无法进行比较"}
            )

        actual_output = execution.final_output or ""
        expected_output = expected.expected_output

        # 计算n-gram相似度，获取详细分解
        similarity_score, similarity_details = self.similarity_calculator.calculate_similarity(
            actual_output,
            expected_output,
            return_details=True
        )

        # 根据相似度分数确定匹配类型
        match_type = self._determine_match_type_from_score(similarity_score)

        details = {
            "actual_output": actual_output,
            "expected_output": expected_output,
            "match_type": match_type,
            "similarity_score": round(similarity_score, 4),
            "ngram_details": similarity_details
        }

        return self._create_metric_score(score=similarity_score, details=details)

    def _determine_match_type_from_score(self, score: float) -> str:
        """
        根据相似度分数确定匹配类型
        
        参数:
            score: 相似度分数（0.0-1.0）
            
        返回:
            str: 匹配类型描述
        """
        if score >= 0.95:
            return "exact"
        elif score >= 0.7:
            return "high_similarity"
        elif score >= 0.4:
            return "partial"
        elif score > 0:
            return "low_similarity"
        else:
            return "no_match"

    def calculate_with_ngrams(
        self,
        actual: str,
        expected: str,
        ngram_weights: Optional[Dict[int, float]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        使用自定义n-gram权重计算相似度
        
        允许临时覆盖默认的n-gram权重配置
        
        参数:
            actual: 实际输出文本
            expected: 预期输出文本
            ngram_weights: 自定义n-gram权重（例如: {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}）
            
        返回:
            Tuple[float, Dict]: (相似度分数, 详细信息)
        """
        from agent_eval.text_similarity import NGramSimilarity
        
        calculator = NGramSimilarity(
            ngram_weights=ngram_weights,
            use_jieba=self.use_jieba
        )
        
        return calculator.calculate_similarity(actual, expected, return_details=True)


class StepRatio(BaseMetric):
    """
    步骤效率指标 - 评估智能体执行步骤数与最优步骤数的比率
    
    用于衡量智能体的执行效率，步骤越少通常表示效率越高
    
    评分标准:
    - ratio <= 1.0: 1.0 (完美或更优)
    - ratio <= 1.5: 0.8 (略多)
    - ratio <= 2.0: 0.6 (较多)
    - ratio <= 3.0: 0.4 (多很多)
    - ratio > 3.0: 0.2 (过多)
    
    示例:
        >>> step_ratio = StepRatio(weight=0.15)
        >>> result = step_ratio.calculate(execution, expected)
        >>> print(f"步骤比率: {result.details['actual_steps']}/{result.details['optimal_steps']}")
    """

    def __init__(self, weight: float = 0.15):
        """
        初始化步骤效率指标
        
        参数:
            weight: 指标权重（默认0.15）
        """
        super().__init__("StepRatio", weight)

    def calculate(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> MetricScore:
        """
        计算步骤效率分数
        
        比较实际执行步骤数与预期最优步骤数
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（包含最优步骤信息）
            
        返回:
            MetricScore: 步骤效率评分
        """
        actual_steps = execution.step_count

        # 如果没有提供预期步骤，使用实际步骤作为基准
        if expected is None or expected.expected_steps is None:
            optimal_steps = actual_steps
            details = {
                "actual_steps": actual_steps,
                "optimal_steps": "未知",
                "message": "未提供最优步骤数"
            }
        else:
            optimal_steps = len(expected.expected_steps)
            details = {
                "actual_steps": actual_steps,
                "optimal_steps": optimal_steps,
                "expected_steps": expected.expected_steps
            }

        # 避免除以零
        if optimal_steps == 0:
            return self._create_metric_score(score=1.0, details=details)

        # 计算步骤比率
        ratio = actual_steps / optimal_steps

        # 根据比率计算分数（阶梯式评分）
        if ratio <= 1.0:
            score = 1.0
        elif ratio <= 1.5:
            score = 0.8
        elif ratio <= 2.0:
            score = 0.6
        elif ratio <= 3.0:
            score = 0.4
        else:
            score = 0.2

        return self._create_metric_score(score=score, details=details)


class ToolCallRatio(BaseMetric):
    """
    工具调用效率指标 - 评估智能体工具调用次数与最优次数的比率
    
    同时考虑工具调用数量和工具调用序列的匹配度
    
    评分维度:
    1. 数量效率: 实际调用次数 / 最优调用次数
    2. 序列匹配: 实际调用序列与预期序列的F1分数
    
    综合分数 = (数量分数 + 序列匹配分数) / 2
    
    示例:
        >>> tool_ratio = ToolCallRatio(weight=0.2)
        >>> result = tool_ratio.calculate(execution, expected)
        >>> print(f"工具调用: {result.details['actual_tool_calls']}/{result.details['optimal_tool_calls']}")
    """

    def __init__(self, weight: float = 0.2):
        """
        初始化工具调用效率指标
        
        参数:
            weight: 指标权重（默认0.2）
        """
        super().__init__("ToolCallRatio", weight)

    def calculate(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> MetricScore:
        """
        计算工具调用效率分数
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（包含最优工具调用信息）
            
        返回:
            MetricScore: 工具调用效率评分
        """
        actual_calls = execution.tool_call_count
        actual_sequence = [tc.name for tc in execution.tool_calls_detail]

        # 确定最优工具调用次数
        if expected is None:
            optimal_calls = actual_calls
            details = {
                "actual_tool_calls": actual_calls,
                "optimal_tool_calls": "未知",
                "tool_call_sequence": actual_sequence,
                "message": "未提供最优工具调用信息"
            }
        elif expected.expected_tool_count is not None:
            optimal_calls = expected.expected_tool_count
            details = {
                "actual_tool_calls": actual_calls,
                "optimal_tool_calls": optimal_calls,
                "expected_sequence": expected.expected_tool_calls,
                "actual_sequence": actual_sequence
            }
        elif expected.expected_tool_calls is not None:
            optimal_calls = len(expected.expected_tool_calls)
            details = {
                "actual_tool_calls": actual_calls,
                "optimal_tool_calls": optimal_calls,
                "expected_sequence": expected.expected_tool_calls,
                "actual_sequence": actual_sequence
            }
        else:
            optimal_calls = actual_calls
            details = {
                "actual_tool_calls": actual_calls,
                "optimal_tool_calls": "未知",
                "tool_call_sequence": actual_sequence,
                "message": "未提供最优工具调用信息"
            }

        # 避免除以零
        if optimal_calls == 0:
            return self._create_metric_score(score=1.0, details=details)

        # 计算数量比率
        ratio = actual_calls / optimal_calls

        # 根据比率计算数量分数（阶梯式评分）
        if ratio <= 1.0:
            score = 1.0
        elif ratio <= 1.5:
            score = 0.8
        elif ratio <= 2.0:
            score = 0.6
        elif ratio <= 3.0:
            score = 0.4
        else:
            score = 0.2

        # 如果提供了预期工具调用序列，计算序列匹配度
        if expected and expected.expected_tool_calls and actual_sequence:
            sequence_match = self._calculate_sequence_match(
                actual_sequence,
                expected.expected_tool_calls
            )
            # 综合数量和序列匹配分数
            score = (score + sequence_match) / 2
            details["sequence_match_score"] = sequence_match

        return self._create_metric_score(score=score, details=details)

    def _calculate_sequence_match(
        self,
        actual: List[str],
        expected: List[str]
    ) -> float:
        """
        计算工具调用序列的匹配度
        
        使用F1分数评估实际序列与预期序列的匹配程度
        
        参数:
            actual: 实际工具调用序列
            expected: 预期工具调用序列
            
        返回:
            float: F1匹配分数（0.0-1.0）
        """
        if not expected:
            return 1.0

        expected_set = set(expected)
        actual_in_expected = sum(1 for tool in actual if tool in expected_set)

        precision = actual_in_expected / len(actual) if actual else 0
        recall = actual_in_expected / len(expected) if expected else 0

        if precision + recall == 0:
            return 0.0

        f1 = 2 * (precision * recall) / (precision + recall)
        return f1


class SolveRate(BaseMetric):
    """
    任务解决率指标 - 评估智能体是否成功完成任务
    
    综合考虑执行状态、输出内容和预期结果匹配度
    
    评分逻辑:
    - 无预期输出时:
      - 成功且有输出: 1.0
      - 成功但无输出: 0.7
      - 未成功: 0.0
    
    - 有预期输出时:
      - 执行失败: 0.0
      - 无输出: 0.0
      - 精确匹配: 1.0
      - 包含预期: 0.9
      - 关键元素匹配度 >= 80%: 0.8
      - 关键元素匹配度 >= 50%: 0.5
      - 无匹配: 0.2
    
    示例:
        >>> solve_rate = SolveRate(weight=0.25)
        >>> result = solve_rate.calculate(execution, expected)
        >>> print(f"解决状态: {result.details['reason']}")
    """

    def __init__(self, weight: float = 0.25):
        """
        初始化任务解决率指标
        
        参数:
            weight: 指标权重（默认0.25）
        """
        super().__init__("SolveRate", weight)

    def calculate(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> MetricScore:
        """
        计算任务解决率
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            MetricScore: 任务解决率评分
        """
        details = {
            "execution_success": execution.success,
            "has_error": execution.error_message is not None,
            "has_output": execution.final_output is not None
        }

        # 如果没有提供预期输出，基于执行状态评分
        if expected is None or expected.expected_output is None:
            if execution.success and execution.final_output:
                score = 1.0
                details["message"] = "任务执行成功且有输出"
            elif execution.success:
                score = 0.7
                details["message"] = "任务执行成功但无输出"
            else:
                score = 0.0
                details["message"] = "任务未成功执行"
        else:
            # 有预期输出时，计算匹配度
            score = self._calculate_solve_score(execution, expected, details)

        return self._create_metric_score(score=score, details=details)

    def _calculate_solve_score(
        self,
        execution: AgentExecution,
        expected: ExpectedResult,
        details: Dict[str, Any]
    ) -> float:
        """
        基于预期输出计算解决率
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果
            details: 详细信息字典（会被修改）
            
        返回:
            float: 解决率分数
        """
        # 执行失败
        if not execution.success:
            details["reason"] = "执行失败"
            return 0.0

        # 无输出
        if not execution.final_output:
            details["reason"] = "无输出"
            return 0.0

        expected_output = expected.expected_output.lower()
        actual_output = execution.final_output.lower()

        # 精确匹配
        if actual_output.strip() == expected_output.strip():
            details["reason"] = "精确匹配"
            return 1.0
        # 包含预期输出
        elif expected_output in actual_output:
            details["reason"] = "包含预期输出"
            return 0.9
        else:
            # 计算关键元素匹配度
            key_elements = self._extract_key_elements(expected_output)
            matches = sum(1 for elem in key_elements if elem in actual_output)
            match_ratio = matches / len(key_elements) if key_elements else 0

            if match_ratio >= 0.8:
                details["reason"] = "关键元素高度匹配"
                return 0.8
            elif match_ratio >= 0.5:
                details["reason"] = "关键元素部分匹配"
                return 0.5
            else:
                details["reason"] = "无匹配"
                return 0.2

    def _extract_key_elements(self, text: str) -> List[str]:
        """
        从文本中提取关键元素
        
        提取长度大于4的单词作为关键元素
        
        参数:
            text: 输入文本
            
        返回:
            List[str]: 关键元素列表
        """
        words = text.split()
        return [w for w in words if len(w) > 4]


class LatencyRatio(BaseMetric):
    """
    延迟率指标 - 评估智能体执行时间与最优时间的比率
    
    用于衡量智能体的执行效率，时间越短通常表示效率越高
    
    评分标准:
    - ratio <= 1.0: 1.0 (完美或更优)
    - ratio <= 1.5: 0.85 (略慢)
    - ratio <= 2.0: 0.7 (较慢)
    - ratio <= 3.0: 0.5 (慢很多)
    - ratio <= 5.0: 0.3 (过慢)
    - ratio > 5.0: 0.1 (极慢)
    
    示例:
        >>> latency = LatencyRatio(weight=0.1)
        >>> result = latency.calculate(execution, expected)
        >>> print(f"执行时间: {result.details['actual_latency']}/{result.details['optimal_latency']}")
    """

    def __init__(self, weight: float = 0.1):
        """
        初始化延迟率指标
        
        参数:
            weight: 指标权重（默认0.1）
        """
        super().__init__("LatencyRatio", weight)

    def calculate(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> MetricScore:
        """
        计算延迟率分数
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（包含最优执行时间）
            
        返回:
            MetricScore: 延迟率评分
        """
        actual_duration = execution.total_duration_ms

        # 如果没有执行时间信息
        if actual_duration is None:
            details = {
                "actual_duration_ms": None,
                "optimal_duration_ms": None,
                "message": "无执行时间信息"
            }
            return self._create_metric_score(score=0.5, details=details)

        # 确定最优执行时间
        if expected is None or expected.expected_duration_ms is None:
            optimal_duration = actual_duration
            details = {
                "actual_duration_ms": actual_duration,
                "optimal_duration_ms": "未知",
                "message": "未提供最优执行时间"
            }
        else:
            optimal_duration = expected.expected_duration_ms
            details = {
                "actual_duration_ms": actual_duration,
                "optimal_duration_ms": optimal_duration,
                "ratio": actual_duration / optimal_duration if optimal_duration else None
            }

        # 避免除以零
        if optimal_duration == 0:
            return self._create_metric_score(score=1.0, details=details)

        # 计算时间比率
        ratio = actual_duration / optimal_duration

        # 根据比率计算分数（阶梯式评分）
        if ratio <= 1.0:
            score = 1.0
        elif ratio <= 1.5:
            score = 0.85
        elif ratio <= 2.0:
            score = 0.7
        elif ratio <= 3.0:
            score = 0.5
        elif ratio <= 5.0:
            score = 0.3
        else:
            score = 0.1

        return self._create_metric_score(score=score, details=details)


class MetricCalculator:
    """
    指标计算协调器 - 聚合多个指标进行综合评估
    
    统一管理多个指标的权重配置和计算流程
    支持自定义权重和选择性启用指标
    
    默认权重配置:
    - Correctness: 0.3 (结果正确性)
    - StepRatio: 0.15 (步骤效率)
    - ToolCallRatio: 0.2 (工具调用效率)
    - SolveRate: 0.25 (任务解决率)
    - LatencyRatio: 0.1 (执行延迟率)
    
    示例:
        >>> calculator = MetricCalculator(
        ...     correctness_weight=0.4,
        ...     solve_rate_weight=0.3
        ... )
        >>> scores, overall = calculator.calculate_all(execution, expected)
        >>> print(f"综合评分: {overall:.2f}")
    """

    def __init__(
        self,
        correctness_weight: float = 0.3,
        step_ratio_weight: float = 0.15,
        tool_call_ratio_weight: float = 0.2,
        solve_rate_weight: float = 0.25,
        latency_ratio_weight: float = 0.1,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化指标计算协调器
        
        参数:
            correctness_weight: Correctness指标权重（默认0.3）
            step_ratio_weight: StepRatio指标权重（默认0.15）
            tool_call_ratio_weight: ToolCallRatio指标权重（默认0.2）
            solve_rate_weight: SolveRate指标权重（默认0.25）
            latency_ratio_weight: LatencyRatio指标权重（默认0.1）
            weights: 自定义权重字典，覆盖上述参数（可选）
            
        注意:
            所有权重之和应该等于1.0
        """
        self.metrics = {
            "Correctness": Correctness(weight=weights.get("Correctness", correctness_weight) if weights else correctness_weight),
            "StepRatio": StepRatio(weight=weights.get("StepRatio", step_ratio_weight) if weights else step_ratio_weight),
            "ToolCallRatio": ToolCallRatio(weight=weights.get("ToolCallRatio", tool_call_ratio_weight) if weights else tool_call_ratio_weight),
            "SolveRate": SolveRate(weight=weights.get("SolveRate", solve_rate_weight) if weights else solve_rate_weight),
            "LatencyRatio": LatencyRatio(weight=weights.get("LatencyRatio", latency_ratio_weight) if weights else latency_ratio_weight)
        }

    def calculate_all(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None,
        enabled_metrics: Optional[List[str]] = None
    ) -> Tuple[List[MetricScore], float]:
        """
        计算所有启用的指标并返回综合评分
        
        根据配置的权重计算加权总分
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            enabled_metrics: 要计算的指标名称列表，None表示计算所有指标
            
        返回:
            Tuple[List[MetricScore], float]: (各指标分数列表, 加权总分)
            
        示例:
            >>> scores, overall = calculator.calculate_all(execution, expected)
            >>> print(f"综合评分: {overall:.2f}")
            >>> for score in scores:
            ...     print(f"{score.metric_name}: {score.score:.2f}")
        """
        # 默认计算所有指标
        if enabled_metrics is None:
            enabled_metrics = list(self.metrics.keys())

        scores = []
        total_weight = 0.0
        weighted_sum = 0.0

        # 遍历启用的指标并计算
        for metric_name in enabled_metrics:
            if metric_name in self.metrics:
                metric = self.metrics[metric_name]
                score = metric.calculate(execution, expected)
                scores.append(score)
                weighted_sum += score.score * metric.weight
                total_weight += metric.weight

        # 计算加权平均分
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        return scores, overall_score

    def calculate_single(
        self,
        metric_name: str,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> Optional[MetricScore]:
        """
        计算单个指标
        
        参数:
            metric_name: 指标名称
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            Optional[MetricScore]: 指标分数，如果指标不存在则返回None
            
        示例:
            >>> score = calculator.calculate_single("Correctness", execution, expected)
            >>> if score:
            ...     print(f"正确性: {score.score:.2f}")
        """
        if metric_name in self.metrics:
            return self.metrics[metric_name].calculate(execution, expected)
        return None
