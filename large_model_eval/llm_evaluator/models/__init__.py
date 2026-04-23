"""模型接口模块"""

from .base import BaseModel, ModelConfig, ModelType
from .openai_model import OpenAIModel
from .local_model import LocalModel

__all__ = ["BaseModel", "ModelConfig", "ModelType", "OpenAIModel", "LocalModel"]
