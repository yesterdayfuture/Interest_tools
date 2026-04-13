---
name: skill-creator
description: 创建新的技能
version: 1.0.0
author: Your Team
tags: [skill-creation, automation]
triggers: [创建技能, 新建技能, skill creation, create skill]
auto_trigger: true
priority: high
scripts:
  - name: create_skill
    path: scripts/create_skill.py
    runtime: python3
    timeout: 60s
    permissions:
      - read: .
      - write: ./skills
parameters:
  - name: skill_name
    type: string
    required: true
  - name: skill_description
    type: string
    required: true
  - name: skill_triggers
    type: array
    items: string
    required: true
  - name: skill_instructions
    type: string
    required: true
---

## 指令

当用户请求创建新的技能时，请按以下步骤执行：

1. **收集技能信息**
   - 分析用户需求，提取技能的核心功能
   - 确定技能名称、描述、触发词列表
   - 设计技能的指令和输出格式
   - 规划必要的脚本功能

2. **生成技能内容**
   - 根据用户需求，为新技能生成个性化的指令内容
   - 设计适合该技能的脚本逻辑
   - 确保内容符合技能的具体功能要求

3. **创建技能文件**
   - 创建英文名称的技能目录
   - 生成SKILL.md文件，包含生成的元数据和指令
   - 生成必要的脚本文件，包含生成的脚本逻辑
   - 确保文件结构正确

4. **验证技能**
   - 检查技能文件是否符合格式要求
   - 确保所有必要字段都已填写
   - 验证脚本的语法和逻辑

5. **返回结果**
   - 告诉用户技能已成功创建
   - 提供技能的路径和基本信息
   - 说明如何使用新技能

## 输出格式

请使用以下格式输出结果：

```markdown
## 技能创建成功

### 技能信息
- **名称**: [技能名称]
- **描述**: [技能描述]
- **触发词**: [触发词列表]
- **路径**: [技能路径]

### 生成的文件
- [文件路径1]
- [文件路径2]
- [文件路径3]

### 如何使用
1. 重启服务器以加载新技能
2. 使用触发词测试新技能
3. 根据需要修改技能文件

### 技能功能
[详细描述新技能的功能和使用方法]
```
