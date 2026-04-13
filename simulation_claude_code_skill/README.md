# Claude Code Skills 模拟实现

这是一个基于 FastAPI 和 OpenAI 的 Claude Code Skills 系统模拟实现，旨在复现 Anthropic 为 Claude Code 推出的模块化能力扩展系统。

## 核心功能

- **技能管理**：基于文件系统的动态技能发现和管理
- **意图识别**：智能匹配用户请求与相关技能
- **渐进式披露**：按需加载技能内容，最小化 Token 消耗
- **安全沙盒**：隔离执行技能脚本，确保安全性
- **API 接口**：完整的 RESTful API 接口

## 项目结构

```
├── skills/              # 技能目录
│   ├── code-reviewer/   # 代码审查技能
│   └── project-health/  # 项目健康分析技能
├── src/                 # 源代码
│   ├── skill_parser.py  # 技能配置解析
│   ├── skill_manager.py # 技能管理
│   ├── intent_matcher.py # 意图匹配
│   ├── progressive_disclosure.py # 渐进式披露
│   └── sandbox.py       # 安全沙盒
├── main.py              # FastAPI 应用
├── requirements.txt     # 依赖文件
└── .env                 # 环境变量
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `.env` 文件中填入你的 OpenAI API 密钥：

```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 启动服务器

```bash
uvicorn main:app --reload
```

### 4. 访问 API 文档

打开浏览器访问：`http://localhost:8000/docs`

## API 接口

### 获取技能列表
- **URL**: `/skills`
- **方法**: `GET`
- **响应**: 返回所有技能的元数据

### 获取技能详情
- **URL**: `/skills/{skill_id}`
- **方法**: `GET`
- **响应**: 返回技能的完整内容

### 触发技能
- **URL**: `/skills/{skill_id}/trigger`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "prompt": "帮我审查这段代码",
    "parameters": {"pr_number": 123, "strict_mode": true}
  }
  ```
- **响应**: 返回技能执行结果

### 意图匹配
- **URL**: `/intent/match`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "input": "帮我分析项目健康状况"
  }
  ```
- **响应**: 返回匹配的技能列表

### 健康检查
- **URL**: `/health`
- **方法**: `GET`
- **响应**: 返回系统状态和加载的技能数量

## 技能开发

### 技能结构

每个技能是一个独立的文件夹，标准结构如下：

```
<skill-name>/
├── SKILL.md              # 核心配置文件（必需）
├── README.md             # 使用说明（可选）
├── scripts/              # 脚本目录（可选）
│   ├── analyze.py
│   └── utils.js
├── references/           # 参考资料（可选）
│   ├── guidelines.pdf
│   └── templates.md
└── examples/             # 示例（可选）
    └── sample-output.md
```

### SKILL.md 配置

```yaml
---
name: skill-name          # 技能唯一标识
description: 技能描述     # 技能功能描述
version: 1.0.0           # 版本号
author: Your Team        # 作者
tags: [tag1, tag2]       # 标签
triggers:                # 触发关键词
  - 关键词1
  - 关键词2
auto_trigger: true       # 是否自动触发
priority: high           # 优先级（high/medium/low）
scripts:                 # 脚本配置
  - name: script-name
    path: scripts/script.py
    runtime: python3
    timeout: 30s
    permissions:
      - read: ./src
      - write: ./output
parameters:              # 参数配置
  - name: param_name
    type: string
    required: true
    default: "default"
---

## 指令

# 指令内容

## 输出格式

# 输出格式说明
```

## 示例技能

### code-reviewer
- **功能**：按照团队规范进行代码审查
- **触发词**：代码审查、PR 评审、code review、合并请求
- **脚本**：分析代码风格、安全性和性能

### project-health
- **功能**：分析项目健康状况并生成报告
- **触发词**：项目健康、代码质量、项目分析
- **脚本**：分析代码覆盖率、技术债务、依赖安全性

## 最佳实践

1. **技能粒度适中**：一个 Skill 专注一类任务
2. **触发词精准**：避免过于宽泛导致误触发
3. **版本管理**：使用 Git 管理 Skills 目录
4. **文档完整**：编写清晰的 README 和使用示例
5. **测试验证**：创建测试用例验证 Skill 行为

## 注意事项

- 确保 OpenAI API 密钥有效
- 技能脚本应遵循安全最佳实践
- 避免在技能中处理敏感信息
- 合理设置脚本执行超时时间

## 许可证

MIT
