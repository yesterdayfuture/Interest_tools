"""
模型基类模块

定义所有模型接口的通用接口和基础功能
支持同步和异步推理
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, AsyncIterator, Iterator
from enum import Enum


class ModelType(Enum):
    """模型类型枚举"""
    OPENAI = "openai"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """模型配置类"""
    name: str  # 模型名称
    model_type: ModelType = ModelType.OPENAI  # 模型类型
    temperature: float = 0.7  # 采样温度
    max_tokens: int = 512  # 最大生成token数
    top_p: float = 1.0  # 核采样参数
    top_k: int = 50  # Top-k采样参数
    repetition_penalty: float = 1.0  # 重复惩罚
    stop_sequences: List[str] = field(default_factory=list)  # 停止序列
    timeout: int = 30  # 超时时间（秒）
    max_retries: int = 3  # 最大重试次数
    batch_size: int = 1  # 批处理大小


@dataclass
class GenerationResult:
    """生成结果数据类"""
    text: str  # 生成的文本
    prompt_tokens: int = 0  # 提示token数
    completion_tokens: int = 0  # 生成token数
    total_tokens: int = 0  # 总token数
    latency_ms: float = 0.0  # 延迟（毫秒）
    finish_reason: Optional[str] = None  # 完成原因
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据


@dataclass
class ModelInfo:
    """模型信息数据类"""
    name: str
    description: str = ""
    context_length: int = 4096
    supports_chat: bool = True
    supports_completion: bool = True
    supports_streaming: bool = False


class BaseModel(ABC):
    """
    模型基类
    
    所有模型接口（OpenAI API、本地模型等）都应继承此类
    提供统一的推理接口和性能监控功能
    """
    
    def __init__(self, config: ModelConfig):
        """
        初始化模型
        
        Args:
            config: 模型配置对象
        """
        self.config = config
        self._initialized = False
        self._request_count = 0
        self._total_latency = 0.0
        self._total_tokens = 0
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化模型
        
        子类必须实现此方法，用于加载模型或建立API连接
        """
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs
    ) -> GenerationResult:
        """
        生成文本（同步/异步统一接口）
        
        Args:
            prompt: 输入提示
            **kwargs: 额外生成参数（覆盖config中的设置）
        
        Returns:
            GenerationResult: 生成结果
        """
        pass
    
    @abstractmethod
    async def batch_generate(
        self,
        prompts: List[str],
        **kwargs
    ) -> List[GenerationResult]:
        """
        批量生成文本
        
        Args:
            prompts: 输入提示列表
            **kwargs: 额外生成参数
        
        Returns:
            List[GenerationResult]: 生成结果列表
        """
        pass
    
    async def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 额外生成参数
        
        Yields:
            str: 生成的文本片段
        """
        # 默认实现：非流式生成后逐字返回
        result = await self.generate(prompt, **kwargs)
        for char in result.text:
            yield char
            await self._async_sleep(0.01)  # 模拟流式效果
    
    @abstractmethod
    async def get_model_info(self) -> ModelInfo:
        """
        获取模型信息
        
        Returns:
            ModelInfo: 模型信息对象
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 模型是否正常工作
        """
        pass
    
    async def close(self) -> None:
        """
        关闭模型连接
        
        子类可根据需要重写此方法
        """
        self._initialized = False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取模型使用统计
        
        Returns:
            Dict: 统计信息字典
        """
        avg_latency = (
            self._total_latency / self._request_count
            if self._request_count > 0 else 0.0
        )
        
        return {
            "model_name": self.config.name,
            "model_type": self.config.model_type.value,
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "avg_latency_ms": round(avg_latency, 2),
            "initialized": self._initialized
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._request_count = 0
        self._total_latency = 0.0
        self._total_tokens = 0
    
    def _update_statistics(self, latency_ms: float, tokens: int) -> None:
        """
        更新统计信息
        
        Args:
            latency_ms: 延迟（毫秒）
            tokens: token数量
        """
        self._request_count += 1
        self._total_latency += latency_ms
        self._total_tokens += tokens
    
    def _merge_generation_params(self, **kwargs) -> Dict[str, Any]:
        """
        合并生成参数
        
        将config中的默认参数与传入的参数合并
        
        Args:
            **kwargs: 用户传入的参数
        
        Returns:
            Dict: 合并后的参数字典
        """
        params = {
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "repetition_penalty": self.config.repetition_penalty,
            "stop": self.config.stop_sequences if self.config.stop_sequences else None,
        }
        
        # 用传入的参数覆盖默认参数
        params.update(kwargs)
        
        # 移除None值
        return {k: v for k, v in params.items() if v is not None}
    
    @staticmethod
    async def _async_sleep(seconds: float) -> None:
        """
        异步睡眠
        
        Args:
            seconds: 睡眠时间（秒）
        """
        import asyncio
        await asyncio.sleep(seconds)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except Exception:
            pass
