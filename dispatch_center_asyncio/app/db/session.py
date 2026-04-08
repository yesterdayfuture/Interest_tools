"""
数据库会话管理模块

该模块负责数据库连接池的创建和管理，提供异步数据库会话。
使用异步 SQLAlchemy 支持高并发场景下的数据库操作。
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import get_settings

# 获取应用配置
settings = get_settings()

# ==================== 数据库引擎配置 ====================
# create_async_engine 创建异步数据库引擎
# echo: 是否打印 SQL 语句，debug 模式下开启便于调试
# future: 启用 SQLAlchemy 2.0 风格
# pool_pre_ping: 连接池中的连接在使用前进行健康检查，避免使用已断开的连接
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
)

# ==================== 会话工厂配置 ====================
# async_sessionmaker 创建异步会话工厂
# class_: 使用 AsyncSession 类，支持异步操作
# expire_on_commit: 提交后不使对象过期，避免在异步环境中出现意外查询
# autoflush: 不自动刷新，需要手动调用 flush()
# autocommit: 不自动提交，需要手动调用 commit()
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db():
    """
    获取数据库会话的异步生成器
    
    用于 FastAPI 的依赖注入系统，每个请求都会获得一个新的数据库会话。
    会话会在请求结束时自动关闭，并处理事务的提交或回滚。
    
    Yields:
        AsyncSession: 异步数据库会话对象
        
    Example:
        >>> @app.get("/items")
        ... async def get_items(db: AsyncSession = Depends(get_db)):
        ...     result = await db.execute(select(Item))
        ...     return result.scalars().all()
    """
    # 创建新的会话实例
    async with AsyncSessionLocal() as session:
        try:
            # 将会话提供给请求处理函数
            yield session
            # 请求处理成功，提交事务
            await session.commit()
        except Exception:
            # 发生异常，回滚事务
            await session.rollback()
            raise
        finally:
            # 无论成功或失败，都关闭会话
            await session.close()


async def init_db():
    """
    初始化数据库
    
    创建所有定义在模型中的数据表。如果表已存在，则不会重复创建。
    通常在应用启动时调用一次。
    
    Note:
        此操作会导入所有模型类，确保它们被注册到 Base.metadata 中。
        生产环境建议使用 Alembic 进行数据库迁移，而不是直接使用此方法。
        
    Example:
        >>> @asynccontextmanager
        ... async def lifespan(app: FastAPI):
        ...     await init_db()  # 启动时初始化数据库
        ...     yield
        ...     # 关闭时清理资源
    """
    # 导入 Base 基类
    from app.db.base import Base
    # 导入所有模型类，确保它们被注册
    # noqa 标记表示虽然看起来未使用，但导入是为了副作用（注册模型）
    from app.models.task import Task  # noqa

    # 使用引擎创建所有表
    # conn.run_sync 在异步上下文中运行同步函数
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
