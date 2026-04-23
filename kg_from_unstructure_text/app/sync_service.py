"""
数据同步服务模块

本模块负责将SQLite数据库中的数据同步到Nebula Graph图数据库，
包括本体定义、实体数据、关系数据等。

主要功能：
1. 本体同步：将Ontology定义同步为Nebula的Tag和Edge
2. 实体同步：将提取的实体同步为Nebula的Vertex
3. 关系同步：将提取的关系同步为Nebula的Edge
4. 同步日志：记录同步历史和状态

同步策略：
- 增量同步：只同步未同步或已变更的数据
- 批量处理：支持批量同步以提高效率
- 错误处理：失败时记录详细错误信息
- 事务支持：确保数据一致性

数据类型映射：
- string -> STRING
- integer/int -> INT64
- float/double -> DOUBLE
- boolean/bool -> BOOL
- datetime -> DATETIME
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.database import OntologyDefinition, OntologyRelation, OntologyType, OntologyStatus
from app.crud import OntologyCRUD, OntologyRelationCRUD, SyncLogCRUD
from app.schemas import SyncRequest
from app.nebula_client import NebulaClient

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Nebula数据类型映射表
# 用于将Python/SQLite的数据类型转换为Nebula Graph的数据类型
NEBULA_TYPE_MAPPING = {
    "string": "STRING",
    "integer": "INT64",
    "int": "INT64",
    "float": "DOUBLE",
    "double": "DOUBLE",
    "boolean": "BOOL",
    "bool": "BOOL",
    "datetime": "DATETIME",
    "date": "DATE",
    "time": "TIME"
}


class OntologySyncService:
    """本体同步服务 - 负责将本体定义同步到Nebula Graph"""
    
    def __init__(self, db: AsyncSession, nebula_client: NebulaClient):
        self.db = db
        self.nebula = nebula_client
    
    async def sync_ontology_to_nebula(self, sync_request: SyncRequest) -> Dict[str, Any]:
        """同步本体到Nebula Graph"""
        results = {
            "success": True,
            "message": "",
            "total_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "failed_items": []
        }
        
        try:
            # 确保Nebula连接
            if not await self.nebula.connect():
                results["success"] = False
                results["message"] = "无法连接到Nebula Graph"
                return results
            
            # 确保space存在
            if not self.nebula.ensure_space():
                results["success"] = False
                results["message"] = "无法创建或使用Nebula Space"
                return results
            
            # 同步实体类型（Tag）
            if sync_request.sync_type in ["all", "ontology_only", "entities_only"]:
                entity_results = await self._sync_entities(sync_request.ontology_ids)
                results["total_count"] += entity_results["total"]
                results["success_count"] += entity_results["success"]
                results["failed_count"] += entity_results["failed"]
                results["failed_items"].extend(entity_results["failed_items"])
            
            # 同步关系类型（Edge）
            if sync_request.sync_type in ["all", "ontology_only", "relations_only"]:
                relation_results = await self._sync_relations()
                results["total_count"] += relation_results["total"]
                results["success_count"] += relation_results["success"]
                results["failed_count"] += relation_results["failed"]
                results["failed_items"].extend(relation_results["failed_items"])
            
            # 记录同步日志
            status = "success" if results["failed_count"] == 0 else ("partial" if results["success_count"] > 0 else "failed")
            await SyncLogCRUD.create(
                self.db,
                sync_type=sync_request.sync_type,
                target="nebula",
                status=status,
                total_count=results["total_count"],
                success_count=results["success_count"],
                failed_count=results["failed_count"],
                details={"failed_items": results["failed_items"]}
            )
            
            results["message"] = f"同步完成: 成功 {results['success_count']}, 失败 {results['failed_count']}"
            results["success"] = results["failed_count"] == 0
            
        except Exception as e:
            logger.error(f"同步失败: {e}")
            results["success"] = False
            results["message"] = f"同步失败: {str(e)}"
        
        return results
    
    async def _sync_entities(self, ontology_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """同步实体类型到Nebula Tag"""
        result = {"total": 0, "success": 0, "failed": 0, "failed_items": []}
        
        # 获取要同步的实体定义
        if ontology_ids:
            entities = []
            for oid in ontology_ids:
                entity = await OntologyCRUD.get_by_id(self.db, oid)
                if entity and entity.ontology_type == OntologyType.ENTITY:
                    entities.append(entity)
        else:
            entities = await OntologyCRUD.get_multi(
                self.db, ontology_type=OntologyType.ENTITY, status=OntologyStatus.ACTIVE
            )
        
        result["total"] = len(entities)
        
        for entity in entities:
            try:
                # 转换属性定义
                nebula_props = {}
                for prop_name, prop_def in entity.properties.items():
                    if isinstance(prop_def, dict):
                        data_type = prop_def.get("data_type", "string")
                    else:
                        data_type = "string"
                    nebula_type = NEBULA_TYPE_MAPPING.get(data_type, "STRING")
                    nebula_props[prop_name] = nebula_type
                
                # 添加默认属性
                nebula_props["ontology_id"] = "INT64"
                nebula_props["created_at"] = "DATETIME"
                
                # 创建或更新Tag
                tag_name = entity.nebula_tag or entity.name
                if self.nebula.create_tag(tag_name, nebula_props):
                    # 更新同步状态
                    await OntologyCRUD.update_sync_status(self.db, entity.id, True)
                    result["success"] += 1
                    logger.info(f"同步实体成功: {entity.name} -> {tag_name}")
                else:
                    result["failed"] += 1
                    result["failed_items"].append({
                        "id": entity.id,
                        "name": entity.name,
                        "error": "创建Tag失败"
                    })
                    
            except Exception as e:
                logger.error(f"同步实体 {entity.name} 失败: {e}")
                result["failed"] += 1
                result["failed_items"].append({
                    "id": entity.id,
                    "name": entity.name,
                    "error": str(e)
                })
        
        return result
    
    async def _sync_relations(self) -> Dict[str, Any]:
        """同步关系到Nebula Edge"""
        result = {"total": 0, "success": 0, "failed": 0, "failed_items": []}
        
        # 获取所有关系定义
        relations = await OntologyRelationCRUD.get_multi(self.db)
        result["total"] = len(relations)
        
        for relation in relations:
            try:
                # 转换属性定义
                nebula_props = {}
                for prop_name, prop_def in relation.properties.items():
                    if isinstance(prop_def, dict):
                        data_type = prop_def.get("data_type", "string")
                    else:
                        data_type = "string"
                    nebula_type = NEBULA_TYPE_MAPPING.get(data_type, "STRING")
                    nebula_props[prop_name] = nebula_type
                
                # 添加默认属性
                nebula_props["relation_id"] = "INT64"
                nebula_props["created_at"] = "DATETIME"
                
                # 创建或更新Edge
                edge_name = relation.nebula_edge_type or relation.name
                if self.nebula.create_edge(edge_name, nebula_props):
                    # 更新同步状态
                    await OntologyRelationCRUD.update_sync_status(self.db, relation.id, True)
                    result["success"] += 1
                    logger.info(f"同步关系成功: {relation.name} -> {edge_name}")
                else:
                    result["failed"] += 1
                    result["failed_items"].append({
                        "id": relation.id,
                        "name": relation.name,
                        "error": "创建Edge失败"
                    })
                    
            except Exception as e:
                logger.error(f"同步关系 {relation.name} 失败: {e}")
                result["failed"] += 1
                result["failed_items"].append({
                    "id": relation.id,
                    "name": relation.name,
                    "error": str(e)
                })
        
        return result
    
    async def update_ontology_in_nebula(self, ontology_id: int) -> bool:
        """更新Nebula中的本体定义（属性变更时）"""
        try:
            entity = await OntologyCRUD.get_by_id(self.db, ontology_id)
            if not entity or not entity.synced_to_nebula:
                return False
            
            tag_name = entity.nebula_tag or entity.name
            
            # 转换属性定义
            nebula_props = {}
            for prop_name, prop_def in entity.properties.items():
                if isinstance(prop_def, dict):
                    data_type = prop_def.get("data_type", "string")
                else:
                    data_type = "string"
                nebula_type = NEBULA_TYPE_MAPPING.get(data_type, "STRING")
                nebula_props[prop_name] = nebula_type
            
            # 使用ALTER TAG添加新属性
            # 注意：Nebula Graph不支持直接修改属性类型，只能添加或删除
            if self.nebula.alter_tag(tag_name, add_props=nebula_props):
                logger.info(f"更新Nebula Tag成功: {tag_name}")
                return True
            else:
                logger.error(f"更新Nebula Tag失败: {tag_name}")
                return False
                
        except Exception as e:
            logger.error(f"更新Nebula本体失败: {e}")
            return False


class EntitySyncService:
    """实体同步服务 - 负责将提取的实体和关系同步到Nebula Graph"""
    
    def __init__(self, db: AsyncSession, nebula_client: NebulaClient):
        self.db = db
        self.nebula = nebula_client
    
    async def sync_entity_to_nebula(self, entity_id: int) -> bool:
        """同步单个实体到Nebula"""
        from app.crud import ExtractedEntityCRUD
        
        try:
            entity = await ExtractedEntityCRUD.get_by_id(self.db, entity_id)
            if not entity:
                return False
            
            # 获取本体定义
            ontology = await OntologyCRUD.get_by_id(self.db, entity.ontology_id)
            if not ontology or not ontology.nebula_tag:
                logger.error(f"实体 {entity_id} 的本体未同步到Nebula")
                return False
            
            # 构建顶点ID
            vertex_id = f"{ontology.name}_{entity.id}"
            
            # 构建属性
            properties = {
                "name": entity.name,
                "ontology_id": entity.ontology_id,
                **entity.properties
            }
            
            # 插入或更新顶点
            if self.nebula.upsert_vertex(ontology.nebula_tag, vertex_id, properties):
                # 更新同步状态
                await ExtractedEntityCRUD.update_sync_status(
                    self.db, entity.id, vertex_id, True
                )
                logger.info(f"同步实体到Nebula成功: {vertex_id}")
                return True
            else:
                logger.error(f"同步实体到Nebula失败: {vertex_id}")
                return False
                
        except Exception as e:
            logger.error(f"同步实体 {entity_id} 失败: {e}")
            return False
    
    async def sync_relation_to_nebula(self, relation_id: int) -> bool:
        """同步单个关系到Nebula"""
        from app.crud import ExtractedRelationCRUD
        from sqlalchemy.orm import joinedload
        from sqlalchemy import select
        from app.database import ExtractedRelation
        
        try:
            # 获取关系详情
            result = await self.db.execute(
                select(ExtractedRelation)
                .options(
                    joinedload(ExtractedRelation.source_entity),
                    joinedload(ExtractedRelation.target_entity),
                    joinedload(ExtractedRelation.relation)
                )
                .where(ExtractedRelation.id == relation_id)
            )
            relation = result.scalar_one_or_none()
            
            if not relation:
                return False
            
            # 检查源实体和目标实体是否已同步
            if not relation.source_entity or not relation.target_entity:
                logger.error(f"关系 {relation_id} 缺少源实体或目标实体")
                return False
            
            # 构建顶点ID
            source_vid = relation.source_entity.nebula_vertex_id
            target_vid = relation.target_entity.nebula_vertex_id
            
            if not source_vid or not target_vid:
                logger.error(f"关系 {relation_id} 的实体未同步到Nebula")
                return False
            
            # 构建属性
            properties = {
                "relation_id": relation.relation_id,
                **relation.properties
            }
            
            # 插入边
            edge_name = relation.relation.nebula_edge_type or relation.relation.name
            if self.nebula.insert_edge(edge_name, source_vid, target_vid, properties):
                edge_id = f"{source_vid}->{target_vid}"
                await ExtractedRelationCRUD.update_sync_status(
                    self.db, relation.id, edge_id, True
                )
                logger.info(f"同步关系到Nebula成功: {edge_id}")
                return True
            else:
                logger.error(f"同步关系到Nebula失败")
                return False
                
        except Exception as e:
            logger.error(f"同步关系 {relation_id} 失败: {e}")
            return False