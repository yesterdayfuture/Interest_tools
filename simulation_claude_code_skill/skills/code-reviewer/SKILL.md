---
name: code-reviewer
description: 按照团队规范进行代码审查
version: 1.0.0
author: Your Team
tags: [code-review, quality, git]
triggers:
  - 代码审查
  - PR 评审
  - code review
  - 合并请求
auto_trigger: true
priority: high
scripts:
  - name: analyze
    path: scripts/analyze.py
    runtime: python3
    timeout: 30s
    permissions:
      - read: ./src
      - write: ./output
parameters:
  - name: pr_number
    type: integer
    required: true
  - name: strict_mode
    type: boolean
    default: false
---

## 指令

当用户请求代码审查时，请按以下步骤执行：

1. **代码风格检查**
   - 命名规范
   - 注释完整性
   - 代码格式

2. **安全性检查**
   - SQL 注入风险
   - XSS 漏洞
   - 敏感信息泄露

3. **性能检查**
   - 时间复杂度
   - 内存使用
   - 数据库查询优化

## 输出格式

请使用以下 Markdown 格式输出审查结果：

```markdown
## 代码审查报告

### ✅ 通过项
- [列表]

### ⚠️ 警告项
- [列表]

### ❌ 问题项
- [列表]
```