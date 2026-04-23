"""
本地模型接口模块

支持使用HuggingFace Transformers加载本地模型
包括：GPT-2、LLaMA、ChatGLM等开源模型
"""

import os
import time
import asyncio
import torch
from typing import List, Dict, Any, Optional, AsyncIterator
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

from .base import BaseModel, ModelConfig, ModelType, GenerationResult, ModelInfo


class LocalModel(BaseModel):
    """
    本地模型类
    
    通过HuggingFace Transformers加载和运行本地模型
    """
    
    def __init__(
        self,
        config: Optional[ModelConfig] = None,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False
    ):
        """
        初始化本地模型
        
        Args:
            config: 模型配置对象
            model_path: 本地模型路径或HuggingFace模型名称
            device: 运行设备（auto/cpu/cuda/cuda:0等）
            load_in_8bit: 是否使用8位量化加载
            load_in_4bit: 是否使用4位量化加载
        """
        if config is None:
            config = ModelConfig(
                name=model_path or "gpt2",
                model_type=ModelType.LOCAL,
                temperature=0.7,
                max_tokens=512
            )
        
        super().__init__(config)
        
        self.model_path = model_path or config.name
        self.device = self._get_device(device)
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        
        # 模型和分词器（延迟初始化）
        self._tokenizer: Optional[AutoTokenizer] = None
        self._model: Optional[AutoModelForCausalLM] = None
        self._generation_config: Optional[GenerationConfig] = None
    
    def _get_device(self, device: Optional[str]) -> str:
        """
        确定运行设备
        
        Args:
            device: 指定的设备
        
        Returns:
            str: 实际使用的设备
        """
        if device and device != "auto":
            return device
        
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    async def initialize(self) -> None:
        """
        初始化模型和分词器
        
        加载预训练模型和对应的分词器
        """
        if self._initialized:
            return
        
        try:
            print(f"正在加载模型: {self.model_path}")
            print(f"使用设备: {self.device}")
            
            # 加载分词器
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                padding_side="left"
            )
            
            # 设置pad token（如果未设置）
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # 准备加载参数
            load_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
            }
            
            # 量化加载选项
            if self.load_in_4bit:
                load_kwargs["load_in_4bit"] = True
                load_kwargs["device_map"] = "auto"
            elif self.load_in_8bit:
                load_kwargs["load_in_8bit"] = True
                load_kwargs["device_map"] = "auto"
            else:
                load_kwargs["device_map"] = self.device
            
            # 加载模型
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **load_kwargs
            )
            
            # 如果不是量化模型，显式设置设备
            if not self.load_in_8bit and not self.load_in_4bit:
                self._model = self._model.to(self.device)
            
            # 设置评估模式
            self._model.eval()
            
            # 初始化生成配置
            self._generation_config = GenerationConfig.from_pretrained(
                self.model_path
            ) if os.path.exists(os.path.join(self.model_path, "generation_config.json")) else None
            
            self._initialized = True
            print(f"模型加载完成: {self.model_path}")
            
        except Exception as e:
            raise RuntimeError(f"模型加载失败: {e}")
    
    async def generate(
        self,
        prompt: str,
        **kwargs
    ) -> GenerationResult:
        """
        生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 额外生成参数
        
        Returns:
            GenerationResult: 生成结果
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 编码输入
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048
            )
            
            # 移动输入到设备
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 获取prompt的token数
            prompt_tokens = inputs["input_ids"].shape[1]
            
            # 合并参数
            params = self._merge_generation_params(**kwargs)
            
            # 生成
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=params.get("max_tokens", 512),
                    temperature=params.get("temperature", 0.7) if params.get("temperature", 0.7) > 0 else None,
                    top_p=params.get("top_p", 1.0),
                    top_k=params.get("top_k", 50),
                    repetition_penalty=params.get("repetition_penalty", 1.0),
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=self._tokenizer.eos_token_id,
                    do_sample=params.get("temperature", 0.7) > 0,
                    num_return_sequences=1
                )
            
            # 计算延迟
            latency_ms = (time.time() - start_time) * 1000
            
            # 解码输出
            # 只取生成的部分（去除输入prompt）
            generated_tokens = outputs[0][prompt_tokens:]
            generated_text = self._tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True
            )
            
            completion_tokens = len(generated_tokens)
            total_tokens = prompt_tokens + completion_tokens
            
            # 更新统计
            self._update_statistics(latency_ms, total_tokens)
            
            return GenerationResult(
                text=generated_text.strip(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                finish_reason="stop",
                metadata={
                    "device": self.device,
                    "model_path": self.model_path
                }
            )
            
        except Exception as e:
            raise RuntimeError(f"生成失败: {e}")
    
    async def batch_generate(
        self,
        prompts: List[str],
        **kwargs
    ) -> List[GenerationResult]:
        """
        批量生成文本
        
        使用批处理提高效率
        
        Args:
            prompts: 输入提示列表
            **kwargs: 额外生成参数
        
        Returns:
            List[GenerationResult]: 生成结果列表
        """
        if not self._initialized:
            await self.initialize()
        
        # 本地模型使用批处理生成
        start_time = time.time()
        
        try:
            # 编码所有输入
            inputs = self._tokenizer(
                prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048
            )
            
            # 移动输入到设备
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 记录每个prompt的长度
            prompt_lengths = [len(ids) for ids in inputs["input_ids"]]
            
            # 合并参数
            params = self._merge_generation_params(**kwargs)
            
            # 批量生成
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=params.get("max_tokens", 512),
                    temperature=params.get("temperature", 0.7) if params.get("temperature", 0.7) > 0 else None,
                    top_p=params.get("top_p", 1.0),
                    top_k=params.get("top_k", 50),
                    repetition_penalty=params.get("repetition_penalty", 1.0),
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=self._tokenizer.eos_token_id,
                    do_sample=params.get("temperature", 0.7) > 0
                )
            
            # 计算延迟
            latency_ms = (time.time() - start_time) * 1000
            
            # 处理每个结果
            results = []
            for i, output in enumerate(outputs):
                prompt_len = prompt_lengths[i]
                generated_tokens = output[prompt_len:]
                generated_text = self._tokenizer.decode(
                    generated_tokens,
                    skip_special_tokens=True
                )
                
                completion_tokens = len(generated_tokens)
                total_tokens = prompt_len + completion_tokens
                
                results.append(GenerationResult(
                    text=generated_text.strip(),
                    prompt_tokens=prompt_len,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms / len(prompts),  # 平均延迟
                    finish_reason="stop",
                    metadata={"batch_index": i}
                ))
                
                # 更新统计
                self._update_statistics(latency_ms / len(prompts), total_tokens)
            
            return results
            
        except Exception as e:
            # 批处理失败时回退到逐个生成
            results = []
            for prompt in prompts:
                try:
                    result = await self.generate(prompt, **kwargs)
                    results.append(result)
                except Exception as inner_e:
                    results.append(GenerationResult(
                        text="",
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        latency_ms=0.0,
                        finish_reason="error",
                        metadata={"error": str(inner_e)}
                    ))
            return results
    
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
        if not self._initialized:
            await self.initialize()
        
        # 本地模型的流式生成（逐token输出）
        try:
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            params = self._merge_generation_params(**kwargs)
            
            # 使用流式生成
            streamer = self._create_text_iterator()
            
            # 在新线程中运行生成
            import threading
            generation_thread = threading.Thread(
                target=self._generate_stream_sync,
                args=(inputs, params, streamer)
            )
            generation_thread.start()
            
            # 输出流式结果
            for text in streamer:
                yield text
                await asyncio.sleep(0.01)
            
            generation_thread.join()
            
        except Exception as e:
            raise RuntimeError(f"流式生成失败: {e}")
    
    def _create_text_iterator(self):
        """创建文本迭代器"""
        from transformers import TextIteratorStreamer
        return TextIteratorStreamer(
            self._tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
    
    def _generate_stream_sync(self, inputs, params, streamer):
        """同步流式生成（在线程中运行）"""
        try:
            self._model.generate(
                **inputs,
                max_new_tokens=params.get("max_tokens", 512),
                temperature=params.get("temperature", 0.7) if params.get("temperature", 0.7) > 0 else None,
                top_p=params.get("top_p", 1.0),
                streamer=streamer,
                do_sample=params.get("temperature", 0.7) > 0
            )
        except Exception:
            pass
    
    async def get_model_info(self) -> ModelInfo:
        """
        获取模型信息
        
        Returns:
            ModelInfo: 模型信息对象
        """
        if not self._initialized:
            await self.initialize()
        
        # 获取模型配置
        config = self._model.config
        
        # 获取上下文长度
        context_length = getattr(
            config,
            "max_position_embeddings",
            getattr(config, "n_positions", 2048)
        )
        
        return ModelInfo(
            name=self.model_path,
            description=f"Local Model: {self.model_path}",
            context_length=context_length,
            supports_chat=False,
            supports_completion=True,
            supports_streaming=True
        )
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 模型是否正常工作
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # 尝试一次简单生成
            test_result = await self.generate("Hello", max_tokens=5)
            return test_result.text is not None
            
        except Exception:
            return False
    
    async def close(self) -> None:
        """
        释放模型资源
        """
        if self._model:
            del self._model
            self._model = None
        
        if self._tokenizer:
            del self._tokenizer
            self._tokenizer = None
        
        # 清理GPU缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self._initialized = False
    
    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]) -> "LocalModel":
        """
        从配置字典创建模型实例
        
        Args:
            config_dict: 配置字典
        
        Returns:
            LocalModel: 模型实例
        """
        model_config = ModelConfig(
            name=config_dict.get("model_path", "gpt2"),
            model_type=ModelType.LOCAL,
            temperature=config_dict.get("temperature", 0.7),
            max_tokens=config_dict.get("max_tokens", 512)
        )
        
        return cls(
            config=model_config,
            model_path=config_dict.get("model_path"),
            device=config_dict.get("device", "auto"),
            load_in_8bit=config_dict.get("load_in_8bit", False),
            load_in_4bit=config_dict.get("load_in_4bit", False)
        )
