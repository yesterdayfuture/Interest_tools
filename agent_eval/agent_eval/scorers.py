"""
评分机制模块 - 用于智能体评估

本模块支持两种评分方式：
1. 基于代码的确定性评分 - 快速、低成本，适用于工具调用路径、格式检查等
2. 基于LLM的评分（LLM-as-Judge）- 灵活、智能，适用于主观质量评估

支持两种LLM调用方式：
- aiohttp: 异步HTTP请求（默认）
- openai: 使用OpenAI官方库

作者: AgentEval Team
创建日期: 2024
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp

from agent_eval.models import AgentExecution, ExpectedResult, LLMConfig

# 尝试导入openai库，如果不可用则设置为None
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False


class ScorerResult:
    """
    评分结果类
    
    用于封装评分器的评分结果，包含分数、通过状态、详细信息和错误信息
    
    属性:
        scorer_name: 评分器名称
        score: 评分分数（0.0-1.0之间）
        passed: 是否通过评分
        details: 详细评分信息字典
        error: 错误信息（如果有）
    """

    def __init__(
        self,
        scorer_name: str,
        score: float,
        passed: bool,
        details: Dict[str, Any] = None,
        error: Optional[str] = None
    ):
        self.scorer_name = scorer_name
        # 确保分数在0-1范围内
        self.score = max(0.0, min(1.0, score))
        self.passed = passed
        self.details = details or {}
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """将结果转换为字典格式，便于序列化和存储"""
        return {
            "scorer_name": self.scorer_name,
            "score": self.score,
            "passed": self.passed,
            "details": self.details,
            "error": self.error
        }


class BaseScorer(ABC):
    """
    评分器抽象基类
    
    所有评分器必须继承此类并实现score方法
    提供统一的评分接口，便于扩展不同类型的评分器
    
    子类需要实现:
        score(): 执行评分逻辑并返回ScorerResult
    """

    def __init__(self, name: str):
        """
        初始化评分器
        
        参数:
            name: 评分器名称，用于标识
        """
        self.name = name

    @abstractmethod
    def score(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> ScorerResult:
        """
        对智能体执行进行评分
        
        参数:
            execution: 智能体执行记录，包含查询、输出、工具调用等信息
            expected: 预期结果，用于对比评估（可选）
            
        返回:
            ScorerResult: 评分结果对象
        """
        pass


class CodeBasedScorer(BaseScorer):
    """
    基于代码的确定性评分器
    
    通过代码逻辑进行精确匹配评分，快速且成本低
    适用于工具调用路径检查、格式验证、精确匹配等场景
    
    检查类型:
    1. 工具序列检查: 验证工具调用顺序是否符合预期
    2. 工具数量检查: 验证工具调用次数是否合理
    3. 输出格式检查: 验证输出是否符合预期格式（JSON、结构化等）
    4. 精确匹配检查: 验证输出是否与预期完全一致
    5. 自定义检查: 支持正则、包含、等于等多种自定义规则
    
    特点:
    - 确定性: 相同的输入总是产生相同的输出
    - 高效: 无需调用外部API，执行速度快
    - 低成本: 不消耗LLM token
    - 可解释: 每个检查都有明确的通过/失败标准
    
    示例:
        >>> scorer = CodeBasedScorer(
        ...     check_tool_sequence=True,  # 检查工具调用序列
        ...     check_tool_count=True,     # 检查工具调用数量
        ...     check_output_format=True,  # 检查输出格式
        ...     custom_checks=[            # 自定义检查规则
        ...         {"type": "contains", "target": "output", "value": "关键信息"}
        ...     ]
        ... )
        >>> result = scorer.score(execution, expected)
    """

    def __init__(
        self,
        check_tool_sequence: bool = True,
        check_tool_count: bool = True,
        check_output_format: bool = False,
        check_exact_match: bool = False,
        custom_checks: Optional[List[Dict[str, Any]]] = None
    ):
        """
        初始化代码评分器
        
        参数:
            check_tool_sequence: 是否检查工具调用序列（默认True）
            check_tool_count: 是否检查工具调用数量（默认True）
            check_output_format: 是否检查输出格式（默认False）
            check_exact_match: 是否检查精确匹配（默认False）
            custom_checks: 自定义检查规则列表（默认空列表）
            
        自定义检查规则格式:
            {
                "type": "contains" | "regex" | "equals",  # 检查类型
                "target": "output" | "tool_calls" | "metadata_key",  # 检查目标
                "value": "要匹配的值"  # 期望值
            }
        """
        super().__init__("CodeBasedScorer")
        self.check_tool_sequence = check_tool_sequence
        self.check_tool_count = check_tool_count
        self.check_output_format = check_output_format
        self.check_exact_match = check_exact_match
        self.custom_checks = custom_checks or []

    def score(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> ScorerResult:
        """
        使用确定性代码逻辑进行评分
        
        根据配置的检查项逐一验证，最后计算平均分
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            ScorerResult: 包含所有检查项详细结果的评分对象
        """
        # 初始化检查结果统计
        details = {
            "checks_performed": [],  # 已执行的检查列表
            "checks_passed": 0,      # 通过的检查数
            "checks_failed": 0       # 失败的检查数
        }

        total_score = 0.0  # 总分
        check_count = 0    # 检查项计数

        # 获取实际工具调用序列
        actual_tool_sequence = [tc.name for tc in execution.tool_calls_detail]

        # 1. 工具序列检查
        if self.check_tool_sequence and expected and expected.expected_tool_calls:
            check_count += 1
            sequence_score = self._check_tool_sequence(
                actual_tool_sequence,
                expected.expected_tool_calls
            )
            total_score += sequence_score
            details["checks_performed"].append({
                "name": "tool_sequence",
                "score": sequence_score,
                "passed": sequence_score >= 0.7
            })
            if sequence_score >= 0.7:
                details["checks_passed"] += 1
            else:
                details["checks_failed"] += 1

        # 2. 工具数量检查
        if self.check_tool_count and expected and expected.expected_tool_count is not None:
            check_count += 1
            count_score = self._check_tool_count(
                execution.tool_call_count,
                expected.expected_tool_count
            )
            total_score += count_score
            details["checks_performed"].append({
                "name": "tool_count",
                "score": count_score,
                "passed": count_score >= 0.7
            })
            if count_score >= 0.7:
                details["checks_passed"] += 1
            else:
                details["checks_failed"] += 1

        # 3. 输出格式检查
        if self.check_output_format and execution.final_output:
            check_count += 1
            format_score = self._check_output_format(execution.final_output)
            total_score += format_score
            details["checks_performed"].append({
                "name": "output_format",
                "score": format_score,
                "passed": format_score >= 0.7
            })
            if format_score >= 0.7:
                details["checks_passed"] += 1
            else:
                details["checks_failed"] += 1

        # 4. 精确匹配检查
        if self.check_exact_match and expected and expected.expected_output:
            check_count += 1
            match_score = self._check_exact_match(
                execution.final_output,
                expected.expected_output
            )
            total_score += match_score
            details["checks_performed"].append({
                "name": "exact_match",
                "score": match_score,
                "passed": match_score == 1.0
            })
            if match_score == 1.0:
                details["checks_passed"] += 1
            else:
                details["checks_failed"] += 1

        # 5. 自定义检查
        for custom_check in self.custom_checks:
            check_count += 1
            custom_score = self._run_custom_check(custom_check, execution, expected)
            total_score += custom_score
            details["checks_performed"].append({
                "name": custom_check.get("name", "custom"),
                "score": custom_score,
                "passed": custom_score >= 0.7
            })
            if custom_score >= 0.7:
                details["checks_passed"] += 1
            else:
                details["checks_failed"] += 1

        # 计算最终分数
        final_score = total_score / check_count if check_count > 0 else 1.0
        passed = details["checks_passed"] >= details["checks_failed"]

        return ScorerResult(
            scorer_name=self.name,
            score=final_score,
            passed=passed,
            details=details
        )

    def _check_tool_sequence(
        self,
        actual: List[str],
        expected: List[str]
    ) -> float:
        """
        检查工具调用序列是否匹配预期
        
        评分逻辑:
        - 完全匹配: 1.0
        - 是子序列: 0.9
        - 部分匹配: 使用F1分数
        - 无匹配: 0.0
        
        参数:
            actual: 实际工具调用序列
            expected: 预期工具调用序列
            
        返回:
            float: 0.0-1.0之间的匹配分数
        """
        if not expected:
            return 1.0

        if actual == expected:
            return 1.0

        # 检查实际序列是否是预期序列的子序列
        if self._is_subsequence(actual, expected):
            return 0.9

        # 计算重叠部分的F1分数
        expected_set = set(expected)
        actual_set = set(actual)
        intersection = expected_set & actual_set

        if not intersection:
            return 0.0

        precision = len(intersection) / len(actual_set) if actual_set else 0
        recall = len(intersection) / len(expected_set) if expected_set else 0

        if precision + recall == 0:
            return 0.0

        f1 = 2 * (precision * recall) / (precision + recall)
        return f1

    def _is_subsequence(self, actual: List[str], expected: List[str]) -> bool:
        """
        检查actual是否是expected的子序列
        
        子序列定义: 可以通过删除expected中的某些元素得到actual，
        同时保持剩余元素的相对顺序
        
        参数:
            actual: 实际序列
            expected: 预期序列
            
        返回:
            bool: 如果是子序列返回True
        """
        it = iter(expected)
        return all(tool in it for tool in actual)

    def _check_tool_count(self, actual: int, expected: int) -> float:
        """
        检查工具调用数量是否接近预期
        
        使用阶梯式评分，实际数量越接近预期得分越高
        
        评分标准:
        - ratio <= 1.0: 1.0 (完美或更少)
        - ratio <= 1.2: 0.9 (略多)
        - ratio <= 1.5: 0.7 (较多)
        - ratio <= 2.0: 0.5 (多很多)
        - ratio > 2.0: 0.3 (过多)
        
        参数:
            actual: 实际工具调用次数
            expected: 预期工具调用次数
            
        返回:
            float: 0.0-1.0之间的评分
        """
        if expected == 0:
            return 1.0 if actual == 0 else 0.0

        ratio = actual / expected

        if ratio <= 1.0:
            return 1.0
        elif ratio <= 1.2:
            return 0.9
        elif ratio <= 1.5:
            return 0.7
        elif ratio <= 2.0:
            return 0.5
        else:
            return 0.3

    def _check_output_format(self, output: str) -> float:
        """
        检查输出格式是否符合预期
        
        检查项:
        1. JSON格式: 是否能解析为JSON
        2. 结构化内容: 是否包含列表、编号、标题等结构
        3. 合理长度: 输出长度是否足够（至少50字符）
        
        参数:
            output: 智能体输出文本
            
        返回:
            float: 0.0-1.0之间的格式评分
        """
        checks = []

        # 检查是否为JSON格式
        try:
            json.loads(output)
            checks.append(1.0)
        except json.JSONDecodeError:
            checks.append(0.0)

        # 检查是否有结构化内容（列表、编号、标题等）
        has_structure = bool(re.search(r'\n\s*[-•*]\s+|\n\s*\d+\.|\n\s*\w+:\s*', output))
        checks.append(1.0 if has_structure else 0.5)

        # 检查长度是否合理（至少50字符得满分，按比例递减）
        length_score = min(1.0, len(output) / 50) if len(output) > 0 else 0.0
        checks.append(length_score)

        return sum(checks) / len(checks)

    def _check_exact_match(self, actual: Optional[str], expected: str) -> float:
        """
        检查实际输出是否与预期完全匹配
        
        参数:
            actual: 实际输出
            expected: 预期输出
            
        返回:
            float: 完全匹配返回1.0，否则返回0.0
        """
        if actual is None:
            return 0.0
        return 1.0 if actual.strip() == expected.strip() else 0.0

    def _run_custom_check(
        self,
        check: Dict[str, Any],
        execution: AgentExecution,
        expected: Optional[ExpectedResult]
    ) -> float:
        """
        执行自定义检查规则
        
        支持的检查类型:
        - contains: 包含检查，内容中是否包含指定值
        - regex: 正则匹配，内容是否匹配指定正则表达式
        - equals: 相等检查，内容是否等于指定值
        
        参数:
            check: 检查规则字典，包含type、target、value
            execution: 智能体执行记录
            expected: 预期结果（未使用，保持接口一致）
            
        返回:
            float: 检查通过返回1.0，失败返回0.0
        """
        check_type = check.get("type", "contains")
        target = check.get("target", "output")
        value = check.get("value", "")

        # 根据target获取要检查的内容
        if target == "output":
            content = execution.final_output or ""
        elif target == "tool_calls":
            actual_tool_sequence = [tc.name for tc in execution.tool_calls_detail]
            content = " ".join(actual_tool_sequence)
        else:
            # 从metadata中获取
            content = str(execution.metadata.get(target, ""))

        # 根据检查类型执行检查
        if check_type == "contains":
            return 1.0 if value in content else 0.0
        elif check_type == "regex":
            return 1.0 if re.search(value, content) else 0.0
        elif check_type == "equals":
            return 1.0 if content == value else 0.0
        else:
            # 未知的检查类型返回中性分数
            return 0.5


class LLMJudgeScorer(BaseScorer):
    """
    基于LLM的评分器（LLM-as-Judge）
    
    使用更强大的语言模型对智能体输出进行主观质量评估
    适用于评估答案质量、相关性、完整性等难以用代码量化的指标
    
    支持两种调用方式：
    1. aiohttp: 异步HTTP请求，轻量级，无需额外依赖
    2. openai: 使用OpenAI官方库，功能更完善，支持流式输出等高级特性
    
    评估维度（可自定义）：
    - accuracy: 准确性，信息是否正确
    - completeness: 完整性，是否回答全面
    - relevance: 相关性，是否切题
    - clarity: 清晰度，表达是否清晰
    
    示例:
        >>> llm_config = LLMConfig(
        ...     model="gpt-4",
        ...     api_key="your-api-key",
        ...     use_openai=True  # 使用openai库
        ... )
        >>> scorer = LLMJudgeScorer(llm_config)
        >>> result = scorer.score(execution, expected)
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        evaluation_criteria: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        use_openai: Optional[bool] = None
    ):
        """
        初始化LLM评分器
        
        参数:
            llm_config: LLM配置，包含模型名称、API密钥、基础URL等
            evaluation_criteria: 评估维度列表，默认为["accuracy", "completeness", "relevance", "clarity"]
            system_prompt: 系统提示词，用于指导LLM如何评分
            use_openai: 是否使用openai库，None则根据llm_config或自动检测
        """
        super().__init__("LLMJudgeScorer")
        self.llm_config = llm_config
        self.evaluation_criteria = evaluation_criteria or [
            "accuracy",
            "completeness",
            "relevance",
            "clarity"
        ]
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # 确定是否使用openai库
        if use_openai is None:
            # 优先使用llm_config中的设置，否则自动检测
            self.use_openai = getattr(llm_config, 'use_openai', False) and OPENAI_AVAILABLE
        else:
            self.use_openai = use_openai and OPENAI_AVAILABLE
        
        # 如果使用openai库，初始化客户端
        if self.use_openai:
            self._init_openai_client()

    def _init_openai_client(self):
        """
        初始化OpenAI客户端
        
        根据配置创建OpenAI或AsyncOpenAI客户端实例
        支持自定义base_url以兼容第三方API（如Azure、文心一言等）
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "使用openai库需要安装openai包。"
                "请运行: pip install openai"
            )
        
        # 配置API密钥和基础URL
        api_key = self.llm_config.api_key
        base_url = self.llm_config.base_url
        
        # 创建同步客户端
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self._openai_client = openai.OpenAI(**client_kwargs)
        
        # 创建异步客户端（用于async方法）
        self._openai_async_client = openai.AsyncOpenAI(**client_kwargs)

    def _default_system_prompt(self) -> str:
        """
        LLM评分器的默认系统提示词
        
        指导LLM如何评估智能体输出，要求返回结构化JSON格式的评分结果
        
        返回:
            str: 系统提示词，包含评估维度和输出格式说明
        """
        return """你是一个专业的AI智能体输出评估专家。
