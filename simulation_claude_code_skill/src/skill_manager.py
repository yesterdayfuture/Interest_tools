#!/usr/bin/env python3
"""
技能管理器模块

该模块负责加载和管理技能，包括完整技能和仅元数据加载。
"""

from pathlib import Path
from src.skill_parser import SkillParser

class SkillManager:
    """
    技能管理器类
    
    负责加载和管理技能，包括完整技能和仅元数据加载，
    并构建技能索引用于快速查找。
    """
    def __init__(self):
        """
        初始化技能管理器
        
        初始化技能列表和技能索引。
        """
        self.skills = []  # 技能列表
        self.skill_index = {}  # 技能索引，用于快速查找
    
    def load_skills(self):
        """
        加载所有技能
        
        扫描全局技能目录、项目技能目录和当前目录技能，
        解析所有技能并构建技能索引。
        
        Returns:
            list: 技能列表
        """
        # 扫描全局技能目录和项目技能目录
        skill_dirs = [
            Path.home() / '.claude' / 'skills',  # 全局技能
            Path('.') / '.claude' / 'skills',    # 项目技能
            Path('skills')                       # 当前目录技能
        ]
        
        # 扫描技能
        self.skills = SkillParser.scan_skills_directories(skill_dirs)
        
        # 构建技能索引
        self._build_index()
        
        return self.skills
    
    def _build_index(self):
        """
        构建技能索引，用于快速查找
        
        为每个技能ID和触发词构建索引，
        以便快速根据ID或触发词查找技能。
        """
        for skill in self.skills:
            skill_id = skill['id']
            self.skill_index[skill_id] = skill
            
            # 索引触发词
            triggers = skill['metadata'].get('triggers', [])
            for trigger in triggers:
                if trigger not in self.skill_index:
                    self.skill_index[trigger] = []
                self.skill_index[trigger].append(skill)
    
    def get_skill_by_id(self, skill_id):
        """
        根据ID获取技能
        
        Args:
            skill_id (str): 技能ID
        
        Returns:
            dict: 技能信息，不存在返回None
        """
        return self.skill_index.get(skill_id)
    
    def get_skills_by_trigger(self, trigger):
        """
        根据触发词获取技能
        
        Args:
            trigger (str): 触发词
        
        Returns:
            list: 技能列表，不存在返回空列表
        """
        return self.skill_index.get(trigger, [])
    
    def get_all_skills(self):
        """
        获取所有技能
        
        Returns:
            list: 技能列表
        """
        return self.skills
    
    def refresh_skills(self):
        """
        刷新技能列表
        
        重新加载所有技能并返回。
        
        Returns:
            list: 技能列表
        """
        return self.load_skills()
    
    def load_skills_metadata(self):
        """
        只加载技能的元数据
        
        扫描全局技能目录、项目技能目录和当前目录技能，
        只解析每个技能的元数据并返回。
        
        Returns:
            list: 技能元数据列表
        """
        # 扫描全局技能目录和项目技能目录
        skill_dirs = [
            Path.home() / '.claude' / 'skills',  # 全局技能
            Path('.') / '.claude' / 'skills',    # 项目技能
            Path('skills')                       # 当前目录技能
        ]
        
        # 扫描技能元数据
        skills_metadata = []
        for skill_dir in skill_dirs:
            if skill_dir.exists() and skill_dir.is_dir():
                for skill_subdir in skill_dir.iterdir():
                    if skill_subdir.is_dir():
                        skill_file = skill_subdir / 'SKILL.md'
                        if skill_file.exists():
                            # 只解析元数据
                            metadata = SkillParser.parse_skill_metadata(skill_file)
                            if metadata:
                                skills_metadata.append({
                                    'id': skill_subdir.name,
                                    'metadata': metadata
                                })
        
        return skills_metadata