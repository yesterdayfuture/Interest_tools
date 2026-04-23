"""
C-Eval数据集模块

C-Eval (Chinese Evaluation)
由上海交通大学和清华大学联合开发的中文大模型评测基准
包含13,948道多项选择题，涵盖初中、高中、大学、专业四个难度级别
覆盖52个学科领域

难度级别:
- middle_school: 初中
- high_school: 高中
- college: 大学
- professional: 专业
"""

from pathlib import Path
from typing import List, Optional
from .base import BaseDataset, DatasetConfig, Sample, TaskType


class CEvalDataset(BaseDataset):
    """
    C-Eval数据集类
    
    专门用于评估大语言模型在中文知识理解方面的能力
    """
    
    # C-Eval学科分类
    SUBJECTS = {
        "middle_school": [
            "初一历史", "初一政治", "初一地理", "初一生物",
            "初二历史", "初二政治", "初二地理", "初二生物",
            "初三历史", "初三政治", "初三地理", "初三生物",
            "初中化学", "初中物理", "初中数学"
        ],
        "high_school": [
            "高一历史", "高一政治", "高一地理", "高一生物",
            "高二历史", "高二政治", "高二地理", "高二生物",
            "高三历史", "高三政治", "高三地理", "高三生物",
            "高中化学", "高中物理", "高中数学", "高中英语", "高中语文"
        ],
        "college": [
            "大学化学", "大学物理", "高等数学", "线性代数",
            "概率统计", "离散数学", "操作系统", "计算机网络",
            "数据库原理", "软件工程", "编译原理", "计算机组成原理",
            "数据结构", "算法设计与分析"
        ],
        "professional": [
            "法律职业资格考试", "医师资格考试", "注册会计师",
            "注册建筑师", "教师资格考试", "公务员考试",
            "研究生入学考试", "经济学", "管理学", "教育学",
            "心理学", "社会学", "中国语言文学", "外国语言文学"
        ]
    }
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """
        初始化C-Eval数据集
        
        Args:
            config: 数据集配置，如果为None则使用默认配置
        """
        if config is None:
            config = DatasetConfig(
                name="ceval",
                description="Chinese Evaluation Dataset",
                task_type=TaskType.MULTIPLE_CHOICE,
                data_dir="./data/ceval"
            )
        super().__init__(config)
    
    def load_data(self) -> None:
        """
        加载C-Eval数据集
        
        从data_dir目录加载所有JSON数据文件
        """
        data_dir = Path(self.config.data_dir)
        
        # 如果目录不存在，尝试使用示例数据
        if not data_dir.exists():
            data_dir = Path("./data")
        
        # 查找所有JSON文件
        json_files = list(data_dir.glob("*ceval*.json")) + list(data_dir.glob("*ceval*.jsonl"))
        
        # 如果没有找到文件，创建示例数据
        if not json_files:
            self._create_sample_data()
            return
        
        # 加载数据文件
        for file_path in json_files:
            try:
                data = self.load_json_data(str(file_path))
                # 处理不同格式
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]
                
                for idx, item in enumerate(data):
                    sample = self._parse_sample(item, f"{file_path.stem}_{idx}")
                    if sample:
                        self.samples.append(sample)
            except Exception as e:
                print(f"加载文件 {file_path} 失败: {e}")
        
        # 数据后处理
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
            question = item.get("question", item.get("stem", ""))
            
            # 提取选项
            choices = []
            for key in ["A", "B", "C", "D", "a", "b", "c", "d"]:
                if key in item:
                    choices.append(item[key])
            
            # 如果没有找到选项，尝试其他格式
            if not choices:
                choices = item.get("choices", [])
            
            # 提取答案
            answer = item.get("answer", item.get("label", ""))
            
            # 提取学科和难度
            subject = item.get("subject", item.get("category", "其他"))
            difficulty = self._get_difficulty_level(subject)
            
            # 提取解释（如果有）
            explanation = item.get("explanation", "")
            
            return Sample(
                id=sample_id,
                question=question,
                choices=choices if choices else None,
                answer=str(answer).strip().upper() if answer else None,
                category=subject,
                difficulty=difficulty,
                metadata={
                    "explanation": explanation,
                    "num_choices": len(choices) if choices else 0
                }
            )
        except Exception:
            return None
    
    def _get_difficulty_level(self, subject: str) -> str:
        """
        根据学科名称确定难度级别
        
        Args:
            subject: 学科名称
        
        Returns:
            str: 难度级别
        """
        for level, subjects in self.SUBJECTS.items():
            if subject in subjects:
                return level
        
        # 根据关键词推断
        if "初中" in subject or "初一" in subject or "初二" in subject or "初三" in subject:
            return "middle_school"
        elif "高中" in subject or "高一" in subject or "高二" in subject or "高三" in subject:
            return "high_school"
        elif "大学" in subject:
            return "college"
        else:
            return "professional"
    
    def _post_process(self) -> None:
        """
        数据后处理
        """
        # 过滤无效样本
        self.samples = [
            s for s in self.samples
            if s.question and s.answer and len(s.question) > 5
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
        """
        sample_data = [
            {
                "question": "下列哪个选项是正确的？中国的首都是____。",
                "A": "上海",
                "B": "北京",
                "C": "广州",
                "D": "深圳",
                "answer": "B",
                "subject": "初中地理",
                "explanation": "中国的首都是北京。"
            },
            {
                "question": "'举头望明月，低头思故乡'出自哪位诗人？",
                "A": "杜甫",
                "B": "李白",
                "C": "王维",
                "D": "白居易",
                "answer": "B",
                "subject": "初中语文",
                "explanation": "这句诗出自李白的《静夜思》。"
            },
            {
                "question": "Python中列表(list)和元组(tuple)的主要区别是？",
                "A": "列表是有序的，元组是无序的",
                "B": "列表可以修改，元组不可修改",
                "C": "列表只能存储数字，元组可以存储任何类型",
                "D": "列表和元组没有区别",
                "answer": "B",
                "subject": "计算机",
                "explanation": "列表是可变对象，可以修改；元组是不可变对象，创建后不能修改。"
            },
            {
                "question": "在经济学中，GDP是指？",
                "A": "国内生产总值",
                "B": "国民生产总值",
                "C": "人均国内生产总值",
                "D": "消费者价格指数",
                "answer": "A",
                "subject": "经济学",
                "explanation": "GDP(Gross Domestic Product)指国内生产总值。"
            },
            {
                "question": "牛顿第二定律的公式是？",
                "A": "F = ma",
                "B": "E = mc²",
                "C": "F = Gm₁m₂/r²",
                "D": "P = IV",
                "answer": "A",
                "subject": "高中物理",
                "explanation": "牛顿第二定律：物体的加速度与作用力成正比，与质量成反比，F = ma。"
            }
        ]
        
        for idx, item in enumerate(sample_data):
            sample = self._parse_sample(item, f"ceval_sample_{idx}")
            if sample:
                self.samples.append(sample)
        
        self._loaded = True
    
    def get_prompt_template(self, sample: Sample) -> str:
        """
        获取C-Eval提示模板
        
        Args:
            sample: 数据样本
        
        Returns:
            str: 格式化后的提示文本
        """
        if not sample.choices:
            return sample.question
        
        # 构建选项文本
        choice_labels = ["A", "B", "C", "D"]
        choice_text = "\n".join([
            f"{label}. {choice}"
            for label, choice in zip(choice_labels[:len(sample.choices)], sample.choices)
        ])
        
        # 构建完整提示（中文风格）
        prompt = f"""以下是一道选择题，请选出正确答案。

{sample.question}

{choice_text}

答案是："""
        
        return prompt
    
    def get_difficulty_distribution(self) -> dict:
        """
        获取难度分布统计
        
        Returns:
            dict: 各难度级别的样本数量
        """
        distribution = {
            "middle_school": 0,
            "high_school": 0,
            "college": 0,
            "professional": 0
        }
        
        for sample in self.samples:
            if sample.difficulty in distribution:
                distribution[sample.difficulty] += 1
        
        return distribution
    
    def get_by_difficulty(self, difficulty: str) -> List[Sample]:
        """
        按难度级别获取样本
        
        Args:
            difficulty: 难度级别
        
        Returns:
            List[Sample]: 该难度下的样本列表
        """
        if not self._loaded:
            self.load_data()
        
        return [s for s in self.samples if s.difficulty == difficulty]
    
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
        
        # 清理预测文本
        pred_clean = prediction.strip().upper()
        ref_clean = reference.strip().upper()
        
        # 直接匹配
        if pred_clean == ref_clean:
            return True
        
        # 从文本中提取第一个选项字母
        import re
        match = re.search(r'\b([A-D])\b', pred_clean)
        if match:
            return match.group(1) == ref_clean
        
        # 检查是否包含选项内容
        if ref_clean in ["A", "B", "C", "D"]:
            if f"选项{ref_clean}" in prediction or f"选{ref_clean}" in prediction:
                return True
        
        return False
