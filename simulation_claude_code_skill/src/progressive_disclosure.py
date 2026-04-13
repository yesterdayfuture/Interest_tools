#!/usr/bin/env python3
"""
渐进式披露模块

该模块负责根据需要逐步披露技能的信息，
从元数据到完整内容，以优化Token使用。
"""

class ProgressiveDisclosure:
    """
    渐进式披露类
    
    负责根据需要逐步披露技能的信息，
    从元数据到完整内容，以优化Token使用。
    """

    @staticmethod
    def get_skill_metadata(skill):
        """
        获取技能元数据（第一层）
        
        返回技能的基本元数据，包括名称、描述和版本。
        
        Args:
            skill (dict): 技能信息
        
        Returns:
            dict: 技能元数据
        """
        return {
            'name': skill['metadata'].get('name'),
            'description': skill['metadata'].get('description'),
            'version': skill['metadata'].get('version')
        }
    
    @staticmethod
    def get_skill_triggers(skill):
        """
        获取技能触发条件（第二层）
        
        返回技能的触发条件，包括触发词、自动触发标志和优先级。
        
        Args:
            skill (dict): 技能信息
        
        Returns:
            dict: 技能触发条件
        """
        return {
            'triggers': skill['metadata'].get('triggers', []),
            'auto_trigger': skill['metadata'].get('auto_trigger', False),
            'priority': skill['metadata'].get('priority', 'medium')
        }
    
    @staticmethod
    def get_skill_full_content(skill):
        """
        获取技能完整内容（第三层）
        
        返回技能的完整内容，包括元数据、指令、脚本、参数和参考资料。
        
        Args:
            skill (dict): 技能信息
        
        Returns:
            dict: 技能完整内容
        """
        content = {
            'metadata': skill['metadata'],
            'instructions': skill['instructions'],
            'scripts': skill['scripts'],
            'parameters': skill['parameters']
        }
        
        # 加载参考资料（如果存在）
        try:
            from pathlib import Path
            skill_path = Path(skill['path'])
            references_dir = skill_path / 'references'
            if references_dir.exists():
                references = {}
                for ref_file in references_dir.iterdir():
                    if ref_file.is_file():
                        try:
                            references[ref_file.name] = ref_file.read_text(encoding='utf-8')
                        except:
                            # 非文本文件跳过
                            pass
                content['references'] = references
        except Exception as e:
            print(f"Error loading references: {e}")
        
        return content
    
    @staticmethod
    def calculate_token_usage(content):
        """
        估算Token使用量
        
        简单估算内容的Token使用量，基于1 token ≈ 4字符的比例。
        
        Args:
            content (any): 要估算的内容
        
        Returns:
            int: 估算的Token使用量
        """
        # 简单估算：1 token ≈ 4字符
        def count_tokens(text):
            if isinstance(text, str):
                return len(text) // 4
            elif isinstance(text, dict):
                return sum(count_tokens(v) for v in text.values())
            elif isinstance(text, list):
                return sum(count_tokens(item) for item in text)
            return 0
        
        return count_tokens(content)
    
    @staticmethod
    def build_context(skill, context_level='full'):
        """
        根据需要构建上下文
        
        根据指定的上下文级别，构建相应的技能上下文。
        
        Args:
            skill (dict): 技能信息
            context_level (str): 上下文级别，可选值：'metadata', 'triggers', 'full'
        
        Returns:
            dict: 构建的上下文
        """
        if context_level == 'metadata':
            return ProgressiveDisclosure.get_skill_metadata(skill)
        elif context_level == 'triggers':
            return {
                **ProgressiveDisclosure.get_skill_metadata(skill),
                **ProgressiveDisclosure.get_skill_triggers(skill)
            }
        elif context_level == 'full':
            return ProgressiveDisclosure.get_skill_full_content(skill)
        return {}
