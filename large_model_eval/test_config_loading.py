#!/usr/bin/env python3
"""
配置加载测试脚本

演示 api_key 和 base_url 的多种配置方式
"""

import os
import sys
from pathlib import Path

# 修改路径以避免导入 __init__.py
sys.path.insert(0, str(Path(__file__).parent))

# 测试配置加载功能
def test_yaml_loading():
    """测试YAML配置文件加载"""
    import yaml
    
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("错误: config.yaml 文件不存在")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("\n" + "="*60)
    print("YAML配置文件内容")
    print("="*60)
    
    openai_config = config.get("models", {}).get("openai", {})
    
    print(f"\napi_key: {'已配置' if openai_config.get('api_key') else '未配置'}")
    print(f"base_url: {openai_config.get('base_url', '未配置')}")
    print(f"default_model: {openai_config.get('default_model', '未配置')}")
    print(f"timeout: {openai_config.get('timeout', '未配置')}")
    print(f"max_retries: {openai_config.get('max_retries', '未配置')}")


def show_config_examples():
    """显示配置示例"""
    print("\n" + "="*60)
    print("配置方式示例")
    print("="*60)
    
    print("""
方式1 - 显式传入（优先级最高）:
    from llm_evaluator.models.openai_model import OpenAIModel
    
    model = OpenAIModel(
        api_key="sk-your-key",
        base_url="https://api.example.com/v1",
        model_name="gpt-3.5-turbo"
    )

方式2 - 环境变量:
    export OPENAI_API_KEY="sk-your-key"
    export OPENAI_BASE_URL="https://api.example.com/v1"
    
    model = OpenAIModel(model_name="gpt-3.5-turbo")

方式3 - YAML配置文件 (config.yaml):
    models:
      openai:
        api_key: "sk-your-key"
        base_url: "https://api.example.com/v1"
        default_model: "gpt-3.5-turbo"
    
    model = OpenAIModel()

方式4 - 混合配置（显式 + 文件）:
    # config.yaml 包含 base_url 和 model
    # 代码中只传入 api_key
    
    model = OpenAIModel(
        api_key="sk-your-key",
        config_path="config.yaml"
    )

方式5 - 使用 from_config 类方法:
    config_dict = {
        "model": "gpt-4",
        "api_key": "sk-your-key",
        "base_url": "https://api.example.com/v1"
    }
    
    # 仅从字典加载
    model = OpenAIModel.from_config(config_dict)
    
    # 或从字典和YAML合并加载
    model = OpenAIModel.from_config(config_dict, config_path="config.yaml")

配置优先级（从高到低）:
    1. 显式传入的参数（代码中直接传入）
    2. 环境变量（OPENAI_API_KEY, OPENAI_BASE_URL）
    3. YAML配置文件（config.yaml）
    4. 默认值

获取配置来源:
    model = OpenAIModel(api_key="sk-key")
    source = model.get_config_source()
    print(source)  # {'api_key': '显式配置', 'base_url': '默认值'}
    """)


def show_code_changes():
    """显示代码修改说明"""
    print("\n" + "="*60)
    print("代码修改说明")
    print("="*60)
    
    print("""
OpenAIModel 类已更新，支持以下特性:

1. 新增 __init__ 参数:
   - config_path: YAML配置文件路径（可选）
   
2. 新增辅助函数:
   - _load_yaml_config(): 加载YAML配置文件
   - _get_config_value(): 从嵌套字典获取配置值
   
3. 配置加载优先级:
   api_key/base_url 按以下顺序获取:
   ① 显式传入的参数
   ② 环境变量
   ③ YAML配置文件
   ④ 默认值

4. 新增方法:
   - get_config_source(): 获取配置来源信息，用于调试
   - from_config() 支持 config_path 参数

5. API密钥检查:
   从构造函数移至 initialize() 方法，
   支持延迟加载和更灵活的配置方式

配置文件结构 (config.yaml):
    models:
      openai:
        api_key: ""              # API密钥
        base_url: "..."          # API基础URL
        default_model: "..."     # 默认模型
        timeout: 30              # 超时时间
        max_retries: 3           # 重试次数
    """)


if __name__ == "__main__":
    print("\n大语言模型评估系统 - 配置加载测试")
    
    try:
        test_yaml_loading()
        show_config_examples()
        show_code_changes()
        
        print("\n" + "="*60)
        print("测试完成!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