你的任务是根据特定标准评估智能体的输出质量，并提供结构化的评估结果。

请根据以下标准评估响应（每项0-1分）：
1. 准确性（accuracy）: 信息是否正确、符合事实？
2. 完整性（completeness）: 是否回答了问题的所有方面？
3. 相关性（relevance）: 内容是否与用户问题相关？
4. 清晰度（clarity）: 响应是否清晰、结构良好？

请以JSON格式提供评估结果：
{
    "scores": {
        "accuracy": <0-1>,
        "completeness": <0-1>,
        "relevance": <0-1>,
        "clarity": <0-1>
    },
    "overall_score": <0-1>,
    "reasoning": "对你的评估的简要说明",
    "passed": <true/false>
}

注意：
- overall_score应该是各项分数的加权平均
- passed为true表示整体通过（建议overall_score >= 0.7）
- reasoning应该用中文简要说明评分理由
"""

    async def score_async(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> ScorerResult:
        """
        异步评分方法
        
        使用LLM对智能体执行进行异步评分
        根据配置选择使用openai库或aiohttp
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            ScorerResult: 评分结果
        """
        try:
            prompt = self._build_evaluation_prompt(execution, expected)
            
            # 根据配置选择调用方式
            if self.use_openai:
                response = await self._call_llm_openai_async(prompt)
            else:
                response = await self._call_llm_aiohttp(prompt)
                
            return self._parse_llm_response(response)
        except Exception as e:
            return ScorerResult(
                scorer_name=self.name,
                score=0.0,
                passed=False,
                error=f"评分失败: {str(e)}"
            )

    def score(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> ScorerResult:
        """
        同步评分方法
        
        使用LLM对智能体执行进行同步评分
        内部调用异步方法，自动处理事件循环
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            ScorerResult: 评分结果
        """
        import asyncio
        try:
            return asyncio.run(self.score_async(execution, expected))
        except RuntimeError:
            # 如果已在事件循环中，创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.score_async(execution, expected))
            finally:
                loop.close()

    def _build_evaluation_prompt(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult]
    ) -> str:
        """
        构建评估提示词
        
        将智能体执行信息格式化为LLM可理解的评估提示
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            str: 格式化的评估提示词
        """
        actual_tool_sequence = [tc.name for tc in execution.tool_calls_detail]
        prompt = f"""用户查询: {execution.query}

