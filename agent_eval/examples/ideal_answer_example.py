"""
Example: Generate ideal answers using LLM and evaluate against actual execution
演示如何使用大模型生成理想回答，并与真实执行进行对比评分
"""

import asyncio
from agent_eval import AgentEvaluator, EvaluationConfig, LLMConfig, StorageConfig, StorageType
from agent_eval.generators import ToolInfo


# 定义可用工具（用于生成理想回答时参考）
AVAILABLE_TOOLS = [
    ToolInfo(
        name="search",
        description="搜索互联网获取信息",
        parameters={"query": "搜索关键词"}
    ),
    ToolInfo(
        name="calculator",
        description="执行数学计算",
        parameters={"expression": "数学表达式"}
    ),
    ToolInfo(
        name="weather",
        description="获取指定城市的天气信息",
        parameters={"city": "城市名称"}
    ),
    ToolInfo(
        name="translate",
        description="翻译文本",
        parameters={"text": "待翻译文本", "target_lang": "目标语言"}
    )
]


def example_1_generate_ideal_answer():
    """示例1: 生成单个问题的理想回答并保存"""
    print("=" * 60)
    print("示例1: 生成单个问题的理想回答")
    print("=" * 60)
    
    # 配置
    config = EvaluationConfig(
        llm_config=LLMConfig(
            model="gpt-4",
            api_key="your-api-key",  # 替换为实际的API密钥
            base_url=None  # 可选：自定义API端点
        ),
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="data/ideal_answers.json"
        ),
        auto_record=True
    )
    
    # 创建评估器
    evaluator = AgentEvaluator(config)
    
    # 用户问题
    query = "计算 123 * 456 的结果，并告诉我今天的天气"
    
    # 生成理想回答（不调用真实工具）
    print(f"\n问题: {query}")
    print("\n正在生成理想回答...")
    
    expected = evaluator.generate_and_save_expected(
        query=query,
        available_tools=AVAILABLE_TOOLS,
        context="用户需要计算乘法并获取天气信息"
    )
    
    # 显示生成的理想回答
    print(f"\n理想回答已生成并保存!")
    print(f"预期输出: {expected.expected_output[:100]}...")
    print(f"执行步骤数: {expected.step_count}")
    print(f"工具调用数: {expected.tool_call_count}")
    print(f"\n详细步骤:")
    for step in expected.steps_detail:
        print(f"  步骤 {step.step_number}: {step.description}")
    print(f"\n工具调用顺序:")
    for tool in expected.tool_calls_detail:
        print(f"  - {tool.name}: {tool.description}")


def example_2_batch_generate_ideal_answers():
    """示例2: 批量生成理想回答"""
    print("\n" + "=" * 60)
    print("示例2: 批量生成理想回答")
    print("=" * 60)
    
    config = EvaluationConfig(
        llm_config=LLMConfig(
            model="gpt-4",
            api_key="your-api-key"
        ),
        storage_config=StorageConfig(
            storage_type=StorageType.SQLITE,
            file_path="data/evaluations.db"
        )
    )
    
    evaluator = AgentEvaluator(config)
    
    # 批量问题
    queries = [
        "搜索 Python 编程最佳实践",
        "计算 (100 + 200) * 3",
        "翻译 'Hello World' 为中文",
        "查询北京今天的天气"
    ]
    
    print(f"\n批量生成 {len(queries)} 个问题的理想回答...")
    
    for query in queries:
        print(f"\n处理: {query}")
        expected = evaluator.generate_and_save_expected(
            query=query,
            available_tools=AVAILABLE_TOOLS
        )
        print(f"  ✓ 已生成 - 步骤: {expected.step_count}, 工具调用: {expected.tool_call_count}")
    
    print(f"\n所有理想回答已保存到 SQLite 数据库")


