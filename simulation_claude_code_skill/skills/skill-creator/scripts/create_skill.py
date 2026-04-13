#!/usr/bin/env python3
import os
import json
import argparse
from pathlib import Path

def create_skill(skill_name, skill_description, skill_triggers, skill_instructions, skill_script=None, skill_md_content=None):
    """创建新的技能"""
    # 生成技能目录名（使用kebab-case）
    # 移除特殊字符，只保留字母、数字和连字符
    import re
    skill_dir_name = re.sub(r'[^a-zA-Z0-9\s_-]', '', skill_name)
    skill_dir_name = skill_dir_name.lower().replace(' ', '-').replace('_', '-')
    # 如果目录名为空，使用默认名称
    if not skill_dir_name:
        skill_dir_name = 'new-skill'
    skill_dir = Path('skills') / skill_dir_name
    
    # 创建技能目录
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成SKILL.md文件
    skill_file = skill_dir / 'SKILL.md'
    if skill_md_content:
        # 检查是否包含Frontmatter结构
        if skill_md_content.strip().startswith('---'):
            # 如果已经包含Frontmatter，直接使用
            skill_content = skill_md_content
        else:
            # 如果不包含Frontmatter，添加默认的Frontmatter结构
            skill_content = f"""
---
name: {skill_name}
description: {skill_description}
version: 1.0.0
author: Your Team
tags: []
triggers: {json.dumps(skill_triggers)}
auto_trigger: true
priority: medium
---

{skill_md_content}
"""
    else:
        # 使用默认模板
        skill_content = f"""
---
name: {skill_name}
description: {skill_description}
version: 1.0.0
author: Your Team
tags: []
triggers: {json.dumps(skill_triggers)}
auto_trigger: true
priority: medium
---

## 指令

{skill_instructions}

## 输出格式

请根据技能的具体功能设计合适的输出格式
"""
    
    skill_file.write_text(skill_content, encoding='utf-8')
    
    # 创建scripts目录
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(exist_ok=True)
    
    # 生成脚本文件
    example_script = scripts_dir / 'generate_content.py'
    if skill_script:
        # 使用大模型生成的脚本内容
        example_script_content = skill_script

        example_script.write_text(example_script_content, encoding='utf-8')
        example_script.chmod(0o755)  # 使其可执行
    
    # 生成README.md文件
    readme_file = skill_dir / 'README.md'
    readme_file_content = f"""
# {skill_name} 技能

## 描述
{skill_description}

## 触发词
{', '.join(skill_triggers)}

## 使用方法
描述如何使用这个技能
"""
    readme_file.write_text(readme_file_content, encoding='utf-8')
    
    # 返回生成的文件列表
    generated_files = [
        str(skill_file),
        str(readme_file)
    ]
    
    # 只有当脚本文件被创建时，才添加到生成文件列表中
    if skill_script:
        generated_files.append(str(example_script))
    
    return {
        'skill_name': skill_name,
        'skill_dir': str(skill_dir),
        'generated_files': generated_files
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='创建新的技能')
    parser.add_argument('--skill_name', required=True, help='技能名称')
    parser.add_argument('--skill_description', required=True, help='技能描述')
    parser.add_argument('--skill_triggers', required=True, help='触发词列表（JSON格式）')
    parser.add_argument('--skill_instructions', required=True, help='技能指令')
    parser.add_argument('--skill_script', help='大模型生成的脚本内容')
    parser.add_argument('--skill_script_file', help='大模型生成的脚本内容文件')
    parser.add_argument('--skill_md_content', help='大模型生成的SKILL.md内容')
    parser.add_argument('--skill_md_content_file', help='大模型生成的SKILL.md内容文件')
    
    args = parser.parse_args()
    
    # 解析触发词列表
    try:
        # 尝试直接解析JSON
        skill_triggers = json.loads(args.skill_triggers)
    except json.JSONDecodeError:
        # 如果不是有效的JSON，尝试解析Python格式的列表字符串
        import ast
        try:
            skill_triggers = ast.literal_eval(args.skill_triggers)
        except:
            # 如果都失败了，使用默认值
            skill_triggers = ['触发词1', '触发词2']
    
    # 读取脚本内容
    skill_script = args.skill_script
    if args.skill_script_file:
        with open(args.skill_script_file, 'r', encoding='utf-8') as f:
            skill_script = f.read()
        # 删除临时文件
        import os
        os.unlink(args.skill_script_file)
    
    # 读取SKILL.md内容
    skill_md_content = args.skill_md_content
    if args.skill_md_content_file:
        with open(args.skill_md_content_file, 'r', encoding='utf-8') as f:
            skill_md_content = f.read()
        # 删除临时文件
        import os
        os.unlink(args.skill_md_content_file)
    
    # 创建技能
    result = create_skill(
        args.skill_name,
        args.skill_description,
        skill_triggers,
        args.skill_instructions,
        skill_script,
        skill_md_content
    )
    
    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))
