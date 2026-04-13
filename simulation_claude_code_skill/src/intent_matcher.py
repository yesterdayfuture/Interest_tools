#!/usr/bin/env python3
"""
意图匹配器模块

该模块负责匹配用户输入与技能，基于触发词和描述进行匹配。
"""

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import string
import re

# 下载NLTK数据
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception as e:
    print(f"Warning: NLTK download failed: {e}")

class IntentMatcher:
    """
    意图匹配器类
    
    负责匹配用户输入与技能，基于触发词和描述进行匹配。
    """

    def __init__(self):
        """
        初始化意图匹配器
        
        初始化英文和中文停用词集合。
        """
        # 英文停用词
        self.english_stop_words = set(stopwords.words('english'))
        # 中文停用词
        self.chinese_stop_words = set([
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '着', '或', '一个', '有', '在', '为', '以'
        ])
    
    def preprocess_text(self, text):
        """
        预处理文本
        
        将文本转换为小写，去除标点符号和停用词，
        并去除多余的空格。
        
        Args:
            text (str): 原始文本
        
        Returns:
            str: 预处理后的文本
        """
        # 转换为小写
        text = text.lower()
        # 去除标点符号
        text = text.translate(str.maketrans('', '', string.punctuation))
        # 去除停用词
        for stop_word in self.chinese_stop_words:
            text = text.replace(stop_word, '')
        for stop_word in self.english_stop_words:
            text = text.replace(' ' + stop_word + ' ', ' ')
        # 去除多余的空格
        text = ' '.join(text.split())
        return text
    
    def match_skills(self, user_input, skills):
        """
        匹配用户输入与技能
        
        基于触发词和描述，计算用户输入与每个技能的匹配度，
        并返回按匹配度排序的结果。
        
        Args:
            user_input (str): 用户输入
            skills (list): 技能列表
        
        Returns:
            list: 匹配结果列表，按匹配度排序
        """
        if not skills:
            return []
        
        # 预处理用户输入
        processed_input = self.preprocess_text(user_input)
        print(f"Processed input: {processed_input}")
        
        # 为每个技能计算匹配度
        matches = []
        for skill in skills:
            # 提取技能的触发词和描述
            triggers = skill['metadata'].get('triggers', [])
            description = skill['metadata'].get('description', '')
            
            # 检查触发词
            confidence = 0.0
            for trigger in triggers:
                trigger_processed = self.preprocess_text(trigger)
                
                # 1. 完全匹配
                if trigger_processed in processed_input:
                    confidence += 0.5
                # 2. 正则表达式匹配
                else:
                    try:
                        # 创建正则表达式模式，允许中间有其他字符
                        pattern = '.*'.join(re.escape(char) for char in trigger_processed)
                        if re.search(pattern, processed_input):
                            # 正则匹配成功，增加置信度
                            confidence += 0.4
                    except:
                        pass
                # 3. 字符级匹配
                match_count = 0
                for char in trigger_processed:
                    if char in processed_input:
                        match_count += 1
                if match_count > 0:
                    confidence += 0.2 * (match_count / len(trigger_processed))
            
            # 检查描述
            description_processed = self.preprocess_text(description)
            # 1. 完全匹配
            if description_processed in processed_input:
                confidence += 0.3
            # 2. 正则表达式匹配
            else:
                try:
                    pattern = '.*'.join(re.escape(char) for char in description_processed)
                    if re.search(pattern, processed_input):
                        confidence += 0.2
                except:
                    pass
            
            print(f"Confidence for {skill['id']}: {confidence}")
            
            if confidence > 0.1:  # 设置阈值
                matches.append({
                    'skill': skill,
                    'confidence': confidence
                })
        
        # 按匹配度排序
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        print(f"Final matches: {matches}")
        
        return matches
    
    def extract_keywords(self, text):
        """
        提取关键词
        
        预处理文本并提取关键词。
        
        Args:
            text (str): 原始文本
        
        Returns:
            list: 关键词列表
        """
        processed_text = self.preprocess_text(text)
        tokens = word_tokenize(processed_text)
        # 简单的关键词提取：返回所有非停用词
        return tokens