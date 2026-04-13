#!/usr/bin/env python3
"""
测试技能管理器

该文件测试技能管理器和意图匹配器的功能。
"""

import unittest
from src.skill_manager import SkillManager
from src.intent_matcher import IntentMatcher

class TestSkillManager(unittest.TestCase):
    """
    测试技能管理器和意图匹配器的功能
    """

    def setUp(self):
        """
        设置测试环境
        
        初始化技能管理器和意图匹配器。
        """
        self.skill_manager = SkillManager()
        self.intent_matcher = IntentMatcher()
    
    def test_load_skills_metadata(self):
        """
        测试加载技能元数据
        
        测试技能管理器是否能正确加载技能元数据，
        并检查每个技能元数据是否包含必要的字段。
        """
        metadata = self.skill_manager.load_skills_metadata()
        self.assertGreaterEqual(len(metadata), 2)
        
        # 检查每个技能元数据是否包含必要的字段
        for skill in metadata:
            self.assertIn('id', skill)
            self.assertIn('metadata', skill)
            self.assertIn('name', skill['metadata'])
            self.assertIn('description', skill['metadata'])
            self.assertIn('version', skill['metadata'])
    
    def test_load_skills(self):
        """
        测试加载完整技能
        
        测试技能管理器是否能正确加载完整技能，
        并检查每个技能是否包含必要的字段。
        """
        skills = self.skill_manager.load_skills()
        self.assertGreaterEqual(len(skills), 2)
        
        # 检查每个技能是否包含必要的字段
        for skill in skills:
            self.assertIn('id', skill)
            self.assertIn('metadata', skill)
            self.assertIn('instructions', skill)
            self.assertIn('path', skill)
    
    def test_get_skill_by_id(self):
        """
        测试根据ID获取技能
        
        测试技能管理器是否能根据ID正确获取技能。
        """
        self.skill_manager.load_skills()
        skill = self.skill_manager.get_skill_by_id('code-reviewer')
        self.assertIsNotNone(skill)
        self.assertEqual(skill['id'], 'code-reviewer')
        
        skill = self.skill_manager.get_skill_by_id('project-health')
        self.assertIsNotNone(skill)
        self.assertEqual(skill['id'], 'project-health')
    
    def test_intent_matching(self):
        """
        测试意图匹配
        
        测试意图匹配器是否能正确匹配用户输入与技能。
        """
        self.skill_manager.load_skills()
        skills = self.skill_manager.get_all_skills()
        
        # 测试代码审查技能匹配
        matches = self.intent_matcher.match_skills('帮我审查一下代码', skills)
        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual(matches[0]['skill']['id'], 'code-reviewer')
        
        # 测试项目健康分析技能匹配
        matches = self.intent_matcher.match_skills('帮我分析一下项目健康状况', skills)
        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual(matches[0]['skill']['id'], 'project-health')

if __name__ == "__main__":
    """
    测试入口点
    
    运行所有测试用例。
    """
    unittest.main()
