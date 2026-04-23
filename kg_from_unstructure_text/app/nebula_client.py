"""
Nebula Graph 客户端模块

本模块提供了与Nebula Graph图数据库交互的封装，包括：
- 连接池管理：维护与Nebula服务器的连接池
- Space管理：自动创建和管理图空间
- Schema管理：创建和管理Tag（节点类型）和Edge（关系类型）
- 数据操作：执行NGQL查询和命令

采用单例模式设计，确保整个应用使用同一个连接池实例。

主要功能：
1. 连接管理：connect()、close()
2. Space管理：ensure_space() - 自动创建Space
3. Schema初始化：init_basic_schema() - 创建基础Tag和Edge
4. 查询执行：execute() - 执行NGQL语句

使用示例：
    from app.nebula_client import nebula_client
    
    # 连接数据库
    await nebula_client.connect()
    
    # 执行查询
    success, result = nebula_client.execute("MATCH (v) RETURN v LIMIT 10")
    
    # 关闭连接
    nebula_client.close()
"""

from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from typing import List, Dict, Any, Optional, Tuple
import json
import logging
from app.config import settings

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NebulaClient:
    """
    Nebula Graph 客户端封装类（单例模式）
    
    封装了与Nebula Graph数据库的所有交互操作，提供高级API：
    - 连接池管理
    - Space自动创建
    - Schema初始化
    - NGQL执行
    
    单例模式确保整个应用只有一个连接池实例，避免资源浪费。
    
    Attributes:
        config (Config): Nebula连接配置
        pool (ConnectionPool): 连接池实例
        session: 当前会话对象
        _initialized (bool): 是否已初始化标志
    
    Example:
        client = NebulaClient()
        await client.connect()
        success, data = client.execute("SHOW SPACES")
    """
    
    _instance = None  # 单例实例
    
    def __new__(cls):
        """
        创建单例实例
        
        确保只有一个NebulaClient实例存在
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        初始化客户端
        
        仅执行一次初始化，避免重复创建连接池
        """
        if self._initialized:
            return
            
        # 创建连接配置
        self.config = Config()
        self.config.max_connection_pool_size = 10  # 最大连接池大小
        self.config.timeout = 60000  # 连接超时时间（毫秒）
        
        # 创建连接池
        self.pool = ConnectionPool()
        self.session = None
        self._initialized = True
    
    async def connect(self) -> bool:
        """
        连接到Nebula Graph数据库
        
        建立与Nebula Graph的连接，初始化连接池并验证连接。
        连接成功后会自动切换到配置的Space。
        
        Returns:
            bool: 连接成功返回True，失败返回False
            
        Raises:
            不抛出异常，错误会被捕获并记录日志
            
        Example:
            if await nebula_client.connect():
                print("连接成功")
        """
        try:
            ok = self.pool.init(
                [(settings.NEBULA_HOST, settings.NEBULA_PORT)],
                self.config
            )
            if not ok:
                logger.error("Failed to initialize connection pool")
                return False
            
            # 获取会话
            self.session = self.pool.get_session(
                settings.NEBULA_USER,
                settings.NEBULA_PASSWORD
            )
            
            # 切换到指定space
            result = self.session.execute(f"USE {settings.NEBULA_SPACE}")
            if not result.is_succeeded():
                logger.error(f"Failed to use space {settings.NEBULA_SPACE}: {result.error_msg()}")
                return False
            
            logger.info(f"Connected to Nebula Graph: {settings.NEBULA_SPACE}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Nebula Graph: {e}")
            return False
    
    def ensure_space(self, space_name: str = None, wait_for_sync: bool = True) -> bool:
        """确保space存在，不存在则创建
        
        Args:
            space_name: space名称，默认为配置中的NEBULA_SPACE
            wait_for_sync: 是否等待space同步完成
        """
        if space_name is None:
            space_name = settings.NEBULA_SPACE
        
        try:
            # 检查space是否存在
            result = self.session.execute(f"SHOW SPACES")
            if not result.is_succeeded():
                logger.error(f"Failed to show spaces: {result.error_msg()}")
                return False
            
            spaces = [row.values[0].get_svalue() for row in result.rows()]
            
            if space_name not in spaces:
                # 创建space
                create_stmt = f"""
                CREATE SPACE IF NOT EXISTS {space_name} (
                    partition_num = 10,
                    replica_factor = 1,
                    vid_type = FIXED_STRING(256)
                )
                """
                result = self.session.execute(create_stmt)
                if not result.is_succeeded():
                    logger.error(f"Failed to create space: {result.error_msg()}")
                    return False
                
                logger.info(f"Created space: {space_name}")
                
                # 等待space同步完成
                if wait_for_sync:
                    import time
                    max_wait = 30  # 最多等待30秒
                    wait_interval = 1
                    elapsed = 0
                    
                    logger.info(f"Waiting for space {space_name} to be ready...")
                    while elapsed < max_wait:
                        time.sleep(wait_interval)
                        elapsed += wait_interval
                        
                        # 检查space是否可用
                        result = self.session.execute(f"DESCRIBE SPACE {space_name}")
                        if result.is_succeeded():
                            logger.info(f"Space {space_name} is ready after {elapsed}s")
                            break
                    else:
                        logger.warning(f"Timeout waiting for space {space_name}, but continuing...")
            
            # 使用space
            result = self.session.execute(f"USE {space_name}")
            if result.is_succeeded():
                logger.info(f"Using space: {space_name}")
                return True
            else:
                logger.error(f"Failed to use space {space_name}: {result.error_msg()}")
                return False
            
        except Exception as e:
            logger.error(f"Error ensuring space: {e}")
            return False
    
    def init_basic_schema(self) -> bool:
        """初始化基础Schema（Tag和Edge）
        
        创建一些基础的Tag和Edge类型，用于通用实体和关系
        """
        try:
            logger.info("Initializing basic Nebula schema...")
            
            # 创建基础实体Tag
            basic_tags = [
                {
                    "name": "Entity",
                    "comment": "基础实体",
                    "properties": {
                        "name": "STRING",
                        "ontology_id": "INT64",
                        "created_at": "DATETIME",
                        "updated_at": "DATETIME"
                    }
                },
                {
                    "name": "Concept",
                    "comment": "概念实体",
                    "properties": {
                        "name": "STRING",
                        "description": "STRING",
                        "ontology_id": "INT64"
                    }
                }
            ]
            
            for tag in basic_tags:
                # 检查Tag是否存在
                result = self.session.execute(f"DESCRIBE TAG {tag['name']}")
                if result.is_succeeded():
                    logger.info(f"Tag {tag['name']} already exists")
                    continue
                
                # 构建属性定义
                props_def = ", ".join([f"`{k}` {v}" for k, v in tag["properties"].items()])
                create_stmt = f"CREATE TAG IF NOT EXISTS `{tag['name']}` ({props_def})"
                
                result = self.session.execute(create_stmt)
                if result.is_succeeded():
                    logger.info(f"Created tag: {tag['name']}")
                else:
                    logger.error(f"Failed to create tag {tag['name']}: {result.error_msg()}")
            
            # 创建基础关系Edge
            basic_edges = [
                {
                    "name": "RELATED_TO",
                    "comment": "相关关系",
                    "properties": {
                        "relation_type": "STRING",
                        "weight": "DOUBLE",
                        "created_at": "DATETIME"
                    }
                },
                {
                    "name": "BELONGS_TO",
                    "comment": "属于关系",
                    "properties": {
                        "created_at": "DATETIME"
                    }
                }
            ]
            
            for edge in basic_edges:
                # 检查Edge是否存在
                result = self.session.execute(f"DESCRIBE EDGE {edge['name']}")
                if result.is_succeeded():
                    logger.info(f"Edge {edge['name']} already exists")
                    continue
                
                # 构建属性定义
                props_def = ", ".join([f"`{k}` {v}" for k, v in edge["properties"].items()])
                create_stmt = f"CREATE EDGE IF NOT EXISTS `{edge['name']}` ({props_def})"
                
                result = self.session.execute(create_stmt)
                if result.is_succeeded():
                    logger.info(f"Created edge: {edge['name']}")
                else:
                    logger.error(f"Failed to create edge {edge['name']}: {result.error_msg()}")
            
            logger.info("Basic schema initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing basic schema: {e}")
            return False
    
    def execute(self, ngql: str) -> Tuple[bool, List[Dict]]:
        """执行Nebula Graph查询"""
        try:
            result = self.session.execute(ngql)
            
            if not result.is_succeeded():
                logger.error(f"NGQL execution failed: {result.error_msg()}")
                return False, []
            
            # 解析结果
            rows = []
            if result.rows():
                column_names = [col.get_name() for col in result.keys()]
                for row in result.rows():
                    row_dict = {}
                    for i, col in enumerate(row.values):
                        row_dict[column_names[i]] = self._parse_value(col)
                    rows.append(row_dict)
            
            return True, rows
            
        except Exception as e:
            logger.error(f"Error executing NGQL: {e}")
            return False, []
    
    def _parse_value(self, value) -> Any:
        """解析Nebula返回值"""
        if value.is_null():
            return None
        elif value.is_empty():
            return None
        elif value.is_bool():
            return value.get_b_value()
        elif value.is_int():
            return value.get_i_value()
        elif value.is_float():
            return value.get_f_value()
        elif value.is_string():
            return value.get_s_value()
        elif value.is_list():
            return [self._parse_value(v) for v in value.get_l_value()]
        elif value.is_set():
            return [self._parse_value(v) for v in value.get_u_value()]
        elif value.is_map():
            return {k: self._parse_value(v) for k, v in value.get_m_value().items()}
        elif value.is_vertex():
            vertex = value.get_v_value()
            return {
                "id": vertex.vid.get_s_value(),
                "tags": [tag.tag_name for tag in vertex.tags]
            }
        elif value.is_edge():
            edge = value.get_e_value()
            return {
                "src": edge.src.get_s_value(),
                "dst": edge.dst.get_s_value(),
                "type": edge.name,
                "ranking": edge.ranking
            }
        else:
            return str(value)
    
    def create_tag(self, tag_name: str, properties: Dict[str, str]) -> bool:
        """创建Tag（节点类型）"""
        try:
            # 检查tag是否存在
            result = self.session.execute("SHOW TAGS")
            if result.is_succeeded():
                existing_tags = [row.values[0].get_svalue() for row in result.rows()]
                if tag_name in existing_tags:
                    logger.info(f"Tag {tag_name} already exists")
                    return True
            
            # 构建属性定义
            props_def = []
            for prop_name, prop_type in properties.items():
                props_def.append(f"`{prop_name}` {prop_type}")
            
            props_str = ", ".join(props_def) if props_def else ""
            
            create_stmt = f"CREATE TAG IF NOT EXISTS `{tag_name}` ({props_str})"
            result = self.session.execute(create_stmt)
            
            if not result.is_succeeded():
                logger.error(f"Failed to create tag {tag_name}: {result.error_msg()}")
                return False
            
            logger.info(f"Created tag: {tag_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating tag {tag_name}: {e}")
            return False
    
    def alter_tag(self, tag_name: str, add_props: Dict[str, str] = None, 
                  drop_props: List[str] = None) -> bool:
        """修改Tag属性"""
        try:
            # 添加属性
            if add_props:
                props_def = ", ".join([f"`{k}` {v}" for k, v in add_props.items()])
                stmt = f"ALTER TAG `{tag_name}` ADD ({props_def})"
                result = self.session.execute(stmt)
                if not result.is_succeeded():
                    logger.error(f"Failed to alter tag {tag_name}: {result.error_msg()}")
                    return False
            
            # 删除属性
            if drop_props:
                props_str = ", ".join([f"`{p}`" for p in drop_props])
                stmt = f"ALTER TAG `{tag_name}` DROP ({props_str})"
                result = self.session.execute(stmt)
                if not result.is_succeeded():
                    logger.error(f"Failed to drop properties from {tag_name}: {result.error_msg()}")
                    return False
            
            logger.info(f"Altered tag: {tag_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error altering tag {tag_name}: {e}")
            return False
    
    def create_edge(self, edge_name: str, properties: Dict[str, str]) -> bool:
        """创建Edge Type（边类型）"""
        try:
            # 检查edge是否存在
            result = self.session.execute("SHOW EDGES")
            if result.is_succeeded():
                existing_edges = [row.values[0].get_svalue() for row in result.rows()]
                if edge_name in existing_edges:
                    logger.info(f"Edge {edge_name} already exists")
                    return True
            
            # 构建属性定义
            props_def = []
            for prop_name, prop_type in properties.items():
                props_def.append(f"`{prop_name}` {prop_type}")
            
            props_str = ", ".join(props_def) if props_def else ""
            
            create_stmt = f"CREATE EDGE IF NOT EXISTS `{edge_name}` ({props_str})"
            result = self.session.execute(create_stmt)
            
            if not result.is_succeeded():
                logger.error(f"Failed to create edge {edge_name}: {result.error_msg()}")
                return False
            
            logger.info(f"Created edge: {edge_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating edge {edge_name}: {e}")
            return False
    
    def alter_edge(self, edge_name: str, add_props: Dict[str, str] = None,
                   drop_props: List[str] = None) -> bool:
        """修改Edge Type属性"""
        try:
            if add_props:
                props_def = ", ".join([f"`{k}` {v}" for k, v in add_props.items()])
                stmt = f"ALTER EDGE `{edge_name}` ADD ({props_def})"
                result = self.session.execute(stmt)
                if not result.is_succeeded():
                    logger.error(f"Failed to alter edge {edge_name}: {result.error_msg()}")
                    return False
            
            if drop_props:
                props_str = ", ".join([f"`{p}`" for p in drop_props])
                stmt = f"ALTER EDGE `{edge_name}` DROP ({props_str})"
                result = self.session.execute(stmt)
                if not result.is_succeeded():
                    logger.error(f"Failed to drop properties from {edge_name}: {result.error_msg()}")
                    return False
            
            logger.info(f"Altered edge: {edge_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error altering edge {edge_name}: {e}")
            return False
    
    def insert_vertex(self, tag_name: str, vid: str, properties: Dict[str, Any]) -> bool:
        """插入顶点"""
        try:
            # 构建属性值
            props_str = self._build_props_string(properties)
            
            stmt = f'INSERT VERTEX `{tag_name}` ({self._build_props_names(properties)}) VALUES "{vid}": ({props_str})'
            result = self.session.execute(stmt)
            
            if not result.is_succeeded():
                logger.error(f"Failed to insert vertex {vid}: {result.error_msg()}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error inserting vertex {vid}: {e}")
            return False
    
    def upsert_vertex(self, tag_name: str, vid: str, properties: Dict[str, Any]) -> bool:
        """更新或插入顶点"""
        try:
            # 先尝试插入
            if self.insert_vertex(tag_name, vid, properties):
                return True
            
            # 插入失败，尝试更新
            update_items = []
            for k, v in properties.items():
                update_items.append(f"`{k}` = {self._format_value(v)}")
            
            stmt = f'UPDATE VERTEX ON `{tag_name}` "{vid}" SET {", ".join(update_items)}'
            result = self.session.execute(stmt)
            
            if not result.is_succeeded():
                logger.error(f"Failed to upsert vertex {vid}: {result.error_msg()}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting vertex {vid}: {e}")
            return False
    
    def insert_edge(self, edge_name: str, src_vid: str, dst_vid: str, 
                    properties: Dict[str, Any], ranking: int = 0) -> bool:
        """插入边"""
        try:
            props_str = self._build_props_string(properties)
            props_names = self._build_props_names(properties)
            
            stmt = f'INSERT EDGE `{edge_name}` ({props_names}) VALUES "{src_vid}" -> "{dst_vid}"@{ranking}: ({props_str})'
            result = self.session.execute(stmt)
            
            if not result.is_succeeded():
                logger.error(f"Failed to insert edge: {result.error_msg()}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error inserting edge: {e}")
            return False
    
    def _build_props_names(self, properties: Dict[str, Any]) -> str:
        """构建属性名字符串"""
        return ", ".join([f"`{k}`" for k in properties.keys()])
    
    def _build_props_string(self, properties: Dict[str, Any]) -> str:
        """构建属性值字符串"""
        values = []
        for v in properties.values():
            values.append(self._format_value(v))
        return ", ".join(values)
    
    def _format_value(self, value: Any) -> str:
        """格式化值为NGQL字符串"""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # 转义引号
            escaped = value.replace('"', '\\"').replace("'", "\\'")
            return f'"{escaped}"'
        elif isinstance(value, list):
            items = [self._format_value(item) for item in value]
            return f'[{", ".join(items)}]'
        else:
            return f'"{str(value)}"'
    
    def delete_vertex(self, vid: str) -> bool:
        """删除顶点及其关联的边"""
        try:
            stmt = f'DELETE VERTEX "{vid}" WITH EDGE'
            result = self.session.execute(stmt)
            return result.is_succeeded()
        except Exception as e:
            logger.error(f"Error deleting vertex {vid}: {e}")
            return False
    
    def delete_edge(self, edge_name: str, src_vid: str, dst_vid: str, ranking: int = 0) -> bool:
        """删除边"""
        try:
            stmt = f'DELETE EDGE `{edge_name}` "{src_vid}" -> "{dst_vid}"@{ranking}'
            result = self.session.execute(stmt)
            return result.is_succeeded()
        except Exception as e:
            logger.error(f"Error deleting edge: {e}")
            return False
    
    def close(self):
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            logger.info("Nebula connection pool closed")


# 全局客户端实例
nebula_client = NebulaClient()