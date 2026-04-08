"""
数据库基础模块

该模块定义了 SQLAlchemy 的声明式基类，所有数据库模型都应该继承自 Base。
使用声明式基类可以简化模型定义，将表结构、列定义和 Python 类绑定在一起。
"""

from sqlalchemy.orm import declarative_base

# declarative_base() 创建一个基类，用于定义 ORM 模型
# 所有数据库模型类都应该继承自这个 Base 类
# Base 类会自动处理表名、列名与类属性之间的映射关系
Base = declarative_base()
