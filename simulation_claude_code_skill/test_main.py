#!/usr/bin/env python3
"""
测试主应用接口

该文件测试Claude Code Skills系统的各个API接口。
"""

import unittest
import requests
import json

class TestClaudeCodeSkills(unittest.TestCase):
    """
    测试Claude Code Skills系统的各个API接口
    """

    def setUp(self):
        """
        设置测试环境
        
        初始化测试的基础URL。
        """
        self.base_url = "http://localhost:8005"
    
    def test_health_check(self):
        """
        测试健康检查接口
        
        测试健康检查接口是否正常返回健康状态。
        """
        response = requests.get(f"{self.base_url}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "healthy")
    
    def test_get_skills_metadata(self):
        """
        测试技能元数据接口
        
        测试技能元数据接口是否正常返回技能列表，
        并检查每个技能是否包含必要的字段。
        """
        response = requests.get(f"{self.base_url}/tools/skills/metadata")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("skills", data)
        skills = data["skills"]
        self.assertGreaterEqual(len(skills), 2)
        
        # 检查每个技能是否包含必要的字段
        for skill in skills:
            self.assertIn("skill_id", skill)
            self.assertIn("name", skill)
            self.assertIn("description", skill)
            self.assertIn("triggers", skill)
    
    def test_qa_code_review(self):
        """
        测试代码审查技能
        
        测试代码审查技能是否能正确匹配和执行。
        """
        response = requests.post(f"{self.base_url}/qa", json={"question": "帮我审查一下这段Python代码"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertIn("used_skill", data)
        self.assertEqual(data["used_skill"], "code-reviewer")
    
    def test_qa_project_health(self):
        """
        测试项目健康分析技能
        
        测试项目健康分析技能是否能正确匹配和执行。
        """
        response = requests.post(f"{self.base_url}/qa", json={"question": "帮我分析一下这个项目的健康状况"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertIn("used_skill", data)
        self.assertEqual(data["used_skill"], "project-health")
    
    def test_qa_no_skill(self):
        """
        测试没有匹配技能的情况
        
        测试当没有匹配的技能时，系统是否能正确处理。
        """
        response = requests.post(f"{self.base_url}/qa", json={"question": "今天天气怎么样"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertIn("used_skill", data)
        self.assertEqual(data["used_skill"], "default")
    
    def test_get_skills(self):
        """
        测试获取技能列表接口
        
        测试获取技能列表接口是否正常返回技能列表。
        """
        response = requests.get(f"{self.base_url}/skills")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("skills", data)
    
    def test_get_skill_detail(self):
        """
        测试获取技能详情接口
        
        测试获取技能详情接口是否正常返回技能详情。
        """
        response = requests.get(f"{self.base_url}/skills/code-reviewer")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("metadata", data)
        self.assertIn("instructions", data)

if __name__ == "__main__":
    """
    测试入口点
    
    运行所有测试用例。
    """
    unittest.main()