def example_3_evaluate_with_ideal_answer():
    """示例3: 使用理想回答评估真实执行"""
    print("\n" + "=" * 60)
    print("示例3: 使用理想回答评估真实执行")
    print("=" * 60)
    
    from agent_eval.tracker import ExecutionTracker
    
    config = EvaluationConfig(
        llm_config=LLMConfig(
            model="gpt-4",
            api_key="your-api-key"
        ),
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="data/evaluations.json"
        ),
        enable_correctness=True,
        enable_step_ratio=True,
        enable_tool_call_ratio=True,
        enable_solve_rate=True,
        enable_latency_ratio=True
    )
    
    evaluator = AgentEvaluator(config)
    
    # 步骤1: 生成理想回答
    query = "计算 100 + 200"
    print(f"\n问题: {query}")
    
    print("\n步骤1: 生成理想回答...")
    expected = evaluator.generate_and_save_expected(
        query=query,
        available_tools=AVAILABLE_TOOLS
    )
    print(f"理想回答生成完成:")
    print(f"  - 预期步骤: {expected.step_count}")
    print(f"  - 预期工具调用: {expected.tool_call_count}")
    
    # 步骤2: 模拟真实执行（使用 ExecutionTracker 记录）
    print("\n步骤2: 模拟真实执行并记录...")
    
    tracker = ExecutionTracker()
    
    with tracker.track(query) as exec:
        # 模拟执行步骤
        exec.add_step(1, "理解用户问题", input_data=query)
        exec.add_step(2, "调用计算器工具", input_data={"expression": "100 + 200"})
        exec.add_tool_call(
            name="calculator",
            input_data={"expression": "100 + 200"},
            output_data={"result": 300},
            duration_ms=150,
            success=True
        )
        exec.add_step(3, "返回计算结果", output_data="300")
        exec.set_final_output("100 + 200 = 300")
    
    actual_execution = tracker.get_execution()
    print(f"真实执行记录完成:")
    print(f"  - 实际步骤: {actual_execution.step_count}")
    print(f"  - 实际工具调用: {actual_execution.tool_call_count}")
    
    # 保存真实执行
    if evaluator.storage:
        evaluator.storage.save_execution(actual_execution)
    
    # 步骤3: 从存储读取并评估
    print("\n步骤3: 评估真实执行 vs 理想回答...")
    
    evaluation = evaluator.evaluate_from_storage(query=query)
    
    print(f"\n评估结果:")
    print(f"  总分: {evaluation.overall_score:.2%}")
    print(f"\n  各指标得分:")
    for metric in evaluation.metric_scores:
        print(f"    - {metric.metric_name}: {metric.score:.2%} (权重: {metric.weight})")


def example_4_generate_report():
    """示例4: 生成评估报告"""
    print("\n" + "=" * 60)
    print("示例4: 生成评估报告")
    print("=" * 60)
    
    from agent_eval.reporting import ReportGenerator, EvaluationPipeline
    
    config = EvaluationConfig(
        llm_config=LLMConfig(
            model="gpt-4",
            api_key="your-api-key"
        ),
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="data/evaluations.json"
        )
    )
    
    evaluator = AgentEvaluator(config)
    pipeline = EvaluationPipeline(
        storage=evaluator.storage,
        evaluator=evaluator
    )
    
    # 生成单条评估报告
    query = "计算 100 + 200"
    print(f"\n生成单条评估报告: {query}")
    
    try:
        report = pipeline.evaluate_from_storage(
            query=query,
            save_report=True,
            report_path="reports/single_evaluation.json"
        )
        
        print(f"报告已保存到: reports/single_evaluation.json")
        print(f"报告内容摘要:")
        print(f"  - 问题: {report['query']}")
        print(f"  - 总分: {report['evaluation']['overall_score']:.2%}")
        
    except ValueError as e:
        print(f"注意: {e}")
        print("请先运行示例3生成必要的评估数据")
    
    # 生成批量评估报告
    print("\n生成批量评估报告...")
    
    try:
        batch_report = pipeline.batch_evaluate_from_storage(
            save_report=True,
            report_path="reports/batch_evaluation.json"
        )
        
        print(f"批量报告已保存到: reports/batch_evaluation.json")
        print(f"报告摘要:")
        print(f"  - 总评估数: {batch_report['summary']['total_evaluations']}")
        print(f"  - 平均分: {batch_report['summary']['average_overall_score']:.2%}")
        print(f"  - 分数分布: {batch_report['summary']['score_distribution']}")
        
    except ValueError as e:
        print(f"注意: {e}")
        print("请先运行示例2和示例3生成必要的评估数据")


