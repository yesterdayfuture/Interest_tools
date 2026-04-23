"""
OpenAI API模型接口模块

支持OpenAI官方API以及兼容OpenAI格式的第三方API
包括：GPT-3.5、GPT-4、Azure OpenAI等
"""

import os
import time
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from pathlib import Path
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError

from .base import BaseModel, ModelConfig, ModelType, GenerationResult, ModelInfo


def _load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    加载YAML配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        Dict: 配置字典，文件不存在则返回空字典
    """
    try:
        import yaml
        path = Path(config_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {}


def _get_config_value(config: Dict, *keys: str, default: Any = None) -> Any:
    """
    从嵌套字典中获取配置值
    
    Args:
        config: 配置字典
        keys: 键路径
        default: 默认值
    
    Returns:
        Any: 配置值或默认值
    """
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


class OpenAIModel(BaseModel):
    """
    OpenAI API模型类
    
    通过OpenAI API进行模型推理
    支持标准completion和chat completion接口
    """
    
    def __init__(
        self,
        config: Optional[ModelConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        初始化OpenAI模型
        
        配置优先级（从高到低）：
        1. 显式传入的参数（api_key, base_url）
        2. 环境变量（OPENAI_API_KEY, OPENAI_BASE_URL）
        3. YAML配置文件（config.yaml 或指定路径）
        4. 默认值
        
        Args:
            config: 模型配置对象
            api_key: OpenAI API密钥（显式配置，优先级最高）
            base_url: API基础URL（显式配置，优先级最高）
            model_name: 模型名称（如gpt-3.5-turbo）
            config_path: YAML配置文件路径，默认查找./config.yaml
        """
        if config is None:
            config = ModelConfig(
                name=model_name or "gpt-3.5-turbo",
                model_type=ModelType.OPENAI,
                temperature=0.0,  # 评估时使用确定性输出
                max_tokens=512,
                timeout=30,
                max_retries=3
            )
        
        super().__init__(config)
        
        # 加载YAML配置
        yaml_config = {}
        yaml_path = config_path or "config.yaml"
        if Path(yaml_path).exists():
            yaml_config = _load_yaml_config(yaml_path)
        
        # 设置API密钥（优先级：显式 > 环境变量 > 配置文件）
        self.api_key = (
            api_key  # 1. 显式传入
            or os.getenv("OPENAI_API_KEY")  # 2. 环境变量
            or _get_config_value(yaml_config, "models", "openai", "api_key")  # 3. 配置文件
            or ""  # 4. 默认空值
        )
        
        # 设置API基础URL（优先级：显式 > 环境变量 > 配置文件 > 默认值）
        self.base_url = (
            base_url  # 1. 显式传入
            or os.getenv("OPENAI_BASE_URL")  # 2. 环境变量
            or _get_config_value(yaml_config, "models", "openai", "base_url")  # 3. 配置文件
            or "https://api.openai.com/v1"  # 4. 默认值
        )
        
        # 设置模型名称（优先级：显式 > 配置文件 > config对象 > 默认值）
        self.model_name = (
            model_name  # 1. 显式传入
            or _get_config_value(yaml_config, "models", "openai", "default_model")  # 2. 配置文件
            or config.name  # 3. config对象
            or "gpt-3.5-turbo"  # 4. 默认值
        )
        
        # 从配置文件加载其他参数
        if yaml_config:
            config.timeout = _get_config_value(
                yaml_config, "models", "openai", "timeout", 
                default=config.timeout
            )
            config.max_retries = _get_config_value(
                yaml_config, "models", "openai", "max_retries", 
                default=config.max_retries
            )
        
        # OpenAI客户端（延迟初始化）
        self._client: Optional[AsyncOpenAI] = None
        
        # 记录配置来源（用于调试）
        self._config_source = {
            "api_key": "显式配置" if api_key else ("环境变量" if os.getenv("OPENAI_API_KEY") else ("配置文件" if _get_config_value(yaml_config, "models", "openai", "api_key") else "未配置")),
            "base_url": "显式配置" if base_url else ("环境变量" if os.getenv("OPENAI_BASE_URL") else ("配置文件" if _get_config_value(yaml_config, "models", "openai", "base_url") else "默认值"))
        }
    
    async def initialize(self) -> None:
        """
        初始化OpenAI客户端
        
        建立与OpenAI API的连接
        """
        if self._initialized:
            return
        
        # 检查API密钥是否已配置
        if not self.api_key:
            raise ValueError(
                "请提供OpenAI API密钥。配置方式（按优先级）：\n"
                "1. 显式传入: OpenAIModel(api_key='your-key')\n"
                "2. 环境变量: export OPENAI_API_KEY='your-key'\n"
                "3. 配置文件: 在config.yaml中设置 models.openai.api_key"
            )
        
        try:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
            
            # 测试连接
            await self.health_check()
            self._initialized = True
            
        except Exception as e:
            raise ConnectionError(f"无法连接到OpenAI API: {e}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> GenerationResult:
        """
        生成文本
        
        使用Chat Completion API进行生成
        
        Args:
            prompt: 用户输入提示
            system_prompt: 系统提示（可选）
            **kwargs: 额外生成参数
        
        Returns:
            GenerationResult: 生成结果
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 合并参数
            params = self._merge_generation_params(**kwargs)
            
            # 调用API
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=params.get("temperature", 0.0),
                max_tokens=params.get("max_tokens", 512),
                top_p=params.get("top_p", 1.0),
                stop=params.get("stop", None)
            )
            
            # 计算延迟
            latency_ms = (time.time() - start_time) * 1000
            
            # 提取结果
            choice = response.choices[0]
            generated_text = choice.message.content or ""
            
            # 获取token使用信息
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
            # 更新统计
            self._update_statistics(latency_ms, total_tokens)
            
            return GenerationResult(
                text=generated_text.strip(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                finish_reason=choice.finish_reason,
                metadata={
                    "model": response.model,
                    "created": response.created
                }
            )
            
        except RateLimitError as e:
            raise RuntimeError(f"API速率限制: {e}")
        except APITimeoutError as e:
            raise RuntimeError(f"API请求超时: {e}")
        except APIError as e:
            raise RuntimeError(f"API错误: {e}")
        except Exception as e:
            raise RuntimeError(f"生成失败: {e}")
    
    async def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> List[GenerationResult]:
        """
        批量生成文本
        
        并发处理多个提示，提高评估效率
        
        Args:
            prompts: 输入提示列表
            system_prompt: 系统提示
            **kwargs: 额外生成参数
        
        Returns:
            List[GenerationResult]: 生成结果列表
        """
        if not self._initialized:
            await self.initialize()
        
        # 限制并发数，避免触发速率限制
        semaphore = asyncio.Semaphore(5)
        
        async def generate_with_semaphore(prompt: str) -> GenerationResult:
            async with semaphore:
                # 添加小延迟，避免请求过于集中
                await asyncio.sleep(0.1)
                return await self.generate(prompt, system_prompt, **kwargs)
        
        # 并发执行所有生成任务
        tasks = [generate_with_semaphore(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 生成失败时返回空结果
                processed_results.append(GenerationResult(
                    text="",
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=0.0,
                    finish_reason="error",
                    metadata={"error": str(result), "prompt_index": i}
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成文本
        
        Args:
            prompt: 输入提示
            system_prompt: 系统提示
            **kwargs: 额外生成参数
        
        Yields:
            str: 生成的文本片段
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 合并参数
            params = self._merge_generation_params(**kwargs)
            
            # 调用流式API
            stream = await self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=params.get("temperature", 0.0),
                max_tokens=params.get("max_tokens", 512),
                top_p=params.get("top_p", 1.0),
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise RuntimeError(f"流式生成失败: {e}")
    
    async def get_model_info(self) -> ModelInfo:
        """
        获取模型信息
        
        Returns:
            ModelInfo: 模型信息对象
        """
        # OpenAI模型信息映射
        model_info_map = {
            "gpt-4": ModelInfo(
                name="gpt-4",
                description="GPT-4",
                context_length=8192,
                supports_chat=True,
                supports_completion=True,
                supports_streaming=True
            ),
            "gpt-4-turbo": ModelInfo(
                name="gpt-4-turbo",
                description="GPT-4 Turbo",
                context_length=128000,
                supports_chat=True,
                supports_completion=True,
                supports_streaming=True
            ),
            "gpt-3.5-turbo": ModelInfo(
                name="gpt-3.5-turbo",
                description="GPT-3.5 Turbo",
                context_length=4096,
                supports_chat=True,
                supports_completion=True,
                supports_streaming=True
            ),
            "gpt-3.5-turbo-16k": ModelInfo(
                name="gpt-3.5-turbo-16k",
                description="GPT-3.5 Turbo 16K",
                context_length=16384,
                supports_chat=True,
                supports_completion=True,
                supports_streaming=True
            ),
        }
        
        # 返回已知模型信息或默认信息
        return model_info_map.get(
            self.model_name,
            ModelInfo(
                name=self.model_name,
                description=f"Custom Model: {self.model_name}",
                context_length=4096,
                supports_chat=True,
                supports_completion=True,
                supports_streaming=False
            )
        )
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        测试API连接是否正常
        
        Returns:
            bool: 是否正常工作
        """
        try:
            # 尝试获取模型列表
            await self._client.models.list()
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """
        关闭客户端连接
        """
        if self._client:
            await self._client.close()
        self._initialized = False
    
    def get_config_source(self) -> Dict[str, str]:
        """
        获取配置来源信息
        
        用于调试，了解api_key和base_url是从哪里加载的
        
        Returns:
            Dict: 配置来源字典
        """
        return getattr(self, '_config_source', {
            "api_key": "未知",
            "base_url": "未知"
        })
    
    @classmethod
    def from_config(
        cls, 
        config_dict: Dict[str, Any],
        config_path: Optional[str] = None
    ) -> "OpenAIModel":
        """
        从配置字典创建模型实例
        
        支持从字典和YAML配置文件加载配置
        
        Args:
            config_dict: 配置字典
            config_path: YAML配置文件路径（可选）
        
        Returns:
            OpenAIModel: 模型实例
        """
        # 如果指定了配置文件路径，也从文件加载
        yaml_config = {}
        if config_path and Path(config_path).exists():
            yaml_config = _load_yaml_config(config_path)
        
        # 合并配置（字典配置优先于文件配置）
        merged_config = {}
        if yaml_config:
            # 从yaml的models.openai路径获取
            openai_config = _get_config_value(yaml_config, "models", "openai", default={})
            merged_config.update(openai_config)
        merged_config.update(config_dict)
        
        model_config = ModelConfig(
            name=merged_config.get("model", merged_config.get("default_model", "gpt-3.5-turbo")),
            model_type=ModelType.OPENAI,
            temperature=merged_config.get("temperature", 0.0),
            max_tokens=merged_config.get("max_tokens", 512),
            timeout=merged_config.get("timeout", 30),
            max_retries=merged_config.get("max_retries", 3)
        )
        
        return cls(
            config=model_config,
            api_key=merged_config.get("api_key"),
            base_url=merged_config.get("base_url"),
            model_name=merged_config.get("model") or merged_config.get("default_model"),
            config_path=config_path
        )
