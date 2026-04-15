"""
元数据生成模块 - 使用大语言模型生成预期结果

本模块提供基于LLM的预期执行生成功能，包括：
- 生成预期输出结果
- 生成工具调用序列
- 生成执行步骤详情
- 估算执行时间和资源消耗

主要用途：
1. 自动创建测试用例的预期结果
2. 为评估提供基准参考
3. 生成训练数据

作者: AgentEval Team
创建日期: 2024
"""

import json
import re
from typing import Any, Dict, List, Optional

import aiohttp

from agent_eval.models import ExpectedResult, LLMConfig, StepDetail, ToolCallDetail


class ToolInfo:
    """
    工具信息类 - 用于向LLM描述可用工具

    包含工具的名称、描述、参数和返回类型，帮助LLM理解如何正确使用工具。

    属性:
        name: 工具名称
        description: 工具功能描述
        parameters: 工具参数定义（JSON Schema格式）
        return_type: 返回值类型描述

    示例:
        >>> tool = ToolInfo(
        ...     name="search",
        ...     description="搜索互联网信息",
        ...     parameters={"query": {"type": "string", "description": "搜索关键词"}},
        ...     return_type="List[SearchResult]"
        ... )
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        return_type: Optional[str] = None
    ):
        """
        初始化工具信息

        参数:
            name: 工具名称
            description: 工具功能描述
            parameters: 工具参数定义
            return_type: 返回值类型
        """
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        self.return_type = return_type or "any"

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        返回:
            Dict[str, Any]: 工具信息的字典表示
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "return_type": self.return_type
        }


class GeneratedExpectedExecution:
    """
    生成的预期执行结果 - 由LLM生成的完整执行计划

    包含查询的预期输出、执行步骤、工具调用序列等信息，但不实际执行工具调用。
    这是LLM对"理想执行"的模拟和预测。

    属性:
        query: 用户查询
        expected_output: 预期输出结果
        steps_detail: 详细执行步骤列表
        tool_calls_detail: 详细工具调用列表
        step_count: 步骤数量
        tool_call_count: 工具调用数量
        expected_duration_ms: 预期执行时长（毫秒）
        reasoning: LLM的推理过程说明
        metadata: 额外元数据

    示例:
        >>> execution = GeneratedExpectedExecution(
        ...     query="今天天气如何？",
        ...     expected_output="今天北京天气晴朗，温度25°C",
        ...     steps_detail=[StepDetail(step=1, description="调用天气API")],
        ...     tool_calls_detail=[ToolCallDetail(name="get_weather", parameters={"city": "北京"})],
        ...     step_count=1,
        ...     tool_call_count=1
        ... )
    """

    def __init__(
        self,
        query: str,
        expected_output: str,
        steps_detail: List[StepDetail],
        tool_calls_detail: List[ToolCallDetail],
        step_count: int,
        tool_call_count: int,
        expected_duration_ms: Optional[float] = None,
        reasoning: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化预期执行结果

        参数:
            query: 用户查询
            expected_output: 预期输出
            steps_detail: 执行步骤详情列表
            tool_calls_detail: 工具调用详情列表
            step_count: 步骤数量
            tool_call_count: 工具调用数量
            expected_duration_ms: 预期执行时长
            reasoning: 推理说明
            metadata: 元数据字典
        """
        self.query = query
        self.expected_output = expected_output
        self.steps_detail = steps_detail
        self.tool_calls_detail = tool_calls_detail
        self.step_count = step_count
        self.tool_call_count = tool_call_count
        self.expected_duration_ms = expected_duration_ms
        self.reasoning = reasoning
        self.metadata = metadata or {}

    def to_expected_result(self) -> ExpectedResult:
        """
        转换为ExpectedResult格式

        将GeneratedExpectedExecution转换为简化的ExpectedResult格式，
        用于评估时的基准比较。

        返回:
            ExpectedResult: 预期结果对象
        """
        return ExpectedResult(
            expected_output=self.expected_output,
            expected_steps=[s.description for s in self.steps_detail],
            expected_tool_calls=[t.name for t in self.tool_calls_detail],
            expected_tool_count=self.tool_call_count,
            expected_duration_ms=self.expected_duration_ms,
            metadata={
                "reasoning": self.reasoning,
                "steps_detail": [s.model_dump() for s in self.steps_detail],
                "tool_calls_detail": [t.model_dump() for t in self.tool_calls_detail],
                **self.metadata
            }
        )

    def model_dump(self) -> Dict[str, Any]:
        """
        序列化为字典

        返回:
            Dict[str, Any]: 对象的字典表示，可用于JSON序列化
        """
        return {
            "query": self.query,
            "expected_output": self.expected_output,
            "steps_detail": [s.model_dump() for s in self.steps_detail],
            "tool_calls_detail": [t.model_dump() for t in self.tool_calls_detail],
            "step_count": self.step_count,
            "tool_call_count": self.tool_call_count,
            "expected_duration_ms": self.expected_duration_ms,
            "reasoning": self.reasoning,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneratedExpectedExecution":
        """
        从字典创建对象

        参数:
            data: 包含对象数据的字典

        返回:
            GeneratedExpectedExecution: 新创建的对象实例
        """
        return cls(
            query=data["query"],
            expected_output=data["expected_output"],
            steps_detail=[StepDetail(**s) for s in data.get("steps_detail", [])],
            tool_calls_detail=[ToolCallDetail(**t) for t in data.get("tool_calls_detail", [])],
            step_count=data.get("step_count", 0),
            tool_call_count=data.get("tool_call_count", 0),
            expected_duration_ms=data.get("expected_duration_ms"),
            reasoning=data.get("reasoning"),
            metadata=data.get("metadata", {})
        )


class MetadataGenerator:
    """
    元数据生成器 - 使用LLM生成预期结果和元数据

    通过调用大语言模型，模拟理想的智能体执行过程，生成包含详细步骤和工具调用的预期结果。
    不实际执行任何工具，仅基于LLM的知识进行推理和预测。

    主要功能：
    1. 生成完整的预期执行计划
    2. 预测所需的工具调用序列
    3. 估算执行时间和资源消耗
    4. 提供推理过程说明

    使用场景：
    - 自动创建测试用例的预期结果
    - 为评估系统提供基准参考
    - 生成训练数据用于模型微调

    示例：
        >>> llm_config = LLMConfig(model="gpt-4", api_key="your-key")
        >>> generator = MetadataGenerator(llm_config)
        >>> result = await generator.generate_expected_execution_async(
        ...     query="查询北京天气",
        ...     available_tools=[ToolInfo(name="weather", description="获取天气")]
        ... )
    """

    def __init__(self, llm_config: LLMConfig):
        """
        初始化元数据生成器

        参数:
            llm_config: LLM配置，包含模型名称、API密钥等
        """
        self.llm_config = llm_config

    async def generate_expected_execution_async(
        self,
        query: str,
        available_tools: Optional[List[ToolInfo]] = None,
        context: Optional[str] = None
    ) -> GeneratedExpectedExecution:
        """
        异步生成完整的预期执行结果（不调用真实工具）

        使用LLM模拟理想的执行过程，生成详细的执行步骤、工具调用和预期输出。

        参数:
            query: 用户查询字符串
            available_tools: 可用工具列表及其描述
            context: 额外的上下文信息

        返回:
            GeneratedExpectedExecution: 包含完整执行详情的预期结果对象

        异常处理：
            如果生成过程中发生错误，会返回一个包含错误信息的fallback对象，
            而不是抛出异常，确保调用方的稳定性。

        示例：
            >>> result = await generator.generate_expected_execution_async(
            ...     query="今天天气如何？",
            ...     available_tools=[weather_tool]
            ... )
            >>> print(f"预期输出: {result.expected_output}")
            >>> print(f"需要步骤: {result.step_count}")
        """
        prompt = self._build_detailed_generation_prompt(query, available_tools, context)

        try:
            response = await self._call_llm(prompt)
            return self._parse_detailed_response(query, response)
        except Exception as e:
            # 发生错误时返回基本的预期执行对象，包含错误信息
            return GeneratedExpectedExecution(
                query=query,
                expected_output=f"生成预期结果时出错: {str(e)}",
                steps_detail=[],
                tool_calls_detail=[],
                step_count=0,
                tool_call_count=0,
                reasoning=f"生成失败: {str(e)}",
                metadata={"error": str(e)}
            )

    def generate_expected_execution(
        self,
        query: str,
        available_tools: Optional[List[ToolInfo]] = None,
        context: Optional[str] = None
    ) -> GeneratedExpectedExecution:
        """
        同步版本 - 生成完整的预期执行结果

        这是generate_expected_execution_async的同步包装器，
        方便在不支持异步的上下文中使用。

        参数:
            query: 用户查询字符串
            available_tools: 可用工具列表及其描述
            context: 额外的上下文信息

        返回:
            GeneratedExpectedExecution: 包含完整执行详情的预期结果对象

        注意：
            此方法会创建新的事件循环来运行异步代码。
            如果当前已经在事件循环中，会自动处理嵌套循环的情况。
        """
        import asyncio
        try:
            return asyncio.run(
                self.generate_expected_execution_async(query, available_tools, context)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_expected_execution_async(query, available_tools, context)
                )
            finally:
                loop.close()

    def _build_detailed_generation_prompt(
        self,
        query: str,
        available_tools: Optional[List[ToolInfo]],
        context: Optional[str]
    ) -> str:
        """
        构建详细的生成提示词

        根据用户查询、可用工具和上下文，构建一个结构化的提示词，
        指导LLM生成理想的执行计划。

        参数:
            query: 用户查询字符串
            available_tools: 可用工具列表
            context: 额外的上下文信息

        返回:
            str: 完整的提示词文本

        提示词结构：
        1. 角色设定：专家级AI智能体设计师
        2. 任务说明：生成理想执行计划
        3. 输入信息：查询、上下文、可用工具
        4. 输出格式要求：JSON格式
        5. 字段说明：每个字段的详细要求
        """
        prompt = f"""You are an expert AI agent designer. Given a user query and available tools, generate the IDEAL execution plan and result.

IMPORTANT: Do NOT actually call any tools. Just simulate what the ideal execution would look like.

User Query:
{query}
"""

        if context:
            prompt += f"""
Context:
{context}
"""

        if available_tools:
            prompt += """
Available Tools:
"""
            for tool in available_tools:
                prompt += f"""
- {tool.name}: {tool.description}
  Parameters: {json.dumps(tool.parameters, ensure_ascii=False)}</thinking>

<output>
继续为generators.py中的其他方法添加中文注释。我需要读取更多内容并为剩余的方法添加注释。
</output>
"""

        prompt += """
Please provide the expected execution in the following JSON format:
{
    "reasoning": "Brief explanation of the approach to solve this query",
    "expected_output": "The complete final answer to the user's query",
    "expected_duration_ms": 5000,
    "steps": [
        {
            "step": 1,
            "description": "Step description",
            "input": "Input to this step (can be null)",
            "output": "Output from this step (can be null)",
            "time": 100.0
        }
    ],
    "tool_calls": [
        {
            "name": "tool_name",
            "input": {"param": "value"},
            "output": {"result": "value"},
            "time": 200.0,
            "success": true,
            "err_msg": null
        }
    ]
}

Guidelines:
1. reasoning: Explain the strategy to solve this query
2. expected_output: Complete, accurate response that directly answers the query
3. expected_duration_ms: Reasonable total execution time in milliseconds
4. steps: Array of execution steps (3-7 steps typically)
   - step: Sequential number (1, 2, 3...)
   - description: What this step does
   - input/output: Data flow (can be null for simple steps)
   - time: Estimated time in milliseconds
5. tool_calls: Array of tool invocations (can be empty if no tools needed)
   - name: Tool name from available tools
   - input: Parameters passed to the tool
   - output: Expected result from the tool (simulated, not real)
   - time: Estimated tool execution time
   - success: true/false
   - err_msg: Error message if failed, null otherwise

Return ONLY the JSON object, no additional text.
"""
        return prompt

    def _parse_detailed_response(
        self,
        query: str,
        response: str
    ) -> GeneratedExpectedExecution:
        """
        解析LLM响应，提取详细的预期执行信息

        从LLM的JSON格式响应中解析出执行步骤、工具调用、预期输出等信息。
        如果解析失败，会返回一个基本的fallback对象。

        参数:
            query: 原始用户查询
            response: LLM的响应文本

        返回:
            GeneratedExpectedExecution: 解析后的预期执行对象

        解析流程：
        1. 从响应中提取JSON部分
        2. 解析JSON数据
        3. 提取步骤详情列表
        4. 提取工具调用列表
        5. 构建GeneratedExpectedExecution对象

        错误处理：
            如果JSON解析失败或缺少必要字段，会创建一个基本的fallback对象，
            包含原始响应和错误信息，确保不会返回None。
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            # Parse steps
            steps_detail = []
            for step_data in data.get("steps", []):
                steps_detail.append(StepDetail(
                    step=step_data.get("step", len(steps_detail) + 1),
                    description=step_data.get("description", ""),
                    input=step_data.get("input"),
                    output=step_data.get("output"),
                    time=step_data.get("time"),
                    success=True,
                    err_msg=None
                ))
            
            # Parse tool calls
            tool_calls_detail = []
            for tool_data in data.get("tool_calls", []):
                tool_calls_detail.append(ToolCallDetail(
                    name=tool_data.get("name", ""),
                    input=tool_data.get("input"),
                    output=tool_data.get("output"),
                    time=tool_data.get("time"),
                    success=tool_data.get("success", True),
                    err_msg=tool_data.get("err_msg")
                ))
            
            return GeneratedExpectedExecution(
                query=query,
                expected_output=data.get("expected_output", ""),
                steps_detail=steps_detail,
                tool_calls_detail=tool_calls_detail,
                step_count=len(steps_detail),
                tool_call_count=len(tool_calls_detail),
                expected_duration_ms=data.get("expected_duration_ms"),
                reasoning=data.get("reasoning", ""),
                metadata={"raw_response": response}
            )
            
        except Exception as e:
            # Fallback: create basic execution
            return GeneratedExpectedExecution(
                query=query,
                expected_output=response.strip(),
                steps_detail=[StepDetail(step=1, description="Generate response")],
                tool_calls_detail=[],
                step_count=1,
                tool_call_count=0,
                reasoning=f"Parse error: {str(e)}",
                metadata={
                    "parse_error": str(e),
                    "raw_response": response
                }
            )

    async def generate_expected_result_async(
        self,
        query: str,
        context: Optional[str] = None,
        available_tools: Optional[List[str]] = None
    ) -> ExpectedResult:
        """
        异步生成预期结果（遗留方法）

        这是generate_expected_execution_async的简化版本，返回ExpectedResult格式。
        主要用于向后兼容。

        参数:
            query: 用户查询字符串
            context: 额外的上下文信息
            available_tools: 可用工具名称列表（简化格式）

        返回:
            ExpectedResult: 预期结果对象

        注意：
            此方法为遗留方法，建议使用generate_expected_execution_async获取更详细的信息。
        """
        # 将简单的工具名称转换为ToolInfo对象
        tool_infos = None
        if available_tools:
            tool_infos = [
                ToolInfo(name=name, description=f"Tool: {name}")
                for name in available_tools
            ]

        generated = await self.generate_expected_execution_async(
            query=query,
            available_tools=tool_infos,
            context=context
        )

        return generated.to_expected_result()

    def generate_expected_result(
        self,
        query: str,
        context: Optional[str] = None,
        available_tools: Optional[List[str]] = None
    ) -> ExpectedResult:
        """
        同步生成预期结果（遗留方法）

        这是generate_expected_result_async的同步包装器。

        参数:
            query: 用户查询字符串
            context: 额外的上下文信息
            available_tools: 可用工具名称列表

        返回:
            ExpectedResult: 预期结果对象

        注意：
            此方法为遗留方法，建议使用generate_expected_execution获取更详细的信息。
        """
        import asyncio
        try:
            return asyncio.run(
                self.generate_expected_result_async(query, context, available_tools)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_expected_result_async(query, context, available_tools)
                )
            finally:
                loop.close()

    async def _call_llm(self, prompt: str) -> str:
        """
        调用LLM API

        使用aiohttp异步HTTP客户端调用大语言模型API。
        支持自定义API密钥、基础URL、模型参数等。

        参数:
            prompt: 发送给LLM的提示词

        返回:
            str: LLM的响应文本

        异常:
            Exception: 当API返回非200状态码时抛出

        配置选项：
        - api_key: API认证密钥
        - base_url: API基础URL（默认OpenAI）
        - model: 模型名称
        - temperature: 采样温度
        - max_tokens: 最大生成token数
        - timeout: 请求超时时间
        """
        headers = {
            "Content-Type": "application/json"
        }

        if self.llm_config.api_key:
            headers["Authorization"] = f"Bearer {self.llm_config.api_key}"

        payload = {
            "model": self.llm_config.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that generates structured expected results."},
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
                    raise Exception(f"LLM API error: {response.status} - {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"]

    def _parse_generation_response(self, response: str) -> ExpectedResult:
        """
        解析LLM响应，提取预期结果（遗留方法）

        从LLM的响应中提取JSON格式的预期结果信息。
        如果无法解析JSON，会将整个响应作为expected_output返回。

        参数:
            response: LLM的响应文本

        返回:
            ExpectedResult: 解析后的预期结果对象

        注意：
            此方法为遗留方法，建议使用_parse_detailed_response获取更详细的信息。
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                return ExpectedResult(
                    expected_output=data.get("expected_output"),
                    expected_steps=data.get("expected_steps"),
                    expected_tool_calls=data.get("expected_tool_calls"),
                    expected_tool_count=data.get("expected_tool_count"),
                    expected_duration_ms=data.get("expected_duration_ms"),
                    metadata={
                        "reasoning": data.get("reasoning", ""),
                        "raw_response": response
                    }
                )
            else:
                # Fallback: create from text
                return ExpectedResult(
                    expected_output=response.strip(),
                    metadata={"parse_error": "Could not extract JSON, using raw response"}
                )

        except json.JSONDecodeError as e:
            return ExpectedResult(
                expected_output=response.strip(),
                metadata={
                    "parse_error": f"JSON decode error: {str(e)}",
                    "raw_response": response
                }
            )

    async def generate_batch_expected_executions_async(
        self,
        queries: List[str],
        available_tools: Optional[List[ToolInfo]] = None,
        context: Optional[str] = None
    ) -> List[GeneratedExpectedExecution]:
        """Generate expected executions for multiple queries (async)"""
        results = []
        for query in queries:
            result = await self.generate_expected_execution_async(
                query, available_tools, context
            )
            results.append(result)
        return results

    def generate_batch_expected_executions(
        self,
        queries: List[str],
        available_tools: Optional[List[ToolInfo]] = None,
        context: Optional[str] = None
    ) -> List[GeneratedExpectedExecution]:
        """Generate expected executions for multiple queries (sync)"""
        import asyncio
        try:
            return asyncio.run(
                self.generate_batch_expected_executions_async(queries, available_tools, context)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_batch_expected_executions_async(queries, available_tools, context)
                )
            finally:
                loop.close()

    async def generate_batch_expected_results_async(
        self,
        queries: List[str],
        context: Optional[str] = None,
        available_tools: Optional[List[str]] = None
    ) -> List[ExpectedResult]:
        """Generate expected results for multiple queries (async) - Legacy method"""
        results = []
        for query in queries:
            result = await self.generate_expected_result_async(
                query, context, available_tools
            )
            results.append(result)
        return results

    def generate_batch_expected_results(
        self,
        queries: List[str],
        context: Optional[str] = None,
        available_tools: Optional[List[str]] = None
    ) -> List[ExpectedResult]:
        """Generate expected results for multiple queries (sync) - Legacy method"""
        import asyncio
        try:
            return asyncio.run(
                self.generate_batch_expected_results_async(queries, context, available_tools)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_batch_expected_results_async(queries, context, available_tools)
                )
            finally:
                loop.close()

    def generate_evaluation_dataset(
        self,
        queries: List[str],
        context: Optional[str] = None,
        available_tools: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Generate a complete evaluation dataset with queries and expected results"""
        expected_results = self.generate_batch_expected_results(
            queries, context, available_tools
        )

        dataset = []
        for query, expected in zip(queries, expected_results):
            dataset.append({
                "query": query,
                "expected_result": expected.model_dump()
            })

        return dataset

    def save_evaluation_dataset(
        self,
        dataset: List[Dict[str, Any]],
        file_path: str
    ):
        """Save evaluation dataset to JSON file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

    def load_evaluation_dataset(
        self,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """Load evaluation dataset from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