def example_5_compare_expected_vs_actual():
    """示例5: 详细对比理想回答和真实执行"""
    print("\n" + "=" * 60)
    print("示例5: 详细对比理想回答和真实执行")
    print("=" * 60)
    
    from agent_eval.reporting import ReportGenerator
    from agent_eval.generators import GeneratedExpectedExecution, StepDetail, ToolCallDetail
    from agent_eval.models import AgentExecution, StepDetail as ActualStepDetail, ToolCallDetail as ActualToolCallDetail
    
    # 创建理想回答
    expected = GeneratedExpectedExecution(
        query="计算 100 + 200",
        expected_output="100 + 200 = 300",
        steps_detail=[
            StepDetail(step=1, description="解析用户输入", input_data="计算 100 + 200"),
            StepDetail(step=2, description="调用计算器", input_data={"expression": "100 + 200"}),
            StepDetail(step=3, description="返回结果", output_data="300")
        ],
        tool_calls_detail=[
            ToolCallDetail(name="calculator", description="执行计算", input_data={"expression": "100 + 200"})
        ],
        step_count=3,
        tool_call_count=1,
        expected_duration_ms=500,
        reasoning="这是一个简单的数学计算问题，需要调用计算器工具"
    )
    
    # 创建真实执行（模拟略有不同的执行路径）
    actual = AgentExecution(
        execution_id="exec-001",
        query="计算 100 + 200",
        steps_summary="第一步执行解析\n第二步执行计算\n第三步返回结果",
        steps_detail=[
            ActualStepDetail(step=1, description="解析用户输入", input_data="计算 100 + 200", time=50, success=True),
            ActualStepDetail(step=2, description="验证输入格式", input_data="100 + 200", time=30, success=True),
            ActualStepDetail(step=3, description="调用计算器", input_data={"expression": "100 + 200"}, time=150, success=True),
            ActualStepDetail(step=4, description="格式化输出", output_data="300", time=20, success=True)
        ],
        tool_calls_detail=[
            ActualToolCallDetail(name="calculator", input_data={"expression": "100 + 200"}, output_data={"result": 300}, time=150, success=True)
        ],
        step_count=4,
        tool_call_count=1,
        final_output="100 + 200 = 300",
        success=True,
        has_error=False,
        total_duration_ms=650
    )
    
    # 生成对比报告
    report_gen = ReportGenerator()
    
    from agent_eval.models import EvaluationResult, MetricScore, ExpectedResult
    evaluation = EvaluationResult(
        evaluation_id="eval-001",
        execution_id="exec-001",
        query="计算 100 + 200",
        overall_score=0.85,
        metric_scores=[
            MetricScore(metric_name="Correctness", score=1.0, weight=0.3),
            MetricScore(metric_name="StepRatio", score=0.75, weight=0.2, details={"expected_steps": 3, "actual_steps": 4}),
            MetricScore(metric_name="ToolCallRatio", score=1.0, weight=0.2),
            MetricScore(metric_name="SolveRate", score=1.0, weight=0.15),
            MetricScore(metric_name="LatencyRatio", score=0.77, weight=0.15, details={"expected_ms": 500, "actual_ms": 650})
        ],
        agent_execution=actual,
        expected_result=ExpectedResult(
            expected_output=expected.expected_output,
            expected_steps=[s.description for s in expected.steps_detail],
            expected_tool_calls=[t.name for t in expected.tool_calls_detail]
        )
    )
    
    report = report_gen.generate_comparison_report(
        query="计算 100 + 200",
        expected_execution=expected,
        actual_execution=actual,
        evaluation=evaluation,
        output_path="reports/comparison_report.json"
    )
    
    print(f"\n对比报告已生成: reports/comparison_report.json")
    print(f"\n对比结果:")
    print(f"  预期步骤: {report['comparison']['expected']['step_count']}")
    print(f"  实际步骤: {report['comparison']['actual']['step_count']}")
    print(f"  步骤差异: {report['comparison']['differences']['step_count_diff']:+d}")
    print(f"  耗时差异: {report['comparison']['differences']['duration_diff_ms']:+.0f}ms")
    print(f"\n  评估得分: {report['evaluation']['overall_score']:.2%}")


async def example_6_async_generation():
    """示例6: 异步生成理想回答"""
    print("\n" + "=" * 60)
    print("示例6: 异步生成理想回答")
    print("=" * 60)
    
    from agent_eval.generators import MetadataGenerator
    
    llm_config = LLMConfig(
        model="gpt-4",
        api_key="your-api-key"
    )
    
    generator = MetadataGenerator(llm_config)
    
    queries = [
        "搜索 Python 异步编程",
        "计算斐波那契数列前10项",
        "翻译 'Machine Learning' 为中文"
    ]
    
    print(f"\n异步批量生成 {len(queries)} 个理想回答...")
    
    # 并发生成
    tasks = [
        generator.generate_expected_execution_async(
            query=q,
            available_tools=AVAILABLE_TOOLS
        )
        for q in queries
    ]
    
    results = await asyncio.gather(*tasks)
    
    for query, expected in zip(queries, results):
        print(f"\n问题: {query}")
        print(f"  步骤数: {expected.step_count}")
        print(f"  工具调用: {expected.tool_call_count}")
        print(f"  预期耗时: {expected.expected_duration_ms}ms")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AgentEval 理想回答生成与评估示例")
    print("=" * 60)
    
    # 运行示例（请确保已配置有效的 API 密钥）
    
    # 示例1: 生成单个理想回答
    # example_1_generate_ideal_answer()
    
    # 示例2: 批量生成理想回答
    # example_2_batch_generate_ideal_answers()
    
    # 示例3: 使用理想回答评估真实执行
    # example_3_evaluate_with_ideal_answer()
    
    # 示例4: 生成评估报告
    # example_4_generate_report()
    
    # 示例5: 详细对比（无需API密钥）
    example_5_compare_expected_vs_actual()
    
    # 示例6: 异步生成（需要 await）
    # asyncio.run(example_6_async_generation())
    
    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)
    print("\n提示:")
    print("1. 运行示例前请设置有效的 API 密钥")
    print("2. 示例5不需要API密钥，可以直接运行")
    print("3. 生成的报告保存在 reports/ 目录")
    print("4. 数据文件保存在 data/ 目录")
