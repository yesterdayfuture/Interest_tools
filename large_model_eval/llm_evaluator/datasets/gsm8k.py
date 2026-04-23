"""
GSM8K数据集模块

GSM8K (Grade School Math 8K)
包含8500道小学数学应用题，需要多步推理才能解决

数据集特点：
- 每道题需要2-8步推理
- 答案为整数
- 包含详细的解答过程
- 评估模型数学推理能力
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base import BaseDataset, DatasetConfig, Sample, TaskType


class GSM8KDataset(BaseDataset):
    """
    GSM8K数学推理数据集类
    
    用于评估模型的数学推理和多步计算能力
    题目为小学水平，但需要仔细推理
    """
    
    # 数学问题类别
    CATEGORIES = {
        "arithmetic": "基础算术",
        "fractions": "分数运算",
        "percentages": "百分比",
        "ratios": "比例问题",
        "algebra": "代数问题",
        "geometry": "几何问题",
        "word_problems": "应用题"
    }
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """
        初始化GSM8K数据集
        
        Args:
            config: 数据集配置，如果为None则使用默认配置
        """
        if config is None:
            config = DatasetConfig(
                name="gsm8k",
                description="GSM8K - 小学数学推理数据集",
                task_type=TaskType.QA,
                data_dir="./data/gsm8k"
            )
        super().__init__(config)
    
    def load_data(self) -> None:
        """
        加载GSM8K数据集
        
        从data_dir目录加载JSON数据文件
        """
        data_dir = Path(self.config.data_dir)
        
        # 如果目录不存在，尝试使用示例数据
        if not data_dir.exists():
            data_dir = Path(__file__).parent.parent.parent / "data" / "gsm8k"
        
        # 加载主数据集
        data_file = data_dir / f"{self.config.split}.json"
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                self._parse_samples(raw_data)
        else:
            # 如果找不到文件，创建示例数据
            self._create_sample_data()
    
    def _parse_samples(self, raw_data: List[Dict[str, Any]]) -> None:
        """
        解析原始数据为Sample对象
        
        Args:
            raw_data: 原始数据列表
        """
        self.samples = []
        for idx, item in enumerate(raw_data):
            # 提取答案数字
            answer_text = item.get("answer", "")
            numeric_answer = self._extract_answer(answer_text)
            
            sample = Sample(
                id=str(item.get("id", f"gsm_{idx}")),
                question=item["question"],
                answer=str(numeric_answer),
                metadata={
                    "full_solution": answer_text,
                    "numeric_answer": numeric_answer,
                    "difficulty": item.get("difficulty", "medium"),
                    "category": item.get("category", "word_problems")
                }
            )
            self.samples.append(sample)
        
        # 应用样本数量限制
        if self.config.max_samples > 0:
            self.samples = self.samples[:self.config.max_samples]
    
    def _extract_answer(self, answer_text: str) -> int:
        """
        从答案文本中提取数字
        
        Args:
            answer_text: 答案文本
            
        Returns:
            int: 提取的数字，默认返回0
        """
        # 匹配 #### 后面的数字（GSM8K格式）
        match = re.search(r'####\s*(-?\d+)', answer_text)
        if match:
            return int(match.group(1))
        
        # 否则匹配文本中的最后一个数字
        numbers = re.findall(r'-?\d+', answer_text)
        if numbers:
            return int(numbers[-1])
        
        return 0
    
    def _create_sample_data(self) -> None:
        """创建示例数学问题用于测试"""
        sample_data = [
            {
                "id": "gsm_001",
                "question": "小明有5个苹果，小红给了他3个苹果，然后小明吃掉了2个。小明现在有多少个苹果？",
                "answer": "小明开始有5个苹果。小红给了他3个，所以他有 5 + 3 = 8 个苹果。然后他吃掉了2个，所以剩下 8 - 2 = 6 个苹果。\n\n#### 6",
                "difficulty": "easy",
                "category": "arithmetic"
            },
            {
                "id": "gsm_002",
                "question": "一个长方形的长是12厘米，宽是8厘米。这个长方形的周长是多少厘米？",
                "answer": "长方形的周长公式是：周长 = 2 × (长 + 宽)。\n所以周长 = 2 × (12 + 8) = 2 × 20 = 40 厘米。\n\n#### 40",
                "difficulty": "easy",
                "category": "geometry"
            },
            {
                "id": "gsm_003",
                "question": "商店里一件T恤原价80元，现在打7折出售。小王买了2件，他一共花了多少钱？",
                "answer": "首先计算打折后的价格：80 × 0.7 = 56 元。\n然后计算2件的总价：56 × 2 = 112 元。\n\n#### 112",
                "difficulty": "medium",
                "category": "percentages"
            },
            {
                "id": "gsm_004",
                "question": "甲乙两地相距360公里。一辆汽车从甲地开往乙地，前3小时每小时行驶60公里，剩下的路程需要在2小时内完成。剩下的路程平均每小时需要行驶多少公里？",
                "answer": "前3小时行驶的距离：60 × 3 = 180 公里。\n剩下的路程：360 - 180 = 180 公里。\n需要在2小时内完成，所以速度为：180 ÷ 2 = 90 公里/小时。\n\n#### 90",
                "difficulty": "medium",
                "category": "word_problems"
            },
            {
                "id": "gsm_005",
                "question": "班级里有30名学生，其中2/5是女生。男生有多少人？",
                "answer": "女生人数：30 × 2/5 = 12 人。\n男生人数：30 - 12 = 18 人。\n或者：男生占 1 - 2/5 = 3/5，所以男生人数 = 30 × 3/5 = 18 人。\n\n#### 18",
                "difficulty": "medium",
                "category": "fractions"
            },
            {
                "id": "gsm_006",
                "question": "一个水池有两个进水管。甲管单独注满需要6小时，乙管单独注满需要4小时。如果两个管子同时打开，需要多少小时注满水池？",
                "answer": "甲管每小时注入 1/6 的水池。\n乙管每小时注入 1/4 的水池。\n两管同时每小时注入：1/6 + 1/4 = 2/12 + 3/12 = 5/12 的水池。\n注满需要的时间：1 ÷ (5/12) = 12/5 = 2.4 小时。\n\n#### 2.4",
                "difficulty": "hard",
                "category": "ratios"
            }
        ]
        self._parse_samples(sample_data)
    
    def get_prompt_template(self, sample: Sample) -> str:
        """
        生成GSM8K的prompt
        
        Args:
            sample: 数据样本
            
        Returns:
            str: 格式化的prompt
        """
        prompt = f"""请解决以下数学问题。你需要：
