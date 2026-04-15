"""
核心评估模块 - 智能体评估的主入口

本模块提供AgentEvaluator类，作为整个评估框架的核心协调器。
集成了记录、指标计算、评分和存储等功能，提供统一的评估接口。

主要功能：
1. 执行记录管理：自动记录智能体的执行过程
2. 指标计算：计算多维度的性能指标
3. 质量评分：使用代码检查和LLM评估质量
4. 结果存储：支持多种存储后端
5. 报告生成：生成评估报告和可视化

使用示例：
    >>> from agent_eval import AgentEvaluator, EvaluationConfig
    >>> config = EvaluationConfig(storage_type="sqlite")
    >>> evaluator = AgentEvaluator(config)
    >>> 
    >>> # 记录执行
    >>> with evaluator.record_execution("查询天气") as recorder:
    ...     result = agent.run("查询天气")
    ...     recorder.set_result(result)
    >>> 
    >>> # 评估
    >>> evaluation = evaluator.evaluate(execution, expected)

作者: AgentEval Team
创建日期: 2024
"""

import uuid
from typing import Any, Dict, List, Optional, Callable

from agent_eval.models import (
    AgentExecution,
    EvaluationConfig,
    EvaluationResult,
    ExpectedResult,
    LLMConfig,
    MetricScore,
    StorageConfig,
)
from agent_eval.metrics import MetricCalculator
from agent_eval.scorers import (
    BaseScorer,
    CodeBasedScorer,
    HybridScorer,
    LLMJudgeScorer,
)
from agent_eval.recorders import ExecutionRecorder, create_recorder
from agent_eval.storages import create_storage, BaseStorage
from agent_eval.generators import MetadataGenerator


