#!/usr/bin/env python3
"""
技能解析器模块

该模块负责解析技能文件，提取元数据和指令内容。
"""

import yaml
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SkillParser:
    """
    技能解析器类
    
    负责解析技能文件，提取元数据和指令内容。
    """

    @staticmethod
    def parse_skill_file(skill_file_path):
        """
        解析SKILL.md文件，提取Frontmatter元数据和指令内容
        
        Args:
            skill_file_path (str): 技能文件路径
        
        Returns:
            dict: 技能数据，包含元数据、指令内容、脚本配置和参数配置
        """
        try:
            content = Path(skill_file_path).read_text(encoding='utf-8')
            
            # 提取Frontmatter元数据
            frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
            if not frontmatter_match:
                return None
            
            frontmatter_str = frontmatter_match.group(1)
            instructions = frontmatter_match.group(2)
            
            # 解析YAML元数据
            metadata = yaml.safe_load(frontmatter_str)
            
            # 验证必需字段
            if not all(key in metadata for key in ['name', 'description', 'version']):
                return None
            
            # 提取脚本配置
            scripts = metadata.get('scripts', [])
            
            # 提取参数配置
            parameters = metadata.get('parameters', [])
            
            return {
                'metadata': metadata,
                'instructions': instructions.strip(),
                'scripts': scripts,
                'parameters': parameters
            }
        except Exception as e:
            print(f"Error parsing skill file: {e}")
            return None
    
    @staticmethod
    def parse_skill_metadata(skill_file_path):
        """
        只解析SKILL.md文件的元数据部分
        
        Args:
            skill_file_path (str): 技能文件路径
        
        Returns:
            dict: 技能元数据
        """
        try:
            content = Path(skill_file_path).read_text(encoding='utf-8')
            
            # 提取Frontmatter元数据
            frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
            if not frontmatter_match:
                return None
            
            frontmatter_str = frontmatter_match.group(1)
            
            # 解析YAML元数据
            metadata = yaml.safe_load(frontmatter_str)
            
            # 验证必需字段
            if not all(key in metadata for key in ['name', 'description', 'version']):
                return None
            
            return metadata
        except Exception as e:
            print(f"Error parsing skill metadata: {e}")
            return None
    
    @staticmethod
    def scan_skills_directories(skill_dirs):
        """
        扫描技能目录，返回所有技能的元数据
        
        Args:
            skill_dirs (list): 技能目录列表
        
        Returns:
            list: 技能列表
        """
        skills = []
        
        for skill_dir in skill_dirs:
            skill_path = Path(skill_dir)
            if not skill_path.exists() or not skill_path.is_dir():
                continue
            
            # 遍历技能目录
            for skill_folder in skill_path.iterdir():
                if not skill_folder.is_dir():
                    continue
                
                # 检查SKILL.md文件
                skill_file = skill_folder / 'SKILL.md'
                if not skill_file.exists():
                    continue
                
                # 解析技能文件
                skill_data = SkillParser.parse_skill_file(skill_file)
                if skill_data:
                    # 添加技能路径信息
                    skill_data['path'] = str(skill_folder)
                    skill_data['id'] = skill_folder.name
                    skills.append(skill_data)
        
        return skills