1. 逐步展示推理过程
2. 最后以 #### 数字 的格式给出最终答案

问题：{sample.question}

解答："""
        return prompt
    
    # 兼容旧方法名
    get_prompt = get_prompt_template
    
    def evaluate_sample(
        self,
        sample: Sample,
        prediction: str,
        eval_type: str = "default"
    ) -> Dict[str, Any]:
        """
        评估数学问题的答案
        
        Args:
            sample: 数据样本
            prediction: 模型预测答案
            eval_type: 评估类型
            
        Returns:
            Dict[str, Any]: 评估指标
        """
        # 提取预测答案中的数字
        pred_answer = self._extract_answer(prediction)
        correct_answer = sample.metadata.get("numeric_answer", 0)
        
        # 数值正确性
        is_correct = pred_answer == correct_answer
        
        # 评估解答过程（可选）
        has_reasoning = self._check_reasoning(prediction)
        
        # 检查格式
        has_correct_format = "####" in prediction
        
        return {
            "correct": is_correct,
            "predicted_answer": pred_answer,
            "correct_answer": correct_answer,
            "has_reasoning": has_reasoning,
            "has_correct_format": has_correct_format,
            "accuracy": 1.0 if is_correct else 0.0
        }
    
    def _check_reasoning(self, prediction: str) -> bool:
        """
        检查是否有推理过程
        
        Args:
            prediction: 预测文本
            
        Returns:
            bool: 是否有推理过程
        """
        # 检查是否包含常见的推理关键词
        reasoning_indicators = [
            "所以", "因此", "首先", "然后", "接着",
            "第一步", "第二步", "计算", "等于", "得出"
        ]
        return any(indicator in prediction for indicator in reasoning_indicators)
    
    def calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        计算整体指标
        
        Args:
            results: 评估结果列表
            
        Returns:
            Dict[str, float]: 整体指标
        """
        if not results:
            return {"accuracy": 0.0}
        
        correct_count = sum(1 for r in results if r.get("correct", False))
        reasoning_count = sum(1 for r in results if r.get("has_reasoning", False))
        format_count = sum(1 for r in results if r.get("has_correct_format", False))
        
        total = len(results)
        
        return {
            "accuracy": round(correct_count / total, 4),
            "reasoning_rate": round(reasoning_count / total, 4),
            "format_compliance": round(format_count / total, 4)
        }