class AgentEvaluator:
    """
    智能体评估器 - 评估智能体性能的主类

    作为评估框架的核心协调器，集成了以下功能：
    - 执行记录：自动记录智能体的执行过程
    - 指标计算：计算Correctness、StepRatio等多维度指标
    - 质量评分：使用CodeBasedScorer和LLMJudgeScorer评估质量
    - 数据存储：支持JSON、CSV、SQLite、PostgreSQL等多种存储
    - 报告生成：生成详细的评估报告

    属性:
        config: 评估配置
        storage: 存储后端实例
        recorder: 执行记录器
        metric_calculator: 指标计算器
        scorers: 评分器列表

    示例:
        >>> config = EvaluationConfig(
        ...     storage_type=StorageType.SQLITE,
        ...     auto_record=True
        ... )
        >>> evaluator = AgentEvaluator(config)
        >>> 
        >>> # 方式1：使用上下文管理器自动记录
        >>> with evaluator.record_execution("用户查询") as rec:
        ...     output = agent.process("用户查询")
        ...     rec.set_result(output)
        >>> 
        >>> # 方式2：手动创建执行记录
        >>> execution = evaluator.create_execution("查询", steps, output)
        >>> evaluation = evaluator.evaluate(execution, expected)
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        初始化智能体评估器

        根据配置初始化所有组件：存储后端、记录器、指标计算器和评分器。
        如果配置中提供了LLM配置，还会初始化元数据生成器。

        Args:
            config: 评估配置对象，包含存储类型、指标权重、评分器配置等
                   如果为None，则使用默认配置

        Example:
            >>> config = EvaluationConfig(storage_type="json")
            >>> evaluator = AgentEvaluator(config)
        """
        self.config = config or EvaluationConfig()

        # 初始化存储后端
        self.storage = self._init_storage()

        # 初始化记录器
        self.recorder = create_recorder(
            storage=self.storage if self.config.auto_record else None,
            auto_save=self.config.auto_record
        )

        # 初始化指标计算器
        self.metric_calculator = self._init_metric_calculator()

        # 初始化评分器
        self.scorers = self._init_scorers()

        # 如果提供了LLM配置，初始化元数据生成器
        self.metadata_generator = None
        if self.config.llm_config:
            self.metadata_generator = MetadataGenerator(self.config.llm_config)

    def _init_storage(self) -> Optional[BaseStorage]:
        """
        初始化存储后端

        根据配置创建相应的存储后端实例。
        支持的存储类型：JSON文件、CSV文件、SQLite数据库、PostgreSQL数据库

        Returns:
            存储后端实例，如果未配置存储则返回None

        Example:
            >>> storage = self._init_storage()
            >>> if storage:
            ...     print(f"使用存储: {type(storage).__name__}")
        """
        if self.config.storage_config:
            return create_storage(self.config.storage_config)
        return None

    def _init_metric_calculator(self) -> MetricCalculator:
        """
        初始化指标计算器

        使用配置中的权重初始化指标计算器。
        支持计算的指标包括：
        - Correctness: 正确性指标
        - StepRatio: 步骤比例指标
        - ToolCallRatio: 工具调用比例指标
        - SolveRate: 解决率指标
        - LatencyRatio: 延迟比例指标

        Returns:
            配置好的指标计算器实例

        Example:
            >>> calculator = self._init_metric_calculator()
            >>> scores = calculator.calculate_all(execution, expected)
        """
        return MetricCalculator(
            correctness_weight=self.config.correctness_weight,
            step_ratio_weight=self.config.step_ratio_weight,
            tool_call_ratio_weight=self.config.tool_call_ratio_weight,
            solve_rate_weight=self.config.solve_rate_weight,
            latency_ratio_weight=self.config.latency_ratio_weight
        )

    def _init_scorers(self) -> List[BaseScorer]:
        """
        初始化评分器列表

        根据配置初始化一个或多个评分器：
        - CodeBasedScorer: 基于代码规则的评分器
        - LLMJudgeScorer: 基于LLM判断的评分器
        - HybridScorer: 混合评分器（代码规则 + LLM判断）

        Returns:
            评分器实例列表

        Example:
            >>> scorers = self._init_scorers()
            >>> for scorer in scorers:
            ...     result = scorer.score(execution, expected)
        """
        scorers = []

        if self.config.use_code_scorer:
            # 创建基于代码的评分器
            code_scorer = CodeBasedScorer(
                check_tool_sequence=True,    # 检查工具调用顺序
                check_tool_count=True,       # 检查工具调用数量
                check_output_format=True,    # 检查输出格式
                check_exact_match=False      # 不检查精确匹配
            )

            # 如果同时启用LLM评分器，创建混合评分器
            if self.config.use_llm_scorer and self.config.llm_config:
                hybrid_scorer = HybridScorer(
                    code_scorer=code_scorer,
                    llm_scorer=LLMJudgeScorer(self.config.llm_config),
                    code_weight=0.4,  # 代码评分权重40%
                    llm_weight=0.6    # LLM评分权重60%
                )
                scorers.append(hybrid_scorer)
            else:
                scorers.append(code_scorer)
        elif self.config.use_llm_scorer and self.config.llm_config:
            # 仅使用LLM评分器
            scorers.append(LLMJudgeScorer(self.config.llm_config))

        return scorers

    def start_recording(self, query: str, metadata: Optional[Dict[str, Any]] = None):
        """
        开始记录执行

        开始一个新的执行记录会话，用于手动控制记录过程。
        与上下文管理器方式相比，这种方式提供了更细粒度的控制。

        Args:
            query: 用户查询字符串
            metadata: 可选的元数据字典

        Returns:
            执行记录对象

        Example:
            >>> recorder = evaluator.start_recording("查询天气")
            >>> # 执行智能体逻辑
            >>> result = agent.run("查询天气")
            >>> recorder.set_output(result)
            >>> execution = evaluator.end_recording()
        """
        return self.recorder.start_recording(query, metadata)

    def end_recording(
        self,
        success: bool = True,
        error_message: Optional[str] = None,
        final_output: Optional[str] = None
    ) -> AgentExecution:
        """
        结束记录并返回执行记录

        结束当前执行记录会话，保存执行记录到存储（如果配置了）。

        Args:
            success: 执行是否成功，默认为True
            error_message: 如果失败，错误信息
            final_output: 最终输出结果

        Returns:
            完成的AgentExecution对象

        Raises:
            RuntimeError: 如果没有活跃的记录会话

        Example:
            >>> execution = evaluator.end_recording(
            ...     success=True,
            ...     final_output="北京今天晴天"
            ... )
        """
        return self.recorder.end_recording(success, error_message, final_output)

    def record_step(self, description: str, metadata: Optional[Dict[str, Any]] = None):
        """
        在当前执行中记录步骤

        记录智能体执行过程中的一个步骤。

        Args:
            description: 步骤描述，例如"解析查询意图"
            metadata: 可选的元数据字典

        Returns:
            创建的步骤详情对象

        Raises:
            RuntimeError: 如果没有活跃的记录会话

        Example:
            >>> evaluator.record_step("解析地点", {"location": "北京"})
            >>> evaluator.record_step("获取天气数据")
        """
        return self.recorder.record_step(description, metadata)

    def record_tool_call(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None,
        duration_ms: Optional[float] = None
    ):
        """
        在当前执行中记录工具调用

        记录智能体调用外部工具的详细信息。

        Args:
            tool_name: 工具名称，例如"search", "calculator"
            arguments: 工具输入参数
            result: 工具执行结果
            duration_ms: 执行耗时（毫秒）

        Returns:
            创建的工具调用详情对象

        Raises:
            RuntimeError: 如果没有活跃的记录会话

        Example:
            >>> evaluator.record_tool_call(
            ...     "search",
            ...     {"q": "北京天气"},
            ...     result="晴天 25°C",
            ...     duration_ms=150
            ... )
        """
        return self.recorder.record_tool_call(tool_name, arguments, result, duration_ms)

    def evaluate(
        self,
        execution: Optional[AgentExecution] = None,
        expected: Optional[ExpectedResult] = None,
        save_result: bool = True
    ) -> EvaluationResult:
        """
        评估智能体执行

        对智能体执行进行全面评估，包括：
        1. 计算各项性能指标
        2. 应用评分器进行质量评分
        3. 生成评估结果
        4. 保存评估结果（如果配置了存储）

        Args:
            execution: 要评估的执行记录，如果为None则使用最近记录的执行
            expected: 预期结果，用于对比评估
            save_result: 是否保存评估结果，默认为True

        Returns:
            评估结果对象，包含总体分数、各项指标分数、评分器结果等

        Raises:
            ValueError: 如果没有提供执行记录且没有历史记录

        Example:
            >>> execution = evaluator.end_recording()
            >>> expected = ExpectedResult(
            ...     query="北京天气",
            ...     expected_steps=["解析地点", "获取数据"],
            ...     expected_tools=["weather_api"],
            ...     expected_output="晴天"
            ... )
            >>> result = evaluator.evaluate(execution, expected)
            >>> print(f"总体分数: {result.overall_score}")
        """
        # 如果没有提供执行记录，使用最近记录的执行
        if execution is None:
            history = self.recorder.get_execution_history()
            if not history:
                raise ValueError("没有提供执行记录且没有历史记录")
            execution = history[-1]

        # 确定启用的指标
        enabled_metrics = []
        if self.config.enable_correctness:
            enabled_metrics.append("Correctness")
        if self.config.enable_step_ratio:
            enabled_metrics.append("StepRatio")
        if self.config.enable_tool_call_ratio:
            enabled_metrics.append("ToolCallRatio")
        if self.config.enable_solve_rate:
            enabled_metrics.append("SolveRate")
        if self.config.enable_latency_ratio:
            enabled_metrics.append("LatencyRatio")

        # 计算指标
        metric_scores, overall_score = self.metric_calculator.calculate_all(
            execution=execution,
            expected=expected,
            enabled_metrics=enabled_metrics
        )

        # 应用评分器
        scorer_results = []
        for scorer in self.scorers:
            scorer_result = scorer.score(execution, expected)
            scorer_results.append(scorer_result.to_dict())

        # 创建评估结果
        evaluation = EvaluationResult(
            evaluation_id=str(uuid.uuid4()),
            execution_id=execution.execution_id,
            query=execution.query,
            overall_score=overall_score,
            metric_scores=metric_scores,
            agent_execution=execution,
            expected_result=expected,
            scorer_results=scorer_results
        )

        # 如果配置了存储，保存评估结果
        if save_result and self.storage:
            self.storage.save_evaluation(evaluation)

        return evaluation

    def evaluate_with_auto_expected(
        self,
        execution: Optional[AgentExecution] = None,
        context: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
        save_result: bool = True
    ) -> EvaluationResult:
        """
        使用自动生成的预期结果进行评估

        使用LLM自动生成预期结果，然后进行评估。
        这在没有人工标注预期结果的场景下非常有用。

        Args:
            execution: 要评估的执行记录，如果为None则使用最近记录的执行
            context: 额外的上下文信息，用于生成预期结果
            available_tools: 可用工具列表
            save_result: 是否保存评估结果，默认为True

        Returns:
            评估结果对象

        Raises:
            ValueError: 如果没有初始化元数据生成器（需要提供LLM配置）

        Example:
            >>> # 配置中需要提供LLM配置
            >>> config = EvaluationConfig(
            ...     llm_config=LLMConfig(api_key="...")
            ... )
            >>> evaluator = AgentEvaluator(config)
            >>> result = evaluator.evaluate_with_auto_expected(
            ...     context="这是一个天气查询场景"
            ... )
        """
        if execution is None:
            history = self.recorder.get_execution_history()
            if not history:
                raise ValueError("没有提供执行记录且没有历史记录")
            execution = history[-1]

        if self.metadata_generator is None:
            raise ValueError(
                "元数据生成器未初始化。"
                "请在EvaluationConfig中提供llm_config以使用此功能。"
            )

        # 生成预期结果
        expected = self.metadata_generator.generate_expected_result(
            query=execution.query,
            context=context,
            available_tools=available_tools
        )

        return self.evaluate(execution, expected, save_result)

    def batch_evaluate(
        self,
        executions: List[AgentExecution],
        expected_results: Optional[List[ExpectedResult]] = None,
        save_results: bool = True
    ) -> List[EvaluationResult]:
        """
        批量评估多个执行

        对多个执行记录进行批量评估，提高评估效率。

        Args:
            executions: 要评估的执行记录列表
            expected_results: 预期结果列表（可选，长度应与executions相同）
            save_results: 是否保存评估结果，默认为True

        Returns:
            评估结果列表

        Example:
            >>> executions = [exec1, exec2, exec3]
            >>> expected_list = [exp1, exp2, exp3]
            >>> results = evaluator.batch_evaluate(executions, expected_list)
            >>> for result in results:
            ...     print(f"分数: {result.overall_score}")
        """
        results = []
        for i, execution in enumerate(executions):
            expected = expected_results[i] if expected_results and i < len(expected_results) else None
            result = self.evaluate(execution, expected, save_results)
            results.append(result)
        return results

    def get_evaluation_summary(self, evaluations: Optional[List[EvaluationResult]] = None) -> Dict[str, Any]:
        """
        获取评估摘要统计

        计算评估结果的统计信息，包括：
        - 总体分数的平均值、最小值、最大值、中位数
        - 各指标的平均值、最小值、最大值

        Args:
            evaluations: 评估结果列表，如果为None则从存储中读取

        Returns:
            包含统计信息的字典

        Example:
            >>> summary = evaluator.get_evaluation_summary()
            >>> print(f"平均分数: {summary['overall_score']['average']}")
            >>> print(f"评估数量: {summary['total_evaluations']}")
        """
        if evaluations is None:
            if self.storage:
                evaluations = self.storage.list_evaluations(limit=1000)
            else:
                return {"error": "没有提供评估结果且没有配置存储"}

        if not evaluations:
            return {"error": "没有找到评估结果"}

        overall_scores = [e.overall_score for e in evaluations]

        # 计算各指标的平均值
        metric_averages = {}
        metric_names = set()
        for eval_result in evaluations:
            for metric in eval_result.metric_scores:
                metric_names.add(metric.metric_name)

        for metric_name in metric_names:
            scores = [
                e.get_metric_score(metric_name)
                for e in evaluations
                if e.get_metric_score(metric_name) is not None
            ]
            if scores:
                metric_averages[metric_name] = {
                    "average": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores)
                }

        return {
            "total_evaluations": len(evaluations),
            "overall_score": {
                "average": sum(overall_scores) / len(overall_scores),
                "min": min(overall_scores),
                "max": max(overall_scores),
                "median": sorted(overall_scores)[len(overall_scores) // 2]
            },
            "metric_averages": metric_averages
        }

    def generate_expected_result(
        self,
        query: str,
        context: Optional[str] = None,
        available_tools: Optional[List[str]] = None
    ) -> ExpectedResult:
        """
        生成预期结果

        使用LLM为指定查询生成预期结果。

        Args:
            query: 用户查询
            context: 额外的上下文信息
            available_tools: 可用工具列表

        Returns:
            生成的预期结果对象

        Raises:
            ValueError: 如果没有初始化元数据生成器

        Example:
            >>> expected = evaluator.generate_expected_result(
            ...     "北京天气",
            ...     available_tools=["weather_api", "location_parser"]
            ... )
        """
        if self.metadata_generator is None:
            raise ValueError(
                "元数据生成器未初始化。"
                "请在EvaluationConfig中提供llm_config以使用此功能。"
            )
        return self.metadata_generator.generate_expected_result(query, context, available_tools)

    def create_recording_context(self, query: str, metadata: Optional[Dict[str, Any]] = None):
        """
        创建记录上下文管理器

        创建一个上下文管理器，用于自动管理执行记录的生命周期。
        这是推荐的使用方式，可以确保记录正确保存。

        Args:
            query: 用户查询
            metadata: 可选的元数据

        Returns:
            上下文管理器对象

        Example:
            >>> with evaluator.create_recording_context("查询天气") as rec:
            ...     result = agent.run("查询天气")
            ...     rec.set_output(result)
            >>> # 退出上下文后，记录自动保存
        """
        return self.recorder.record(query, metadata)

    def evaluate_from_storage(
        self,
        query: str,
        execution_id: Optional[str] = None,
        save_result: bool = True
    ) -> EvaluationResult:
        """
        从存储中加载数据进行评估

        从存储中加载预期执行和实际执行，然后进行评估。
        这在批量评估已存储的执行记录时非常有用。

        Args:
            query: 用户查询
            execution_id: 特定执行ID（可选，如果不提供则使用最新的执行）
            save_result: 是否保存评估结果，默认为True

        Returns:
            评估结果对象

        Raises:
            ValueError: 如果没有配置存储
            ValueError: 如果没有找到预期执行或实际执行

        Example:
            >>> result = evaluator.evaluate_from_storage("北京天气")
            >>> print(f"评估ID: {result.evaluation_id}")
        """
        if not self.storage:
            raise ValueError("未配置存储")
        
        # 从存储中获取预期执行
        from agent_eval.generators import GeneratedExpectedExecution
        expected_data = self.storage.get_expected_execution(query)
        
        if not expected_data:
            raise ValueError(f"未找到查询的预期执行: {query}")
        
        # 获取实际执行
        if execution_id:
            actual_execution = self.storage.get_execution(execution_id)
        else:
            # 获取该查询的最新执行
            executions = self.storage.list_executions(limit=100)
            actual_execution = None
            for exec in reversed(executions):
                if exec.query == query:
                    actual_execution = exec
                    break
        
        if not actual_execution:
            raise ValueError(f"未找到查询的实际执行: {query}")
        
        # 转换为ExpectedResult并评估
        expected_result = expected_data.to_expected_result()
        return self.evaluate(actual_execution, expected_result, save_result)

    def batch_evaluate_from_storage(
        self,
        queries: Optional[List[str]] = None,
        save_results: bool = True
    ) -> List[EvaluationResult]:
        """
        从存储中批量评估多个查询

        批量评估存储中的多个查询，自动匹配预期执行和实际执行。

        Args:
            queries: 要评估的查询列表（可选，如果为None则评估所有）
            save_results: 是否保存评估结果，默认为True

        Returns:
            评估结果列表

        Raises:
            ValueError: 如果没有配置存储
            ValueError: 如果没有找到预期执行

        Example:
            >>> queries = ["北京天气", "上海天气", "广州天气"]
            >>> results = evaluator.batch_evaluate_from_storage(queries)
            >>> print(f"评估了 {len(results)} 个查询")
        """
        if not self.storage:
            raise ValueError("未配置存储")
        
        # 获取预期执行
        if queries:
            expected_executions = []
            for query in queries:
                expected = self.storage.get_expected_execution(query)
                if expected:
                    expected_executions.append(expected)
        else:
            expected_executions = self.storage.list_expected_executions(limit=1000)
        
        if not expected_executions:
            raise ValueError("在存储中未找到预期执行")
        
        # 评估每个查询
        results = []
        for expected in expected_executions:
            # 查找匹配的实际执行
            all_executions = self.storage.list_executions(limit=1000)
            actual = None
            for exec in reversed(all_executions):
                if exec.query == expected.query:
                    actual = exec
                    break
            
            if actual:
                expected_result = expected.to_expected_result()
                result = self.evaluate(actual, expected_result, save_results)
                results.append(result)
        
        return results

    def generate_and_save_expected(
        self,
        query: str,
        available_tools: Optional[List[Any]] = None,
        context: Optional[str] = None
    ) -> Any:  # GeneratedExpectedExecution
        """
        生成并保存预期执行

        使用LLM生成预期执行并保存到存储中，用于后续的对比评估。

        Args:
            query: 用户查询
            available_tools: 可用工具列表（带描述）
            context: 额外的上下文信息

        Returns:
            生成的预期执行对象

        Raises:
            ValueError: 如果没有初始化元数据生成器
            ValueError: 如果没有配置存储

        Example:
            >>> expected = evaluator.generate_and_save_expected(
            ...     "北京天气",
            ...     available_tools=[{"name": "weather_api", "description": "获取天气"}],
            ...     context="天气查询场景"
            ... )
            >>> print(f"预期步骤: {expected.expected_steps}")
        """
        if not self.metadata_generator:
            raise ValueError(
                "元数据生成器未初始化。"
                "请在EvaluationConfig中提供llm_config。"
            )
        
        if not self.storage:
            raise ValueError("未配置存储")
        
        # 生成预期执行
        expected = self.metadata_generator.generate_expected_execution(
            query=query,
            available_tools=available_tools,
            context=context
        )
        
        # 保存到存储
        self.storage.save_expected_execution(expected)
        
        return expected

    def get_execution_history(self) -> List[AgentExecution]:
        """
        获取执行历史

        获取内存中的执行历史记录（非持久化存储中的）。

        Returns:
            执行记录列表

        Example:
            >>> history = evaluator.get_execution_history()
            >>> print(f"共 {len(history)} 条记录")
        """
        return self.recorder.get_execution_history()

    def get_stored_executions(self, limit: int = 100) -> List[AgentExecution]:
        """
        获取存储中的执行记录

        从持久化存储中获取执行记录。

        Args:
            limit: 最大返回数量，默认100

        Returns:
            执行记录列表

        Example:
            >>> executions = evaluator.get_stored_executions(limit=10)
            >>> for exec in executions:
            ...     print(f"{exec.query}: {exec.success}")
        """
        if self.storage:
            return self.storage.list_executions(limit)
        return []

    def get_stored_evaluations(self, limit: int = 100) -> List[EvaluationResult]:
        """
        获取存储中的评估结果

        从持久化存储中获取评估结果。

        Args:
            limit: 最大返回数量，默认100

        Returns:
            评估结果列表

        Example:
            >>> evaluations = evaluator.get_stored_evaluations(limit=10)
            >>> avg_score = sum(e.overall_score for e in evaluations) / len(evaluations)
        """
        if self.storage:
            return self.storage.list_evaluations(limit)
        return []


# =============================================================================
# 便捷函数 - 用于快速使用
# =============================================================================

def create_evaluator(
    storage_type: str = "json",
    file_path: Optional[str] = None,
    llm_config: Optional[LLMConfig] = None
) -> AgentEvaluator:
    """
    创建评估器（简化配置）

    使用简单的参数创建评估器，适合快速开始。

    Args:
        storage_type: 存储类型（json, csv, sqlite, postgres）
        file_path: 文件存储路径
        llm_config: LLM配置（用于LLM评分和预期结果生成）

    Returns:
        配置好的AgentEvaluator实例

    Example:
        >>> evaluator = create_evaluator(
        ...     storage_type="sqlite",
        ...     file_path="evaluations.db"
        ... )
    """
    from agent_eval.models import StorageType

    config = EvaluationConfig(
        storage_config=StorageConfig(
            storage_type=StorageType(storage_type),
            file_path=file_path
        ),
        llm_config=llm_config
    )

    return AgentEvaluator(config)


def quick_evaluate(
    execution: AgentExecution,
    expected: Optional[ExpectedResult] = None
) -> EvaluationResult:
    """
    快速评估（无持久化存储）

    对单个执行进行快速评估，不使用持久化存储。
    适合临时评估或测试场景。

    Args:
        execution: 要评估的执行记录
        expected: 可选的预期结果

    Returns:
        评估结果

    Example:
        >>> execution = create_execution_record(...)
        >>> result = quick_evaluate(execution)
        >>> print(f"分数: {result.overall_score}")
    """
    evaluator = AgentEvaluator(
        EvaluationConfig(auto_record=False)
    )
    return evaluator.evaluate(execution, expected, save_result=False)
