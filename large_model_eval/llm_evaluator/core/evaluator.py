"""
评估执行引擎模块

核心评估逻辑实现，协调数据集、模型和指标计算
支持多种评估模式和结果分析
"""

import time
import json
import asyncio
import statistics
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .metrics import (
    MetricsCalculator,
    EvaluationResult,
    AccuracyMetrics,
    PerformanceMetrics,
    RobustnessMetrics,
    GenerationMetrics,
    SafetyMetrics,
    TextGenerationMetrics
)
from ..datasets.base import BaseDataset, Sample
from ..models.base import BaseModel, GenerationResult


@dataclass
class EvaluationConfig:
    """评估配置类"""
    name: str  # 评估任务名称
    description: str = ""  # 评估描述
    batch_size: int = 8  # 批处理大小
    max_samples: int = -1  # 最大样本数，-1表示全部
    num_workers: int = 4  # 并行工作数
    seed: int = 42  # 随机种子
    save_predictions: bool = True  # 是否保存预测结果
    output_dir: str = "./results"  # 输出目录
    evaluate_performance: bool = True  # 是否评估性能
    evaluate_robustness: bool = False  # 是否评估鲁棒性
    evaluate_safety: bool = False  # 是否评估安全性


@dataclass
class EvaluationSummary:
    """评估摘要数据类"""
    eval_name: str
    model_name: str
    dataset_name: str
    total_samples: int
    accuracy: float
    avg_latency_ms: float
    total_time_seconds: float
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)


