"""
MMLU数据集模块

MMLU (Massive Multi-task Language Understanding)
覆盖57个学科领域的选择题问答任务

支持学科分类:
- humanities: 人文学科
- social_sciences: 社会科学
- stem: 科学、技术、工程、数学
- other: 其他
"""

from pathlib import Path
from typing import List, Optional
from .base import BaseDataset, DatasetConfig, Sample, TaskType


class MMLUDataset(BaseDataset):
    """
    MMLU数据集类
    
    用于评估模型在多学科选择题上的能力
    """
    
    # MMLU学科分类映射
    CATEGORIES = {
        "humanities": [
            "formal_logic", "high_school_european_history", "high_school_us_history",
            "high_school_world_history", "international_law", "jurisprudence",
            "logical_fallacies", "moral_disputes", "moral_scenarios", "philosophy",
            "prehistory", "professional_law", "world_religions"
        ],
        "social_sciences": [
            "econometrics", "high_school_geography", "high_school_government_and_politics",
            "high_school_macroeconomics", "high_school_microeconomics", "high_school_psychology",
            "human_sexuality", "professional_psychology", "public_relations", "security_studies",
            "sociology", "us_foreign_policy"
        ],
        "stem": [
            "abstract_algebra", "anatomy", "astronomy", "college_biology",
            "college_chemistry", "college_computer_science", "college_mathematics",
            "college_physics", "computer_security", "conceptual_physics",
            "electrical_engineering", "elementary_mathematics", "high_school_biology",
            "high_school_chemistry", "high_school_computer_science", "high_school_mathematics",
            "high_school_physics", "high_school_statistics", "machine_learning"
        ],
        "other": [
            "business_ethics", "clinical_knowledge", "college_medicine",
            "global_facts", "management", "marketing", "medical_genetics",
            "miscellaneous", "nutrition", "professional_accounting",
            "professional_medicine", "virology"
        ]
    }
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """
        初始化MMLU数据集
        
        Args:
            config: 数据集配置，如果为None则使用默认配置
        """
        if config is None:
            config = DatasetConfig(
                name="mmlu",
                description="Massive Multi-task Language Understanding",
                task_type=TaskType.MULTIPLE_CHOICE,
                data_dir="./data/mmlu"
            )
        super().__init__(config)
    
    def load_data(self) -> None:
        """
        加载MMLU数据集
        
        从data_dir目录加载所有JSON数据文件
        """
        data_dir = Path(self.config.data_dir)
        
        # 如果目录不存在，尝试使用示例数据
        if not data_dir.exists():
            data_dir = Path("./data")
        
        # 查找所有JSON文件
        json_files = list(data_dir.glob("*.json")) + list(data_dir.glob("*.jsonl"))
        
        # 如果没有找到文件，创建示例数据
        if not json_files:
            self._create_sample_data()
            return
        
        # 加载数据文件
        for file_path in json_files:
            try:
                data = self.load_json_data(str(file_path))
                for idx, item in enumerate(data):
                    sample = self._parse_sample(item, f"{file_path.stem}_{idx}")
                    if sample:
                        self.samples.append(sample)
            except Exception as e:
                print(f"加载文件 {file_path} 失败: {e}")
        
        # 数据预处理和过滤
        self._post_process()
        self._loaded = True
    
    def _parse_sample(self, item: dict, sample_id: str) -> Optional[Sample]:
        """
        解析数据项为Sample对象
        
        Args:
            item: 原始数据项
            sample_id: 样本ID
        
        Returns:
            Sample对象或None
        """
        try:
            # 支持多种数据格式
            question = item.get("question", "")
            choices = item.get("choices", [])
            answer = item.get("answer", "")
            category = item.get("category", item.get("subject", "other"))
            
            # 处理选项格式
            if not choices and "A" in item and "B" in item:
                # 另一种常见格式
                choices = []
                for opt in ["A", "B", "C", "D", "E"]:
                    if opt in item:
                        choices.append(item[opt])
            
            # 确定学科大类
            main_category = self._get_main_category(category)
            
            return Sample(
                id=sample_id,
                question=question,
                choices=choices if choices else None,
                answer=str(answer).strip().upper() if answer else None,
                category=main_category,
                metadata={
                    "subject": category,
                    "num_choices": len(choices) if choices else 0
                }
            )
        except Exception:
            return None
    
    def _get_main_category(self, subject: str) -> str:
        """
        获取学科的主分类
        
        Args:
            subject: 学科名称
        
        Returns:
            str: 主分类名称
        """
        subject_lower = subject.lower().replace(" ", "_")
        
        for category, subjects in self.CATEGORIES.items():
            if subject_lower in subjects or subject_lower == category:
                return category
        
        return "other"
    
    def _post_process(self) -> None:
        """
        数据后处理
        
        包括：过滤、打乱、限制样本数等
        """
        # 过滤无效样本
        self.samples = [
            s for s in self.samples
            if s.question and s.answer
        ]
        
        # 打乱数据
        if self.config.shuffle:
            import random
            random.shuffle(self.samples)
        
        # 限制样本数
        if self.config.max_samples > 0:
            self.samples = self.samples[:self.config.max_samples]
    
    def _create_sample_data(self) -> None:
        """
        创建示例数据
        
        当没有数据文件时，生成一些示例数据用于演示
        """
        sample_data = [
            {
                "question": "下列哪位哲学家提出了'我思故我在'的观点？",
                "choices": ["苏格拉底", "柏拉图", "笛卡尔", "康德"],
                "answer": "C",
                "category": "philosophy"
            },
            {
                "question": "水的化学式是什么？",
                "choices": ["CO2", "H2O", "NaCl", "O2"],
                "answer": "B",
                "category": "chemistry"
            },
            {
                "question": "第二次世界大战结束于哪一年？",
                "choices": ["1943", "1944", "1945", "1946"],
                "answer": "C",
                "category": "history"
            },
            {
                "question": "一个三角形的内角和是多少度？",
                "choices": ["90°", "180°", "270°", "360°"],
                "answer": "B",
                "category": "mathematics"
            },
            {
                "question": "Python中用于定义函数的关键字是什么？",
                "choices": ["func", "def", "function", "define"],
                "answer": "B",
                "category": "computer_science"
            }
        ]
        
        for idx, item in enumerate(sample_data):
            sample = self._parse_sample(item, f"sample_{idx}")
            if sample:
                self.samples.append(sample)
        
        self._loaded = True
    
    def get_prompt_template(self, sample: Sample) -> str:
        """
        获取MMLU提示模板
        
        构建选择题的标准提示格式
        
        Args:
            sample: 数据样本
        
        Returns:
            str: 格式化后的提示文本
        """
        if not sample.choices:
            return sample.question
        
        # 构建选项文本
        choice_labels = ["A", "B", "C", "D", "E"]
        choice_text = "\n".join([
            f"{label}. {choice}"
            for label, choice in zip(choice_labels[:len(sample.choices)], sample.choices)
        ])
        
        # 构建完整提示
        prompt = f"""问题：{sample.question}

选项：
{choice_text}

请从上述选项中选择正确答案，只回答选项字母（A、B、C或D）："""
        
        return prompt
    
    def evaluate_answer(self, prediction: str, reference: str) -> bool:
        """
        评估答案是否正确
        
        Args:
            prediction: 模型预测答案
            reference: 标准答案
        
        Returns:
            bool: 是否正确
        """
        if not prediction or not reference:
            return False
        
        # 提取选项字母
        pred_clean = prediction.strip().upper()
        ref_clean = reference.strip().upper()
        
        # 直接匹配
        if pred_clean == ref_clean:
            return True
        
        # 从文本中提取第一个选项字母
        import re
        match = re.search(r'\b([A-E])\b', pred_clean)
        if match:
            return match.group(1) == ref_clean
        
        return False
    
    def get_category_statistics(self) -> dict:
        """
        获取各分类的统计信息
        
        Returns:
            dict: 分类统计字典
        """
        stats = {}
        for category in self.CATEGORIES.keys():
            samples = self.get_by_category(category)
            if samples:
                stats[category] = {
                    "count": len(samples),
                    "percentage": len(samples) / len(self.samples) * 100
                }
        return stats
