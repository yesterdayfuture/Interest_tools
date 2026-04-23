"""
HumanEval数据集模块

HumanEval 用于评估代码生成能力
包含164个编程问题，每个问题包含：
- 函数签名和文档字符串
- 多个单元测试用例

评估方式：
- 执行单元测试验证代码正确性
- 计算 pass@k 指标
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base import BaseDataset, DatasetConfig, Sample, TaskType


class HumanEvalDataset(BaseDataset):
    """
    HumanEval代码生成数据集类
    
    用于评估模型的代码生成能力
    需要模型根据函数签名和文档字符串生成正确的Python代码
    """
    
    # 编程问题类别
    CATEGORIES = {
        "string_manipulation": "字符串处理",
        "list_operations": "列表操作",
        "math": "数学计算",
        "logic": "逻辑推理",
        "algorithms": "算法",
        "data_structures": "数据结构"
    }
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """
        初始化HumanEval数据集
        
        Args:
            config: 数据集配置，如果为None则使用默认配置
        """
        if config is None:
            config = DatasetConfig(
                name="humaneval",
                description="HumanEval - 代码生成评估数据集",
                task_type=TaskType.QA,
                data_dir="./data/humaneval"
            )
        super().__init__(config)
    
    def load_data(self) -> None:
        """
        加载HumanEval数据集
        """
        data_dir = Path(self.config.data_dir)
        
        # 如果目录不存在，尝试使用示例数据
        if not data_dir.exists():
            data_dir = Path(__file__).parent.parent.parent / "data" / "humaneval"
        
        # 加载主数据集
        data_file = data_dir / f"{self.config.split}.jsonl"
        if data_file.exists():
            raw_data = []
            with open(data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        raw_data.append(json.loads(line))
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
            sample = Sample(
                id=item.get("task_id", f"he_{idx}"),
                question=item["prompt"],
                answer=item.get("canonical_solution", ""),
                metadata={
                    "entry_point": item.get("entry_point", ""),
                    "test": item.get("test", ""),
                    "prompt": item["prompt"],
                    "category": item.get("category", "general")
                }
            )
            self.samples.append(sample)
        
        # 应用样本数量限制
        if self.config.max_samples > 0:
            self.samples = self.samples[:self.config.max_samples]
    
    def _create_sample_data(self) -> None:
        """创建示例代码生成问题"""
        sample_data = [
            {
                "task_id": "he_001",
                "prompt": "def add(a, b):\n    \"\"\"返回两个数的和\n    \n    Args:\n        a: 第一个数\n        b: 第二个数\n    \n    Returns:\n        两数之和\n    \"\"\"\n",
                "canonical_solution": "    return a + b",
                "test": "def check(add):\n    assert add(2, 3) == 5\n    assert add(-1, 1) == 0\n    assert add(0, 0) == 0\n    assert add(100, 200) == 300\n\ncheck(add)",
                "entry_point": "add",
                "category": "math"
            },
            {
                "task_id": "he_002",
                "prompt": "def reverse_string(s):\n    \"\"\"反转字符串\n    \n    Args:\n        s: 输入字符串\n    \n    Returns:\n        反转后的字符串\n    \"\"\"\n",
                "canonical_solution": "    return s[::-1]",
                "test": "def check(reverse_string):\n    assert reverse_string(\"hello\") == \"olleh\"\n    assert reverse_string(\"Python\") == \"nohtyP\"\n    assert reverse_string(\"\") == \"\"\n    assert reverse_string(\"a\") == \"a\"\n\ncheck(reverse_string)",
                "entry_point": "reverse_string",
                "category": "string_manipulation"
            },
            {
                "task_id": "he_003",
                "prompt": "def is_palindrome(s):\n    \"\"\"判断字符串是否为回文\n    \n    回文是指正读反读都相同的字符串（忽略大小写和非字母字符）\n    \n    Args:\n        s: 输入字符串\n    \n    Returns:\n        如果是回文返回True，否则返回False\n    \"\"\"\n",
                "canonical_solution": "    s = ''.join(c.lower() for c in s if c.isalnum())\n    return s == s[::-1]",
                "test": "def check(is_palindrome):\n    assert is_palindrome(\"A man a plan a canal Panama\") == True\n    assert is_palindrome(\"race a car\") == False\n    assert is_palindrome(\"\") == True\n    assert is_palindrome(\"a\") == True\n    assert is_palindrome(\"Abba\") == True\n\ncheck(is_palindrome)",
                "entry_point": "is_palindrome",
                "category": "string_manipulation"
            },
            {
                "task_id": "he_004",
                "prompt": "def find_max(nums):\n    \"\"\"找出列表中的最大值\n    \n    Args:\n        nums: 数字列表\n    \n    Returns:\n        列表中的最大值\n    \n    Raises:\n        ValueError: 如果列表为空\n    \"\"\"\n",
                "canonical_solution": "    if not nums:\n        raise ValueError(\"列表不能为空\")\n    max_val = nums[0]\n    for num in nums[1:]:\n        if num > max_val:\n            max_val = num\n    return max_val",
                "test": "def check(find_max):\n    assert find_max([1, 2, 3, 4, 5]) == 5\n    assert find_max([5, 4, 3, 2, 1]) == 5\n    assert find_max([1]) == 1\n    assert find_max([-1, -2, -3]) == -1\n    try:\n        find_max([])\n        assert False, \"应该抛出ValueError\"\n    except ValueError:\n        pass\n\ncheck(find_max)",
                "entry_point": "find_max",
                "category": "list_operations"
            },
            {
                "task_id": "he_005",
                "prompt": "def fibonacci(n):\n    \"\"\"计算第n个斐波那契数\n    \n    斐波那契数列：0, 1, 1, 2, 3, 5, 8, 13...\n    F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2)\n    \n    Args:\n        n: 非负整数\n    \n    Returns:\n        第n个斐波那契数\n    \"\"\"\n",
                "canonical_solution": "    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b",
                "test": "def check(fibonacci):\n    assert fibonacci(0) == 0\n    assert fibonacci(1) == 1\n    assert fibonacci(2) == 1\n    assert fibonacci(10) == 55\n    assert fibonacci(20) == 6765\n\ncheck(fibonacci)",
                "entry_point": "fibonacci",
                "category": "algorithms"
            }
        ]
        self._parse_samples(sample_data)
    
    def get_prompt_template(self, sample: Sample) -> str:
        """
        生成HumanEval的prompt
        
        Args:
            sample: 数据样本
            
        Returns:
            str: 格式化的prompt
        """
        prompt = f"""请根据函数签名和文档字符串生成完整的Python函数实现。

