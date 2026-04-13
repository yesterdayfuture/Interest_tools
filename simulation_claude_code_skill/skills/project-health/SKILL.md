---
name: project-health
description: 分析项目健康状况并生成报告
version: 1.2.0
author: Your Team
tags: [project, health, analysis]
triggers:
  - 项目健康
  - 代码质量
  - 项目分析
auto_trigger: false
priority: medium
scripts:
  - name: analyze_health
    path: scripts/health_analyzer.py
    runtime: python3
    timeout: 60s
    permissions:
      - read: .
      - write: ./reports
---

## 指令

当用户请求项目健康分析时，执行以下步骤：

1. 扫描项目结构
2. 分析代码覆盖率
3. 检查技术债务
4. 评估依赖安全性
5. 生成综合评分

## 输出模板

### 项目健康报告

| 维度 | 评分 | 状态 |
|------|------|------|
| 代码质量 | 85/100 | 🟢 |
| 测试覆盖 | 72/100 | 🟡 |
| 依赖安全 | 90/100 | 🟢 |
| 文档完整 | 65/100 | 🟡 |

**总体评分：78/100** 🟢