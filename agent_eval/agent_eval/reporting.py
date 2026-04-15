"""
评估报告生成模块 - 支持生成单条和批量评估报告

本模块提供完整的报告生成功能，支持多种报告类型：
- 单条评估报告：详细展示单个执行的评估结果
- 批量评估报告：汇总展示多个执行的评估统计信息
- 对比报告：对比预期执行与实际执行的差异

支持多种输出格式：
- JSON格式：完整的结构化数据
- CSV格式：适合批量评估的表格数据

主要组件：
- ReportGenerator: 报告生成器，支持多种报告类型
- EvaluationPipeline: 评估流水线，整合存储、评估和报告生成

使用示例：
    # 生成单条评估报告
    report_gen = ReportGenerator(storage)
    report = report_gen.generate_single_report(
        execution=execution,
        evaluation=evaluation,
        expected=expected,
        output_path="report.json"
    )
    
    # 生成批量评估报告
    batch_report = report_gen.generate_batch_report(
        evaluations=evaluations,
        output_path="batch_report.json"
    )
    
    # 使用评估流水线
    pipeline = EvaluationPipeline(storage, evaluator)
    report = pipeline.evaluate_from_storage("什么是AI？")
"""

import json
import csv
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_eval.models import AgentExecution, EvaluationResult, ExpectedResult
from agent_eval.storages import BaseStorage, create_storage, StorageConfig, StorageType


# =============================================================================
# 报告生成器类
# =============================================================================