要求：
1. 只生成函数体代码，不要包含测试代码
2. 确保代码能正确处理所有边界情况
3. 使用标准的Python语法

{sample.question}

请生成完整的函数实现：

```python
{sample.question}"""
        return prompt
    
    # 兼容旧方法名
    get_prompt = get_prompt_template
    
    def extract_code(self, prediction: str) -> str:
        """
        从模型输出中提取代码
        
        Args:
            prediction: 模型输出文本
            
        Returns:
            str: 提取的代码
        """
        # 尝试从代码块中提取
        code_pattern = r'```python\s*(.*?)```'
        match = re.search(code_pattern, prediction, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 如果没有代码块，尝试提取函数定义
        func_pattern = r'(def\s+\w+\([^)]*\):[^\n]*(?:\n(?:    .*|\s*))*?)(?=\n\ndef|\nclass|\Z)'
        match = re.search(func_pattern, prediction, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 直接返回预测文本（清理后）
        return prediction.strip()
    
    def evaluate_sample(
        self,
        sample: Sample,
        prediction: str,
        eval_type: str = "default"
    ) -> Dict[str, Any]:
        """
        评估代码生成结果
        
        Args:
            sample: 数据样本
            prediction: 模型预测答案
            eval_type: 评估类型
            
        Returns:
            Dict[str, Any]: 评估指标
        """
        # 提取代码
        code = self.extract_code(prediction)
        
        # 获取测试代码
        test_code = sample.metadata.get("test", "")
        entry_point = sample.metadata.get("entry_point", "")
        
        # 构建完整代码
        full_code = f"{code}\n\n{test_code}"
        
        # 执行测试（在安全环境中）
        result = self._execute_test(full_code, entry_point)
        
        return {
            "passed": result["passed"],
            "error": result.get("error", ""),
            "execution_time": result.get("execution_time", 0.0),
            "code_length": len(code),
            "has_function_def": "def " in code
        }
    
    def _execute_test(self, code: str, entry_point: str) -> Dict[str, Any]:
        """
        执行测试代码（简化版本，实际应使用沙箱环境）
        
        Args:
            code: 完整代码
            entry_point: 入口函数名
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        import time
        
        result = {
            "passed": False,
            "error": "",
            "execution_time": 0.0
        }
        
        try:
            start_time = time.time()
            
            # 创建受限的执行环境
            namespace = {
                '__builtins__': {
                    'len': len,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'int': int,
                    'float': float,
                    'str': str,
                    'list': list,
                    'dict': dict,
                    'set': set,
                    'tuple': tuple,
                    'sorted': sorted,
                    'reversed': reversed,
                    'print': print,
                    'True': True,
                    'False': False,
                    'None': None,
                    'Exception': Exception,
                    'ValueError': ValueError,
                    'TypeError': TypeError,
                    'AssertionError': AssertionError
                }
            }
            
            # 执行代码
            exec(code, namespace)
            
            result["execution_time"] = time.time() - start_time
            result["passed"] = True
            
        except AssertionError as e:
            result["error"] = f"测试失败: {str(e)}"
        except Exception as e:
            result["error"] = f"执行错误: {type(e).__name__}: {str(e)}"
        
        return result
    
    def calculate_pass_at_k(self, results: List[Dict[str, Any]], k: int = 1) -> float:
        """
        计算 pass@k 指标
        
        Args:
            results: 评估结果列表
            k: k值
            
        Returns:
            float: pass@k 值
        """
        if not results:
            return 0.0
        
        passed_count = sum(1 for r in results if r.get("passed", False))
        return passed_count / len(results)
    
    def calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        计算整体指标
        
        Args:
            results: 评估结果列表
            
        Returns:
            Dict[str, float]: 整体指标
        """
        if not results:
            return {"pass@1": 0.0}
        
        pass_at_1 = self.calculate_pass_at_k(results, k=1)
        avg_execution_time = sum(r.get("execution_time", 0) for r in results) / len(results)
        
        return {
            "pass@1": round(pass_at_1, 4),
            "avg_execution_time": round(avg_execution_time, 4)
        }
