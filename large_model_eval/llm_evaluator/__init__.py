"""
大语言模型评估系统

本系统提供全面的LLM评估功能，包括：
- 基础性能评估（准确性、效率、鲁棒性）
- 高级能力评估（生成质量、交互能力）
- 伦理安全评估（偏见、安全性、对齐）

支持多种数据集：MMLU、C-Eval、CMMLU等
支持多种模型接入：OpenAI API、本地HuggingFace模型
"""

__version__ = "1.0.0"
__author__ = "LLM Evaluator Team"

from .core.evaluator import Evaluator
from .core.metrics import MetricsCalculator

__all__ = ["Evaluator", "MetricsCalculator"]