class Evaluator:
    """
    评估器类
    
    大语言模型评估的核心执行引擎
    协调数据集加载、模型推理、指标计算和结果输出
    """
    
    def __init__(self, config: EvaluationConfig):
        """
        初始化评估器
        
        Args:
            config: 评估配置
        """
        self.config = config
        self.metrics_calculator = MetricsCalculator()
        self.results: List[Dict[str, Any]] = []
        
        # 创建输出目录
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    async def evaluate(
        self,
        model: BaseModel,
        dataset: BaseDataset,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> EvaluationResult:
        """
        执行完整评估
        
        Args:
            model: 待评估模型
            dataset: 评估数据集
            progress_callback: 进度回调函数(current, total, message)
        
        Returns:
            EvaluationResult: 完整评估结果
        """
        start_time = time.time()
        
        # 确保模型已初始化
        if not hasattr(model, '_initialized') or not model._initialized:
            await model.initialize()
        
        # 加载数据集
        if not dataset._loaded:
            dataset.load_data()
        
        # 限制样本数
        samples = dataset.samples
        if self.config.max_samples > 0:
            samples = samples[:self.config.max_samples]
        
        total_samples = len(samples)
        print(f"开始评估: {self.config.name}")
        print(f"模型: {model.config.name}")
        print(f"数据集: {dataset.config.name}")
        print(f"样本数: {total_samples}")
        
        # 执行评估
        predictions = []
        references = []
        latencies = []
        token_counts = []
        
        # 批处理评估
        batch_size = self.config.batch_size
        num_batches = (total_samples + batch_size - 1) // batch_size
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_samples)
            batch_samples = samples[start_idx:end_idx]
            
            # 准备提示
            prompts = [dataset.get_prompt_template(s) for s in batch_samples]
            refs = [s.answer for s in batch_samples]
            
            # 批量生成
            batch_start = time.time()
            try:
                results = await model.batch_generate(prompts)
            except Exception as e:
                print(f"批次 {batch_idx + 1} 生成失败: {e}")
                # 创建空结果
                results = [
                    GenerationResult(text="", prompt_tokens=0, completion_tokens=0, total_tokens=0, latency_ms=0)
                    for _ in prompts
                ]
            batch_latency = (time.time() - batch_start) * 1000
            
            # 处理结果
            for i, result in enumerate(results):
                sample = batch_samples[i]
                pred_text = result.text
                
                predictions.append(pred_text)
                references.append(refs[i])
                latencies.append(result.latency_ms)
                token_counts.append(result.total_tokens)
                
                # 保存详细结果
                if self.config.save_predictions:
                    self.results.append({
                        "id": sample.id,
                        "question": sample.question,
                        "prompt": prompts[i],
                        "prediction": pred_text,
                        "reference": refs[i],
                        "correct": self._check_answer(pred_text, refs[i], dataset),
                        "latency_ms": result.latency_ms,
                        "tokens": result.total_tokens,
                        "category": sample.category
                    })
            
            # 更新进度
            current = min(end_idx, total_samples)
            if progress_callback:
                progress_callback(current, total_samples, f"已处理 {current}/{total_samples} 样本")
            
            if (batch_idx + 1) % 10 == 0 or batch_idx == num_batches - 1:
                print(f"进度: {current}/{total_samples} ({current/total_samples*100:.1f}%)")
        
        # 计算总时间
        total_time = time.time() - start_time
        
        # 计算各项指标
        print("\n计算评估指标...")
        
        # 检测任务类型
        task_type = self._detect_task_type(dataset)
        
        # 1. 准确性指标（根据任务类型选择）
        if task_type == "multiple_choice":
            accuracy_metrics = self.metrics_calculator.calculate_classification_metrics(
                predictions, references
            )
        else:
            # 文字回答任务使用生成指标
            print("  计算生成指标 (BLEU, ROUGE, BERT Score)...")
            gen_metrics_dict = self.metrics_calculator.calculate_generation_metrics(
                predictions, references, calculate_bert_score=True
            )
            
            # 转换为 AccuracyMetrics 格式（保持兼容性）
            accuracy_metrics = AccuracyMetrics(
                accuracy=gen_metrics_dict.get("answer_correctness", gen_metrics_dict.get("bert_score_f1", 0.0)),
                precision=gen_metrics_dict.get("bert_score_precision", 0.0),
                recall=gen_metrics_dict.get("bert_score_recall", 0.0),
                f1_score=gen_metrics_dict.get("bert_score_f1", 0.0),
                exact_match=gen_metrics_dict.get("exact_match", 0.0),
                semantic_similarity=gen_metrics_dict.get("bert_score_f1", 0.0)
            )
            
            # 保存详细的文字回答指标
            text_gen_metrics = TextGenerationMetrics(
                exact_match=gen_metrics_dict.get("exact_match", 0.0),
                answer_correctness=gen_metrics_dict.get("answer_correctness", 0.0),
                bleu=gen_metrics_dict.get("bleu", 0.0),
                rouge1=gen_metrics_dict.get("rouge1", 0.0),
                rouge2=gen_metrics_dict.get("rouge2", 0.0),
                rougeL=gen_metrics_dict.get("rougeL", 0.0),
                bert_score=gen_metrics_dict.get("bert_score_f1", 0.0),
                semantic_similarity=gen_metrics_dict.get("semantic_similarity", 0.0),
                ngram_overlap=gen_metrics_dict.get("ngram_overlap", 0.0),
                ngram_1=gen_metrics_dict.get("ngram_1", 0.0),
                ngram_2=gen_metrics_dict.get("ngram_2", 0.0),
                ngram_3=gen_metrics_dict.get("ngram_3", 0.0),
                ngram_4=gen_metrics_dict.get("ngram_4", 0.0)
            )
        
        # 2. 性能指标
        performance_metrics = PerformanceMetrics()
        if self.config.evaluate_performance and latencies:
            performance_metrics = PerformanceMetrics(
                inference_time=total_time,
                tokens_per_second=sum(token_counts) / total_time if total_time > 0 else 0,
                memory_usage_mb=0.0,  # 可由外部测量
                latency_ms=statistics.mean(latencies) if latencies else 0.0
            )
        
        # 3. 鲁棒性指标（可选）
        robustness_metrics = RobustnessMetrics()
        if self.config.evaluate_robustness:
            # 简化的鲁棒性评估
            robustness_metrics = self._evaluate_robustness_quick(predictions, references)
        
        # 4. 生成质量指标（可选）
        generation_metrics = GenerationMetrics()
        try:
            diversity = self.metrics_calculator.calculate_diversity(predictions)
            generation_metrics = GenerationMetrics(diversity=diversity)
        except Exception:
            pass
        
        # 5. 安全性指标（可选）
        safety_metrics = SafetyMetrics()
        if self.config.evaluate_safety:
            safety_metrics = self.metrics_calculator.evaluate_safety(predictions)
        
        # 构建元数据
        metadata = {
            "eval_config": asdict(self.config),
            "dataset_stats": dataset.get_statistics(),
            "model_stats": model.get_statistics(),
            "total_time_seconds": total_time,
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type
        }
        
        # 添加文字回答任务的详细指标
        if task_type != "multiple_choice":
            metadata["text_generation_metrics"] = {
                "exact_match": text_gen_metrics.exact_match,
                "bleu": text_gen_metrics.bleu,
                "rouge1": text_gen_metrics.rouge1,
                "rouge2": text_gen_metrics.rouge2,
                "rougeL": text_gen_metrics.rougeL,
                "bert_score": text_gen_metrics.bert_score,
                "semantic_similarity": text_gen_metrics.semantic_similarity,
                "ngram_overlap": text_gen_metrics.ngram_overlap,
                "ngram_1": text_gen_metrics.ngram_1,
                "ngram_2": text_gen_metrics.ngram_2,
                "ngram_3": text_gen_metrics.ngram_3,
                "ngram_4": text_gen_metrics.ngram_4
            }
        
        # 构建评估结果
        result = EvaluationResult(
            dataset_name=dataset.config.name,
            model_name=model.config.name,
            accuracy=accuracy_metrics,
            performance=performance_metrics,
            robustness=robustness_metrics,
            generation=generation_metrics,
            safety=safety_metrics,
            raw_predictions=self.results,
            metadata=metadata
        )
        
        # 保存结果
        self._save_results(result)
        
        # 打印摘要
        self._print_summary(result, total_time)
        
        return result
    
    def _detect_task_type(self, dataset: BaseDataset) -> str:
        """
        检测任务类型
        
        Args:
            dataset: 数据集对象
            
        Returns:
            str: 任务类型 (multiple_choice/qa/math/code)
        """
        dataset_name = dataset.config.name.lower()
        
        # 根据数据集名称判断
        if dataset_name in ['mmlu', 'ceval', 'cmmlu']:
            return "multiple_choice"
        elif dataset_name in ['gsm8k']:
            return "math"
        elif dataset_name in ['humaneval']:
            return "code"
        elif dataset_name in ['truthfulqa']:
            return "qa"
        else:
            # 根据样本特征判断
            if dataset.samples:
                sample = dataset.samples[0]
                if sample.choices and len(sample.choices) > 0:
                    return "multiple_choice"
            return "qa"
    
    def _check_answer(
        self,
        prediction: str,
        reference: str,
        dataset: BaseDataset
    ) -> bool:
        """
        检查答案是否正确
        
        Args:
            prediction: 预测答案
            reference: 标准答案
            dataset: 数据集对象
        
        Returns:
            bool: 是否正确
        """
        # 尝试使用数据集特定的方法
        if dataset and hasattr(dataset, 'evaluate_answer'):
            return dataset.evaluate_answer(prediction, reference)
        
        # 默认比较
        if not prediction or not reference:
            return False
        
        # 检测任务类型（如果数据集可用）
        task_type = "multiple_choice"  # 默认选择题
        if dataset:
            task_type = self._detect_task_type(dataset)
        
        # 文字回答任务使用语义相似度判断
        if task_type in ["qa", "math", "code"]:
            # 计算语义相似度
            similarity = self._calculate_text_similarity(prediction, reference)
            # 相似度超过阈值认为是正确的（阈值设为0.08以适应灵活的答案表述）
            return similarity >= 0.08
        
        # 选择题使用传统匹配
        pred_clean = prediction.strip().lower()
        ref_clean = reference.strip().lower()
        
        # 直接匹配
        if pred_clean == ref_clean:
            return True
        
        # 提取选项字母
        import re
        pred_match = re.search(r'\b([a-d])\b', pred_clean)
        ref_match = re.search(r'\b([a-d])\b', ref_clean)
        
        if pred_match and ref_match:
            return pred_match.group(1) == ref_match.group(1)
        
        # 包含关系
        return ref_clean in pred_clean or pred_clean in ref_clean
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        
        综合使用多种相似度计算方法，支持中文和英文
        特别优化处理长短文本不匹配的情况
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
        
        Returns:
            float: 相似度分数 (0-1)
        """
        import re
        
        if not text1 or not text2:
            return 0.0
        
        # 改进的分词函数（支持中文）
        def tokenize(text):
            # 移除多余空格和标点，保留中英文字符
            text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
            # 空格分词
            words = [w for w in text.split() if len(w) > 0]
            # 添加单个字符（对中文很重要）
            chars = [c for c in text.replace(' ', '') if len(c.strip()) > 0]
            return set(words + chars)
        
        # 改进的关键信息提取（使用n-gram方法，更适合中文）
        def extract_key_info(text):
            text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
            chars = list(text.replace(' ', ''))
            key_info = set()
            
            # 提取2-4字词组作为关键信息
            for n in [2, 3, 4]:
                for i in range(len(chars) - n + 1):
                    word = ''.join(chars[i:i+n])
                    if len(word) >= 2:
                        key_info.add(word)
            
            return key_info
        
        # 1. 关键信息包含度（更适合长短文本比较）
        key_info1 = extract_key_info(text1)
        key_info2 = extract_key_info(text2)
        
        # 计算较短文本的关键信息在较长文本中的覆盖度
        if key_info1 and key_info2:
            shorter, longer = (key_info1, key_info2) if len(key_info1) <= len(key_info2) else (key_info2, key_info1)
            coverage = len(shorter & longer) / len(shorter) if shorter else 0.0
        else:
            coverage = 0.0
        
        # 2. Jaccard 相似度（基于词集合）
        words1 = tokenize(text1)
        words2 = tokenize(text2)
        
        if words1 and words2:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            jaccard = intersection / union if union > 0 else 0.0
        else:
            jaccard = 0.0
        
        # 3. 包含关系检查
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # 检查关键信息是否被包含
        containment = 0.0
        if text1_lower in text2_lower or text2_lower in text1_lower:
            containment = 0.9
        else:
            # 检查关键句子是否被包含
            sentences1 = [s.strip() for s in re.split(r'[。！？.!?]', text1_lower) if len(s.strip()) > 5]
            sentences2 = [s.strip() for s in re.split(r'[。！？.!?]', text2_lower) if len(s.strip()) > 5]
            if sentences1 and sentences2:
                match_count = sum(1 for s1 in sentences1 if any(s1 in s2 or s2 in s1 for s2 in sentences2))
                containment = (match_count / len(sentences1)) * 0.7
        
        # 4. N-gram 相似度（基于字符，用于捕捉局部相似性）
        def get_ngrams(text, n=2):
            chars = list(text.lower().replace(' ', ''))
            return set(tuple(chars[i:i+n]) for i in range(len(chars)-n+1))
        
        ngrams1 = get_ngrams(text1)
        ngrams2 = get_ngrams(text2)
        
        if ngrams1 and ngrams2:
            ngram_intersection = len(ngrams1 & ngrams2)
            ngram_union = len(ngrams1 | ngrams2)
            ngram_sim = ngram_intersection / ngram_union if ngram_union > 0 else 0.0
        else:
            ngram_sim = 0.0
        
        # 5. 关键主题词匹配（提取最重要的概念）
        def extract_concepts(text):
            # 提取名词性词汇（简化版：长度>=3的词）
            text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
            words = text.split()
            return set(w for w in words if len(w) >= 3)
        
        concepts1 = extract_concepts(text1)
        concepts2 = extract_concepts(text2)
        
        if concepts1 and concepts2:
            concept_intersection = len(concepts1 & concepts2)
            concept_union = len(concepts1 | concepts2)
            concept_sim = concept_intersection / concept_union if concept_union > 0 else 0.0
        else:
            concept_sim = 0.0
        
        # 综合得分（加权平均）
        # 关键信息覆盖度最重要，其次是概念相似度和包含关系
        final_score = (
            coverage * 0.35 +      # 关键信息覆盖度
            jaccard * 0.15 +       # Jaccard相似度
            containment * 0.25 +   # 包含关系
            ngram_sim * 0.10 +     # N-gram相似度
            concept_sim * 0.15     # 关键概念相似度
        )
        
        return min(1.0, final_score)
    
    def _evaluate_robustness_quick(
        self,
        predictions: List[str],
        references: List[str]
    ) -> RobustnessMetrics:
        """
        快速鲁棒性评估
        
        Args:
            predictions: 预测列表
            references: 参考答案列表
        
        Returns:
            RobustnessMetrics: 鲁棒性指标
        """
        # 简化的鲁棒性评估：检查预测长度分布
        lengths = [len(p) for p in predictions if p]
        
        if not lengths:
            return RobustnessMetrics()
        
        # 长度方差作为简单鲁棒性指标
        if len(lengths) > 1:
            length_variance = statistics.variance(lengths)
            # 方差越小，说明输出越稳定
            stability = 1.0 / (1.0 + length_variance / 1000)
        else:
            stability = 1.0
        
        return RobustnessMetrics(
            adversarial_accuracy=0.0,  # 需要专门测试
            noise_robustness=stability,
            long_context_score=0.0  # 需要专门测试
        )
    
    def _save_results(self, result: EvaluationResult) -> None:
        """
        保存评估结果
        
        Args:
            result: 评估结果对象
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = Path(self.config.output_dir) / f"eval_{self.config.name}_{timestamp}.json"
        
        # 转换为字典
        result_dict = {
            "dataset_name": result.dataset_name,
            "model_name": result.model_name,
            "accuracy": asdict(result.accuracy),
            "performance": asdict(result.performance),
            "robustness": asdict(result.robustness),
            "generation": asdict(result.generation),
            "safety": asdict(result.safety),
            "metadata": result.metadata
        }
        
        # 保存主要结果
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        # 保存详细预测结果
        if self.config.save_predictions and self.results:
            pred_file = Path(self.config.output_dir) / f"predictions_{self.config.name}_{timestamp}.jsonl"
            with open(pred_file, 'w', encoding='utf-8') as f:
                for item in self.results:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"\n结果已保存到: {result_file}")
    
    def _print_summary(self, result: EvaluationResult, total_time: float) -> None:
        """
        打印评估摘要
        
        Args:
            result: 评估结果对象
            total_time: 总耗时
        """
        print("\n" + "=" * 60)
        print("评估结果摘要")
        print("=" * 60)
        print(f"任务名称: {self.config.name}")
        print(f"模型: {result.model_name}")
        print(f"数据集: {result.dataset_name}")
        print(f"总样本数: {len(self.results)}")
        print(f"总耗时: {total_time:.2f}秒")
        print("-" * 60)
        
        # 检查是否是文字回答任务
        task_type = result.metadata.get("task_type", "multiple_choice")
        text_metrics = result.metadata.get("text_generation_metrics", None)
        
        if text_metrics:
            print("文字回答任务指标:")
            print(f"  精确匹配: {text_metrics.get('exact_match', 0):.4f}")
            print(f"  BLEU: {text_metrics.get('bleu', 0):.4f}")
            print(f"  ROUGE-1: {text_metrics.get('rouge1', 0):.4f}")
            print(f"  ROUGE-2: {text_metrics.get('rouge2', 0):.4f}")
            print(f"  ROUGE-L: {text_metrics.get('rougeL', 0):.4f}")
            print(f"  BERT Score: {text_metrics.get('bert_score', 0):.4f}")
            print(f"  语义相似度: {text_metrics.get('semantic_similarity', 0):.4f}")
            print(f"  N-gram重叠 (平均): {text_metrics.get('ngram_overlap', 0):.4f}")
            print(f"    1-gram (unigram): {text_metrics.get('ngram_1', 0):.4f}")
            print(f"    2-gram (bigram): {text_metrics.get('ngram_2', 0):.4f}")
            print(f"    3-gram (trigram): {text_metrics.get('ngram_3', 0):.4f}")
            print(f"    4-gram: {text_metrics.get('ngram_4', 0):.4f}")
        else:
            print("准确性指标:")
            print(f"  准确率: {result.accuracy.accuracy:.4f} ({result.accuracy.accuracy*100:.2f}%)")
            print(f"  精确匹配: {result.accuracy.exact_match:.4f}")
            print(f"  F1分数: {result.accuracy.f1_score:.4f}")
        
        print("-" * 60)
        print("性能指标:")
        print(f"  平均延迟: {result.performance.latency_ms:.2f}ms")
        print(f"  Token/秒: {result.performance.tokens_per_second:.2f}")
        print("=" * 60)
    
    def get_summary(self, result: EvaluationResult) -> EvaluationSummary:
        """
        获取评估摘要
        
        Args:
            result: 评估结果对象
        
        Returns:
            EvaluationSummary: 评估摘要
        """
        return EvaluationSummary(
            eval_name=self.config.name,
            model_name=result.model_name,
            dataset_name=result.dataset_name,
            total_samples=len(self.results),
            accuracy=result.accuracy.accuracy,
            avg_latency_ms=result.performance.latency_ms,
            total_time_seconds=result.metadata.get("total_time_seconds", 0),
            timestamp=result.metadata.get("timestamp", ""),
            details={
                "exact_match": result.accuracy.exact_match,
                "f1_score": result.accuracy.f1_score,
                "tokens_per_second": result.performance.tokens_per_second
            }
        )
    
    def compare_results(
        self,
        results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        比较多个评估结果
        
        Args:
            results: 评估结果列表
        
        Returns:
            Dict: 比较结果
        """
        comparison = {
            "models": [],
            "accuracy": {},
            "performance": {},
            "ranking": []
        }
        
        for result in results:
            model_name = result.model_name
            comparison["models"].append(model_name)
            
            comparison["accuracy"][model_name] = {
                "accuracy": result.accuracy.accuracy,
                "exact_match": result.accuracy.exact_match,
                "f1_score": result.accuracy.f1_score
            }
            
            comparison["performance"][model_name] = {
                "latency_ms": result.performance.latency_ms,
                "tokens_per_second": result.performance.tokens_per_second
            }
        
        # 按准确率排序
        sorted_models = sorted(
            results,
            key=lambda r: r.accuracy.accuracy,
            reverse=True
        )
        comparison["ranking"] = [
            {"rank": i+1, "model": r.model_name, "accuracy": r.accuracy.accuracy}
            for i, r in enumerate(sorted_models)
        ]
        
        return comparison
