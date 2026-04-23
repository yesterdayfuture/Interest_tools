"""
数据集基类模块

定义所有评估数据集的通用接口和基础功能
"""

import json
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Tuple
from enum import Enum


class TaskType(Enum):
    """任务类型枚举"""
    MULTIPLE_CHOICE = "multiple_choice"  # 选择题
    GENERATION = "generation"  # 生成任务
    CLASSIFICATION = "classification"  # 分类任务
    QA = "question_answering"  # 问答任务


@dataclass
class DatasetConfig:
    """数据集配置类"""
    name: str  # 数据集名称
    description: Optional[str] = None # 数据集描述
    task_type: TaskType = TaskType.MULTIPLE_CHOICE  # 任务类型
    data_dir: str = "./data"  # 数据存储目录
    max_samples: int = -1  # 最大样本数，-1表示全部
    shuffle: bool = False  # 是否打乱数据
    seed: int = 42  # 随机种子
    split: str = "test"  # 数据集划分（train/test/val）


@dataclass
class Sample:
    """数据样本类"""
    id: str  # 样本唯一标识
    question: str  # 问题/提示
    choices: Optional[List[str]] = None  # 选项列表（选择题）
    answer: Optional[str] = None  # 标准答案
    context: Optional[str] = None  # 上下文信息
    category: Optional[str] = None  # 类别/学科
    difficulty: Optional[str] = None  # 难度级别
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据


class BaseDataset(ABC):
    """
    数据集基类
    
    所有评估数据集都应继承此类，并实现相应接口
    """
    
    def __init__(self, config: DatasetConfig):
        """
        初始化数据集
        
        Args:
            config: 数据集配置对象
        """
        self.config = config
        self.samples: List[Sample] = []
        self._loaded = False
        
        # 设置随机种子
        random.seed(config.seed)
    
    @abstractmethod
    def load_data(self) -> None:
        """
        加载数据集
        
        子类必须实现此方法，用于加载具体的数据文件
        """
        pass
    
    @abstractmethod
    def get_prompt_template(self, sample: Sample) -> str:
        """
        获取提示模板
        
        子类必须实现此方法，用于构建模型输入提示
        
        Args:
            sample: 数据样本
        
        Returns:
            str: 格式化后的提示文本
        """
        pass
    
    def __len__(self) -> int:
        """获取数据集大小"""
        if not self._loaded:
            self.load_data()
        return len(self.samples)
    
    def __iter__(self) -> Iterator[Sample]:
        """迭代数据集"""
        if not self._loaded:
            self.load_data()
        return iter(self.samples)
    
    def __getitem__(self, index: int) -> Sample:
        """获取指定索引的样本"""
        if not self._loaded:
            self.load_data()
        return self.samples[index]
    
    def get_batch(self, batch_size: int, start_idx: int = 0) -> List[Sample]:
        """
        获取批次数据
        
        Args:
            batch_size: 批次大小
            start_idx: 起始索引
        
        Returns:
            List[Sample]: 样本列表
        """
        if not self._loaded:
            self.load_data()
        
        end_idx = min(start_idx + batch_size, len(self.samples))
        return self.samples[start_idx:end_idx]
    
    def get_by_category(self, category: str) -> List[Sample]:
        """
        按类别获取样本
        
        Args:
            category: 类别名称
        
        Returns:
            List[Sample]: 该类别下的所有样本
        """
        if not self._loaded:
            self.load_data()
        
        return [s for s in self.samples if s.category == category]
    
    def get_categories(self) -> List[str]:
        """
        获取所有类别
        
        Returns:
            List[str]: 类别列表
        """
        if not self._loaded:
            self.load_data()
        
        categories = set(s.category for s in self.samples if s.category)
        return sorted(list(categories))
    
    def filter(self, **kwargs) -> List[Sample]:
        """
        根据条件过滤样本
        
        Args:
            **kwargs: 过滤条件（如category="math", difficulty="hard"）
        
        Returns:
            List[Sample]: 过滤后的样本列表
        """
        if not self._loaded:
            self.load_data()
        
        result = self.samples
        for key, value in kwargs.items():
            result = [s for s in result if getattr(s, key, None) == value]
        
        return result
    
    def load_json_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        从JSON文件加载数据
        
        Args:
            file_path: JSON文件路径
        
        Returns:
            List[Dict]: 数据列表
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix == '.jsonl':
                # JSON Lines格式
                data = [json.loads(line) for line in f if line.strip()]
            else:
                # 标准JSON格式
                data = json.load(f)
        
        return data if isinstance(data, list) else [data]
    
    def save_json_data(self, data: List[Dict[str, Any]], file_path: str) -> None:
        """
        保存数据到JSON文件
        
        Args:
            data: 数据列表
            file_path: 保存路径
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix == '.jsonl':
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def split_by_ratio(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1
    ) -> Tuple[List[Sample], List[Sample], List[Sample]]:
        """
        按比例划分数据集
        
        Args:
            train_ratio: 训练集比例
            val_ratio: 验证集比例
            test_ratio: 测试集比例
        
        Returns:
            Tuple: (train_samples, val_samples, test_samples)
        """
        if not self._loaded:
            self.load_data()
        
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "比例之和必须等于1"
        
        samples = self.samples.copy()
        random.shuffle(samples)
        
        n = len(samples)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        return (
            samples[:train_end],
            samples[train_end:val_end],
            samples[val_end:]
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据集统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        if not self._loaded:
            self.load_data()
        
        total = len(self.samples)
        categories = self.get_categories()
        
        category_counts = {}
        for cat in categories:
            category_counts[cat] = len(self.get_by_category(cat))
        
        # 计算平均问题长度
        avg_question_length = sum(len(s.question) for s in self.samples) / total if total > 0 else 0
        
        return {
            "name": self.config.name,
            "description": self.config.description,
            "task_type": self.config.task_type.value,
            "total_samples": total,
            "num_categories": len(categories),
            "categories": categories,
            "category_distribution": category_counts,
            "avg_question_length": round(avg_question_length, 2)
        }
    
    def preview(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        预览数据集样本
        
        Args:
            n: 预览样本数量
        
        Returns:
            List[Dict]: 样本字典列表
        """
        if not self._loaded:
            self.load_data()
        
        preview_samples = self.samples[:n]
        return [
            {
                "id": s.id,
                "question": s.question[:100] + "..." if len(s.question) > 100 else s.question,
                "choices": s.choices,
                "answer": s.answer,
                "category": s.category
            }
            for s in preview_samples
        ]