智能体响应:
{execution.final_output or "未提供响应"}

执行详情:
- 执行成功: {execution.success}
- 执行步骤数: {execution.step_count}
- 工具调用次数: {execution.tool_call_count}
- 使用的工具: {', '.join(actual_tool_sequence) if actual_tool_sequence else '无'}
"""

        if expected and expected.expected_output:
            prompt += f"""
预期响应:
{expected.expected_output}
"""

        prompt += """
请根据上述标准评估智能体的响应，并返回包含评估结果的JSON对象。
"""
        return prompt

    async def _call_llm_openai_async(self, prompt: str) -> str:
        """
        使用OpenAI库异步调用LLM
        
        参数:
            prompt: 用户提示词
            
        返回:
            str: LLM的响应内容
            
        异常:
            Exception: 当API调用失败时抛出
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._openai_async_client.chat.completions.create(
            model=self.llm_config.model,
            messages=messages,
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.max_tokens
        )
        
        return response.choices[0].message.content

    def _call_llm_openai_sync(self, prompt: str) -> str:
        """
        使用OpenAI库同步调用LLM
        
        参数:
            prompt: 用户提示词
            
        返回:
            str: LLM的响应内容
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self._openai_client.chat.completions.create(
            model=self.llm_config.model,
            messages=messages,
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.max_tokens
        )
        
        return response.choices[0].message.content

    async def _call_llm_aiohttp(self, prompt: str) -> str:
        """
        使用aiohttp异步调用LLM API
        
        轻量级的HTTP调用方式，无需额外依赖openai库
        兼容OpenAI API格式和第三方API
        
        参数:
            prompt: 用户提示词
            
        返回:
            str: LLM的响应内容
            
        异常:
            Exception: 当API调用失败时抛出
        """
        headers = {
            "Content-Type": "application/json"
        }

        if self.llm_config.api_key:
            headers["Authorization"] = f"Bearer {self.llm_config.api_key}"

        payload = {
            "model": self.llm_config.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.llm_config.temperature
        }

        if self.llm_config.max_tokens:
            payload["max_tokens"] = self.llm_config.max_tokens

        base_url = self.llm_config.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"

        timeout = aiohttp.ClientTimeout(total=self.llm_config.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM API错误: {response.status} - {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"]

    def _parse_llm_response(self, response: str) -> ScorerResult:
        """
        解析LLM响应，提取评分结果
        
        尝试从JSON格式的响应中提取分数，如果失败则使用备用解析方法
        
        参数:
            response: LLM的原始响应文本
            
        返回:
            ScorerResult: 解析后的评分结果
        """
        try:
            # 尝试从响应中提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                scores = data.get("scores", {})
                overall_score = data.get("overall_score", 0.5)
                passed = data.get("passed", overall_score >= 0.7)
                reasoning = data.get("reasoning", "")

                return ScorerResult(
                    scorer_name=self.name,
                    score=overall_score,
                    passed=passed,
                    details={
                        "individual_scores": scores,
                        "reasoning": reasoning,
                        "raw_response": response
                    }
                )
            else:
                # 备用：从文本中解析
                return self._fallback_parse(response)

        except json.JSONDecodeError:
            return self._fallback_parse(response)

    def _fallback_parse(self, response: str) -> ScorerResult:
        """
        备用解析方法
        
        当JSON提取失败时，尝试从文本中查找分数模式
        
        参数:
            response: LLM的原始响应文本
            
        返回:
            ScorerResult: 解析后的评分结果
        """
        # 在文本中查找分数模式
        score_patterns = [
            r'overall[\s_]*score[:\s]+([0-9.]+)',
            r'score[:\s]+([0-9.]+)',
            r'([0-9.]+)\s*/\s*10',
            r'([0-9.]+)\s*/\s*1'
        ]

        for pattern in score_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                # 归一化到0-1范围
                if score > 1.0:
                    score = score / 10.0
                return ScorerResult(
                    scorer_name=self.name,
                    score=score,
                    passed=score >= 0.7,
                    details={"raw_response": response}
                )

        # 默认备用结果
        return ScorerResult(
            scorer_name=self.name,
            score=0.5,
            passed=True,
            details={
                "message": "无法从响应中解析分数",
                "raw_response": response
            }
        )


class HybridScorer(BaseScorer):
    """
    混合评分器
    
    结合基于代码的确定性评分和基于LLM的智能评分
    兼顾评分的准确性和灵活性
    
    评分公式:
        final_score = code_score * code_weight + llm_score * llm_weight
    
    使用场景:
    - 需要快速确定性检查（如工具调用序列）
    - 同时需要主观质量评估（如回答相关性）
    - 希望平衡成本和评估质量
    
    示例:
        >>> code_scorer = CodeBasedScorer(check_tool_sequence=True)
        >>> llm_scorer = LLMJudgeScorer(llm_config)
        >>> hybrid = HybridScorer(code_scorer, llm_scorer, code_weight=0.4, llm_weight=0.6)
        >>> result = hybrid.score(execution, expected)
    """

    def __init__(
        self,
        code_scorer: CodeBasedScorer,
        llm_scorer: Optional[LLMJudgeScorer] = None,
        code_weight: float = 0.4,
        llm_weight: float = 0.6
    ):
        """
        初始化混合评分器
        
        参数:
            code_scorer: 代码评分器实例，用于确定性检查
            llm_scorer: LLM评分器实例，用于主观评估（可选）
            code_weight: 代码评分的权重（默认0.4）
            llm_weight: LLM评分的权重（默认0.6）
            
        注意:
            code_weight + llm_weight 应该等于1.0
        """
        super().__init__("HybridScorer")
        self.code_scorer = code_scorer
        self.llm_scorer = llm_scorer
        self.code_weight = code_weight
        self.llm_weight = llm_weight

    def score(
        self,
        execution: AgentExecution,
        expected: Optional[ExpectedResult] = None
    ) -> ScorerResult:
        """
        使用代码和LLM两种方法进行评分
        
        先执行代码评分，如果配置了LLM评分器则也执行LLM评分，
        最后根据权重合并两个评分结果
        
        参数:
            execution: 智能体执行记录
            expected: 预期结果（可选）
            
        返回:
            ScorerResult: 合并后的评分结果，包含两个评分器的详细结果
        """
        # 执行代码评分
        code_result = self.code_scorer.score(execution, expected)

        # 如果没有配置LLM评分器，直接返回代码评分结果
        if self.llm_scorer is None:
            return ScorerResult(
                scorer_name=self.name,
                score=code_result.score,
                passed=code_result.passed,
                details={
                    "code_scorer": code_result.to_dict(),
                    "llm_scorer": None,
                    "weights": {
                        "code": 1.0,
                        "llm": 0.0
                    },
                    "note": "未配置LLM评分器，仅使用代码评分"
                }
            )

        # 执行LLM评分
        llm_result = self.llm_scorer.score(execution, expected)

        # 根据权重合并分数
        combined_score = (
            code_result.score * self.code_weight +
            llm_result.score * self.llm_weight
        )

        # 判断是否通过（阈值0.7）
        passed = combined_score >= 0.7

        return ScorerResult(
            scorer_name=self.name,
            score=combined_score,
            passed=passed,
            details={
                "code_scorer": code_result.to_dict(),
                "llm_scorer": llm_result.to_dict(),
                "weights": {
                    "code": self.code_weight,
                    "llm": self.llm_weight
                },
                "calculation": f"{code_result.score:.3f} * {self.code_weight} + {llm_result.score:.3f} * {self.llm_weight} = {combined_score:.3f}"
            }
        )