class ReportGenerator:
    """
    评估报告生成器 - 从执行和评估数据生成报告
    
    支持生成三种类型的报告：
    1. 单条评估报告：展示单个执行的完整评估信息
    2. 批量评估报告：汇总多个执行的统计信息
    3. 对比报告：对比预期执行与实际执行的差异
    
    Attributes:
        storage: 存储后端实例，用于获取执行数据
    
    Example:
        >>> report_gen = ReportGenerator(storage=my_storage)
        >>> 
        >>> # 单条报告
        >>> report = report_gen.generate_single_report(
        ...     execution=execution,
        ...     evaluation=evaluation,
        ...     output_path="single_report.json"
        ... )
        >>> 
        >>> # 批量报告
        >>> batch_report = report_gen.generate_batch_report(
        ...     evaluations=evaluations,
        ...     output_path="batch_report.json"
        ... )
    """
    
    def __init__(self, storage: Optional[BaseStorage] = None):
        """
        初始化报告生成器
        
        Args:
            storage: 可选的存储后端实例，用于获取执行数据
        """
        self.storage = storage
    
    def generate_single_report(
        self,
        execution: AgentExecution,
        evaluation: EvaluationResult,
        expected: Optional[ExpectedResult] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成单条评估报告
        
        生成包含执行详情、评估结果和预期结果的完整报告。
        
        Args:
            execution: 实际智能体执行记录
            evaluation: 评估结果对象
            expected: 预期结果对象（可选）
            output_path: 报告保存路径（可选）
            
        Returns:
            报告数据字典
            
        Example:
            >>> report = report_gen.generate_single_report(
            ...     execution=execution,
            ...     evaluation=evaluation,
            ...     expected=expected_result,
            ...     output_path="report.json"
            ... )
            >>> print(f"总分: {report['evaluation_result']['overall_score']}")
        """
        report = {
            "report_type": "single_evaluation",
            "generated_at": datetime.now().isoformat(),
            "evaluation": {
                "execution_id": execution.execution_id,
                "query": execution.query,
                "final_output": execution.final_output,
                "success": execution.success,
                "has_error": execution.has_error,
                "error_message": execution.error_message,
                "step_count": execution.step_count,
                "tool_call_count": execution.tool_call_count,
                "total_duration_ms": execution.total_duration_ms,
                "steps_summary": execution.steps_summary,
                "steps_detail": [s.model_dump() for s in execution.steps_detail],
                "tool_calls_detail": [t.model_dump() for t in execution.tool_calls_detail],
            },
            "expected": expected.model_dump() if expected else None,
            "evaluation_result": {
                "evaluation_id": evaluation.evaluation_id,
                "overall_score": evaluation.overall_score,
                "metric_scores": [
                    {
                        "metric_name": m.metric_name,
                        "score": m.score,
                        "weight": m.weight,
                        "details": m.details
                    }
                    for m in evaluation.metric_scores
                ]
            }
        }
        
        # 如果提供了路径，保存报告
        if output_path:
            self._save_report(report, output_path)
        
        return report
    
    def generate_batch_report(
        self,
        evaluations: List[EvaluationResult],
        executions: Optional[List[AgentExecution]] = None,
        expected_results: Optional[List[ExpectedResult]] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成批量评估报告
        
        汇总多个评估结果，生成统计信息和分布分析。
        
        Args:
            evaluations: 评估结果列表
            executions: 执行记录列表（可选，如果配置了存储会自动获取）
            expected_results: 预期结果列表（可选）
            output_path: 报告保存路径（可选）
            
        Returns:
            批量报告数据字典
            
        Example:
            >>> batch_report = report_gen.generate_batch_report(
            ...     evaluations=evaluations,
            ...     output_path="batch_report.json"
            ... )
            >>> print(f"平均得分: {batch_report['summary']['average_overall_score']}")
        """
        # 如果未提供执行记录但配置了存储，从存储中获取
        if executions is None and self.storage:
            executions = []
            for eval_result in evaluations:
                exec_data = self.storage.get_execution(eval_result.execution_id)
                if exec_data:
                    executions.append(exec_data)
        
        # 计算汇总统计信息
        total_evaluations = len(evaluations)
        overall_scores = [e.overall_score for e in evaluations]
        avg_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        
        # 计算每个指标的统计信息
        metric_stats = {}
        for evaluation in evaluations:
            for metric_score in evaluation.metric_scores:
                metric_name = metric_score.metric_name
                if metric_name not in metric_stats:
                    metric_stats[metric_name] = {
                        "scores": [],
                        "weight": metric_score.weight
                    }
                metric_stats[metric_name]["scores"].append(metric_score.score)
        
        for metric_name, stats in metric_stats.items():
            scores = stats["scores"]
            stats["average"] = sum(scores) / len(scores) if scores else 0
            stats["min"] = min(scores) if scores else 0
            stats["max"] = max(scores) if scores else 0
            del stats["scores"]  # 删除原始分数列表以保持报告简洁
        
        # 构建单个评估摘要
        individual_results = []
        for i, evaluation in enumerate(evaluations):
            exec_data = executions[i] if executions and i < len(executions) else None
            expected_data = expected_results[i] if expected_results and i < len(expected_results) else None
            
            result_summary = {
                "execution_id": evaluation.execution_id,
                "query": evaluation.query,
                "overall_score": evaluation.overall_score,
                "success": exec_data.success if exec_data else None,
                "step_count": exec_data.step_count if exec_data else None,
                "tool_call_count": exec_data.tool_call_count if exec_data else None,
            }
            individual_results.append(result_summary)
        
        report = {
            "report_type": "batch_evaluation",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_evaluations": total_evaluations,
                "average_overall_score": avg_score,
                "score_distribution": self._calculate_score_distribution(overall_scores),
            },
            "metric_statistics": metric_stats,
            "individual_results": individual_results,
            "detailed_evaluations": [
                {
                    "evaluation_id": e.evaluation_id,
                    "execution_id": e.execution_id,
                    "query": e.query,
                    "overall_score": e.overall_score,
                    "metric_scores": [
                        {
                            "metric_name": m.metric_name,
                            "score": m.score,
                            "weight": m.weight
                        }
                        for m in e.metric_scores
                    ]
                }
                for e in evaluations
            ]
        }
        
        # 如果提供了路径，保存报告
        if output_path:
            self._save_report(report, output_path)
        
        return report
    
    def generate_comparison_report(
        self,
        query: str,
        expected_execution: Any,  # GeneratedExpectedExecution
        actual_execution: AgentExecution,
        evaluation: EvaluationResult,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成预期与实际执行的对比报告
        
        详细对比LLM生成的预期执行与实际执行的差异，包括步骤数、工具调用数、
        输出内容等方面的对比。
        
        Args:
            query: 用户查询字符串
            expected_execution: 预期（理想）执行记录
            actual_execution: 实际智能体执行记录
            evaluation: 评估结果
            output_path: 报告保存路径（可选）
            
        Returns:
            对比报告数据字典
            
        Example:
            >>> comparison_report = report_gen.generate_comparison_report(
            ...     query="什么是AI？",
            ...     expected_execution=expected,
            ...     actual_execution=actual,
            ...     evaluation=evaluation,
            ...     output_path="comparison.json"
            ... )
        """
        report = {
            "report_type": "comparison",
            "generated_at": datetime.now().isoformat(),
            "query": query,
            "comparison": {
                "expected": {
                    "output": expected_execution.expected_output,
                    "step_count": expected_execution.step_count,
                    "tool_call_count": expected_execution.tool_call_count,
                    "steps": [s.model_dump() for s in expected_execution.steps_detail],
                    "tool_calls": [t.model_dump() for t in expected_execution.tool_calls_detail],
                    "duration_ms": expected_execution.expected_duration_ms,
                },
                "actual": {
                    "output": actual_execution.final_output,
                    "step_count": actual_execution.step_count,
                    "tool_call_count": actual_execution.tool_call_count,
                    "steps": [s.model_dump() for s in actual_execution.steps_detail],
                    "tool_calls": [t.model_dump() for t in actual_execution.tool_calls_detail],
                    "duration_ms": actual_execution.total_duration_ms,
                    "success": actual_execution.success,
                    "has_error": actual_execution.has_error,
                },
                "differences": self._calculate_differences(
                    expected_execution, actual_execution
                )
            },
            "evaluation": {
                "overall_score": evaluation.overall_score,
                "metric_scores": [
                    {
                        "metric_name": m.metric_name,
                        "score": m.score,
                        "weight": m.weight,
                        "details": m.details
                    }
                    for m in evaluation.metric_scores
                ]
            }
        }
        
        # 如果提供了路径，保存报告
        if output_path:
            self._save_report(report, output_path)
        
        return report
    
    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """
        计算分数分布
        
        将分数按等级分类统计：优秀(90-100%)、良好(70-89%)、一般(50-69%)、较差(0-49%)
        
        Args:
            scores: 分数列表
            
        Returns:
            各等级的数量分布字典
        """
        distribution = {
            "excellent (90-100%)": 0,
            "good (70-89%)": 0,
            "fair (50-69%)": 0,
            "poor (0-49%)": 0
        }
        
        for score in scores:
            if score >= 0.9:
                distribution["excellent (90-100%)"] += 1
            elif score >= 0.7:
                distribution["good (70-89%)"] += 1
            elif score >= 0.5:
                distribution["fair (50-69%)"] += 1
            else:
                distribution["poor (0-49%)"] += 1
        
        return distribution
    
    def _calculate_differences(
        self,
        expected: Any,  # GeneratedExpectedExecution
        actual: AgentExecution
    ) -> Dict[str, Any]:
        """
        计算预期执行与实际执行的差异
        
        计算步骤数差异、工具调用数差异、耗时差异和输出相似度。
        
        Args:
            expected: 预期执行记录
            actual: 实际执行记录
            
        Returns:
            差异分析字典
        """
        differences = {
            "step_count_diff": actual.step_count - expected.step_count,
            "tool_call_count_diff": actual.tool_call_count - expected.tool_call_count,
            "duration_diff_ms": None,
            "output_similarity": None
        }
        
        if expected.expected_duration_ms and actual.total_duration_ms:
            differences["duration_diff_ms"] = actual.total_duration_ms - expected.expected_duration_ms
        
        # 简单的输出对比（可以使用文本相似度算法增强）
        if expected.expected_output and actual.final_output:
            expected_words = set(expected.expected_output.lower().split())
            actual_words = set(actual.final_output.lower().split())
            if expected_words:
                intersection = expected_words & actual_words
                differences["output_similarity"] = len(intersection) / len(expected_words)
        
        return differences
    
    def _save_report(self, report: Dict[str, Any], output_path: str):
        """
        保存报告到文件
        
        支持JSON和CSV两种格式，根据文件扩展名自动选择。
        
        Args:
            report: 报告数据字典
            output_path: 保存路径
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        def json_serial(obj):
            """JSON序列化器，处理datetime等特殊类型"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        if path.suffix == '.json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=json_serial)
        elif path.suffix == '.csv':
            self._save_report_csv(report, path)
        else:
            # 默认使用JSON格式
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=json_serial)
    
    def _save_report_csv(self, report: Dict[str, Any], path: Path):
        """
        以CSV格式保存报告
        
        主要用于批量评估报告，生成表格形式的数据。
        
        Args:
            report: 报告数据字典
            path: 保存路径
        """
        if report.get("report_type") == "batch_evaluation":
            # 写入汇总信息
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Total Evaluations', report['summary']['total_evaluations']])
                writer.writerow(['Average Score', f"{report['summary']['average_overall_score']:.2%}"])
                writer.writerow([])
                
                # 写入指标统计信息
                writer.writerow(['Metric Name', 'Average', 'Min', 'Max', 'Weight'])
                for metric_name, stats in report['metric_statistics'].items():
                    writer.writerow([
                        metric_name,
                        f"{stats['average']:.2%}",
                        f"{stats['min']:.2%}",
                        f"{stats['max']:.2%}",
                        stats['weight']
                    ])
                writer.writerow([])
                
                # 写入单个结果
                writer.writerow(['Execution ID', 'Query', 'Overall Score', 'Success', 'Steps', 'Tool Calls'])
                for result in report['individual_results']:
                    writer.writerow([
                        result['execution_id'],
                        result['query'],
                        f"{result['overall_score']:.2%}",
                        result['success'],
                        result['step_count'],
                        result['tool_call_count']
                    ])


# =============================================================================
# 评估流水线类
# =============================================================================

class EvaluationPipeline:
    """
    完整评估流水线
    
    整合存储、评估和报告生成，提供从存储加载数据到生成报告的完整流程：
    1. 从存储加载预期结果（或生成新的预期结果）
    2. 从存储加载实际执行记录
    3. 执行评估
    4. 生成报告
    
    Attributes:
        storage: 存储后端实例
        evaluator: 评估器实例（AgentEvaluator）
        report_generator: 报告生成器实例
    
    Example:
        >>> pipeline = EvaluationPipeline(storage, evaluator)
        >>> 
        >>> # 单条评估
        >>> report = pipeline.evaluate_from_storage("什么是AI？")
        >>> 
        >>> # 批量评估
        >>> batch_report = pipeline.batch_evaluate_from_storage(
        ...     queries=["什么是AI？", "什么是机器学习？"]
        ... )
    """
    
    def __init__(
        self,
        storage: BaseStorage,
        evaluator: Any  # AgentEvaluator
    ):
        """
        初始化评估流水线
        
        Args:
            storage: 存储后端实例
            evaluator: 评估器实例（AgentEvaluator）
        """
        self.storage = storage
        self.evaluator = evaluator
        self.report_generator = ReportGenerator(storage)
    
    def evaluate_from_storage(
        self,
        query: str,
        execution_id: Optional[str] = None,
        save_report: bool = True,
        report_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从存储加载数据并执行单条评估
        
        根据查询字符串从存储中获取预期执行和实际执行，执行评估并生成报告。
        
        Args:
            query: 用户查询字符串
            execution_id: 特定执行ID（可选，不提供则使用最新的）
            save_report: 是否保存报告
            report_path: 报告保存路径
            
        Returns:
            评估报告字典
            
        Raises:
            ValueError: 如果找不到预期执行或实际执行
            
        Example:
            >>> pipeline = EvaluationPipeline(storage, evaluator)
            >>> report = pipeline.evaluate_from_storage("什么是AI？")
            >>> print(f"得分: {report['evaluation']['overall_score']}")
        """
        # 获取预期执行
        from agent_eval.generators import GeneratedExpectedExecution
        expected_data = self.storage.get_expected_execution(query)
        
        if not expected_data:
            raise ValueError(f"No expected execution found for query: {query}")
        
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
            raise ValueError(f"No actual execution found for query: {query}")
        
        # 转换预期结果为ExpectedResult格式
        expected_result = expected_data.to_expected_result()
        
        # 执行评估
        evaluation = self.evaluator.evaluate(
            actual_execution,
            expected_result,
            save_result=True
        )
        
        # 生成报告
        if not report_path:
            report_path = f"reports/evaluation_{actual_execution.execution_id}.json"
        
        report = self.report_generator.generate_comparison_report(
            query=query,
            expected_execution=expected_data,
            actual_execution=actual_execution,
            evaluation=evaluation,
            output_path=report_path if save_report else None
        )
        
        return report
    
    def batch_evaluate_from_storage(
        self,
        queries: Optional[List[str]] = None,
        save_report: bool = True,
        report_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从存储批量加载数据并执行评估
        
        批量评估多个查询，生成汇总报告。
        
        Args:
            queries: 要评估的查询列表（可选，不提供则评估所有）
            save_report: 是否保存报告
            report_path: 报告保存路径
            
        Returns:
            批量评估报告字典
            
        Raises:
            ValueError: 如果找不到预期执行或匹配的执行记录
            
        Example:
            >>> pipeline = EvaluationPipeline(storage, evaluator)
            >>> batch_report = pipeline.batch_evaluate_from_storage(
            ...     queries=["什么是AI？", "什么是机器学习？"]
            ... )
            >>> print(f"平均得分: {batch_report['summary']['average_overall_score']}")
        """
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
            raise ValueError("No expected executions found in storage")
        
        # 获取实际执行并评估
        evaluations = []
        executions = []
        expected_results = []
        
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
                evaluation = self.evaluator.evaluate(
                    actual,
                    expected_result,
                    save_result=True
                )
                evaluations.append(evaluation)
                executions.append(actual)
                expected_results.append(expected_result)
        
        if not evaluations:
            raise ValueError("No matching executions found for evaluation")
        
        # 生成批量报告
        if not report_path:
            report_path = f"reports/batch_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.report_generator.generate_batch_report(
            evaluations=evaluations,
            executions=executions,
            expected_results=expected_results,
            output_path=report_path if save_report else None
        )
        
        return report


# =============================================================================
# 便捷函数
# =============================================================================

def generate_report_from_files(
    expected_file: str,
    actual_file: str,
    output_path: str,
    report_type: str = "comparison"
) -> Dict[str, Any]:
    """
    从JSON文件生成报告
    
    从包含预期结果和实际执行的JSON文件加载数据，生成报告。
    
    Args:
        expected_file: 预期结果JSON文件路径
        actual_file: 实际执行JSON文件路径
        output_path: 报告保存路径
        report_type: 报告类型（comparison对比报告, batch批量报告）
        
    Returns:
        报告数据字典
        
    Example:
        >>> report = generate_report_from_files(
        ...     expected_file="expected.json",
        ...     actual_file="actual.json",
        ...     output_path="report.json",
        ...     report_type="comparison"
        ... )
    """
    # 加载预期数据
    with open(expected_file, 'r', encoding='utf-8') as f:
        expected_data = json.load(f)
    
    # 加载实际数据
    with open(actual_file, 'r', encoding='utf-8') as f:
        actual_data = json.load(f)
    
    report_generator = ReportGenerator()
    
    if report_type == "comparison" and isinstance(expected_data, dict) and isinstance(actual_data, dict):
        # 单条对比报告
        from agent_eval.generators import GeneratedExpectedExecution
        expected = GeneratedExpectedExecution.from_dict(expected_data)
        actual = AgentExecution(**actual_data)
        
        # 创建模拟的评估结果
        evaluation = EvaluationResult(
            evaluation_id="manual",
            execution_id=actual.execution_id,
            query=actual.query,
            overall_score=0.0,
            agent_execution=actual,
            expected_result=expected.to_expected_result()
        )
        
        report = report_generator.generate_comparison_report(
            query=actual.query,
            expected_execution=expected,
            actual_execution=actual,
            evaluation=evaluation,
            output_path=output_path
        )
    else:
        # 批量报告
        evaluations = [EvaluationResult(**e) for e in actual_data.get("evaluations", [])]
        report = report_generator.generate_batch_report(
            evaluations=evaluations,
            output_path=output_path
        )
    
    return report
