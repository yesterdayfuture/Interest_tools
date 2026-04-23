"""
数据库CRUD操作模块

本模块提供了对数据库模型的增删改查(CRUD)操作封装，包括：
- OntologyCRUD: 本体定义的操作（创建、查询、更新、删除、合并）
- OntologyRelationCRUD: 本体关系的操作
- OntologyPropertyCRUD: 本体属性的操作
- FileCRUD: 文件记录的操作
- PropertyTypeCRUD: 属性类型的操作

所有CRUD类都使用静态方法设计，便于直接调用而不需要实例化。
使用SQLAlchemy 2.0风格的异步查询API。

设计特点：
1. 异步操作：所有数据库操作都是异步的，避免阻塞
2. 类型提示：完善的类型注解，支持IDE智能提示
3. 灵活查询：支持分页、排序、筛选等高级查询
4. 软删除：支持软删除而非物理删除，保留数据历史
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.database import (
    OntologyDefinition, OntologyRelation, OntologyProperty,
    FileRecord, ExtractedEntity, ExtractedRelation, SyncLog,
    PropertyType, PropertyTypeStatus,
    OntologyType, OntologyStatus, FileStatus
)
from app.schemas import (
    OntologyDefinitionCreate, OntologyDefinitionUpdate,
    OntologyRelationCreate, OntologyRelationUpdate,
    OntologyMergeRequest
)


# ==================== 本体定义CRUD ====================

class OntologyCRUD:
    """本体定义CRUD操作"""
    
    @staticmethod
    async def create(db: AsyncSession, obj_in: OntologyDefinitionCreate, 
                     created_by: Optional[str] = None) -> OntologyDefinition:
        """创建本体定义"""
        # 计算层级和路径
        level = 0
        path = ""
        
        if obj_in.parent_id:
            parent = await OntologyCRUD.get_by_id(db, obj_in.parent_id)
            if parent:
                level = parent.level + 1
                path = f"{parent.path}/{parent.id}"
        
        db_obj = OntologyDefinition(
            name=obj_in.name,
            display_name=obj_in.display_name,
            description=obj_in.description,
            parent_id=obj_in.parent_id,
            level=level,
            path=path,
            ontology_type=obj_in.ontology_type,
            properties=obj_in.properties,
            nebula_tag=obj_in.name if obj_in.ontology_type == OntologyType.ENTITY else None,
            nebula_edge=obj_in.name if obj_in.ontology_type == OntologyType.RELATION else None,
            created_by=created_by
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def get_by_id(db: AsyncSession, id: int) -> Optional[OntologyDefinition]:
        """根据ID获取本体定义"""
        result = await db.execute(
            select(OntologyDefinition).where(OntologyDefinition.id == id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_name(db: AsyncSession, name: str, 
                          ontology_type: OntologyType = None) -> Optional[OntologyDefinition]:
        """根据名称获取本体定义"""
        query = select(OntologyDefinition).where(OntologyDefinition.name == name)
        if ontology_type:
            query = query.where(OntologyDefinition.ontology_type == ontology_type)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        ontology_type: OntologyType = None,
        parent_id: Optional[int] = None,
        status: OntologyStatus = None
    ) -> List[OntologyDefinition]:
        """获取多个本体定义"""
        query = select(OntologyDefinition)
        
        if ontology_type:
            query = query.where(OntologyDefinition.ontology_type == ontology_type)
        if parent_id is not None:
            query = query.where(OntologyDefinition.parent_id == parent_id)
        if status:
            query = query.where(OntologyDefinition.status == status)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_tree(
        db: AsyncSession,
        root_id: Optional[int] = None,
        ontology_type: OntologyType = None
    ) -> List[OntologyDefinition]:
        """获取树状结构的本体定义"""
        # 加载所有节点
        query = select(OntologyDefinition).options(
            selectinload(OntologyDefinition.children)
        )
        
        if ontology_type:
            query = query.where(OntologyDefinition.ontology_type == ontology_type)
        
        result = await db.execute(query)
        all_nodes = result.scalars().all()
        
        # 构建树
        node_map = {node.id: node for node in all_nodes}
        roots = []
        
        for node in all_nodes:
            if root_id and node.id == root_id:
                roots.append(node)
            elif not root_id and not node.parent_id:
                roots.append(node)
            
            # 关联子节点
            if node.children:
                node.children = [node_map.get(child.id) for child in node.children 
                                if child.id in node_map]
        
        return roots if not root_id else (roots[0] if roots else None)
    
    @staticmethod
    async def update(
        db: AsyncSession,
        db_obj: OntologyDefinition,
        obj_in: OntologyDefinitionUpdate
    ) -> OntologyDefinition:
        """更新本体定义"""
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def delete(db: AsyncSession, id: int) -> bool:
        """删除本体定义（软删除）"""
        result = await db.execute(
            update(OntologyDefinition)
            .where(OntologyDefinition.id == id)
            .values(status=OntologyStatus.INACTIVE, updated_at=datetime.utcnow())
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def hard_delete(db: AsyncSession, id: int) -> bool:
        """硬删除本体定义"""
        # 先删除子节点
        await db.execute(
            delete(OntologyDefinition).where(OntologyDefinition.parent_id == id)
        )
        
        # 删除本体
        result = await db.execute(
            delete(OntologyDefinition).where(OntologyDefinition.id == id)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def merge(
        db: AsyncSession,
        merge_request: OntologyMergeRequest
    ) -> Optional[OntologyDefinition]:
        """合并本体定义"""
        # 获取目标本体
        target = await OntologyCRUD.get_by_id(db, merge_request.target_id)
        if not target:
            return None
        
        # 更新源本体状态
        for source_id in merge_request.source_ids:
            await db.execute(
                update(OntologyDefinition)
                .where(OntologyDefinition.id == source_id)
                .values(
                    status=OntologyStatus.MERGED,
                    merged_into_id=merge_request.target_id,
                    merged_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
        
        await db.commit()
        await db.refresh(target)
        return target
    
    @staticmethod
    async def update_sync_status(
        db: AsyncSession,
        id: int,
        synced: bool = True
    ) -> bool:
        """更新同步状态"""
        result = await db.execute(
            update(OntologyDefinition)
            .where(OntologyDefinition.id == id)
            .values(
                synced_to_nebula=synced,
                last_sync_at=datetime.utcnow() if synced else None
            )
        )
        await db.commit()
        return result.rowcount > 0


# ==================== 本体关系CRUD ====================

class OntologyRelationCRUD:
    """本体关系CRUD操作"""
    
    @staticmethod
    async def create(db: AsyncSession, obj_in: OntologyRelationCreate) -> OntologyRelation:
        """创建本体关系"""
        db_obj = OntologyRelation(
            name=obj_in.name,
            display_name=obj_in.display_name,
            description=obj_in.description,
            source_type_id=obj_in.source_type_id,
            target_type_id=obj_in.target_type_id,
            is_directed=obj_in.is_directed,
            properties=obj_in.properties,
            nebula_edge_type=obj_in.name
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def get_by_id(db: AsyncSession, id: int) -> Optional[OntologyRelation]:
        """根据ID获取本体关系"""
        result = await db.execute(
            select(OntologyRelation)
            .options(
                joinedload(OntologyRelation.source_type),
                joinedload(OntologyRelation.target_type)
            )
            .where(OntologyRelation.id == id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        source_type_id: Optional[int] = None,
        target_type_id: Optional[int] = None
    ) -> List[OntologyRelation]:
        """获取多个本体关系"""
        query = select(OntologyRelation).options(
            joinedload(OntologyRelation.source_type),
            joinedload(OntologyRelation.target_type)
        )
        
        if source_type_id:
            query = query.where(OntologyRelation.source_type_id == source_type_id)
        if target_type_id:
            query = query.where(OntologyRelation.target_type_id == target_type_id)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def update(
        db: AsyncSession,
        db_obj: OntologyRelation,
        obj_in: OntologyRelationUpdate
    ) -> OntologyRelation:
        """更新本体关系"""
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def delete(db: AsyncSession, id: int) -> bool:
        """删除本体关系"""
        result = await db.execute(
            delete(OntologyRelation).where(OntologyRelation.id == id)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def update_sync_status(
        db: AsyncSession,
        id: int,
        synced: bool = True
    ) -> bool:
        """更新同步状态"""
        result = await db.execute(
            update(OntologyRelation)
            .where(OntologyRelation.id == id)
            .values(
                synced_to_nebula=synced,
                last_sync_at=datetime.utcnow() if synced else None
            )
        )
        await db.commit()
        return result.rowcount > 0


# ==================== 属性类型CRUD ====================

class PropertyTypeCRUD:
    """属性类型CRUD操作"""
    
    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> PropertyType:
        """创建属性类型"""
        db_obj = PropertyType(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def get_by_id(db: AsyncSession, id: int) -> Optional[PropertyType]:
        """根据ID获取属性类型"""
        result = await db.execute(
            select(PropertyType).where(PropertyType.id == id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[PropertyType]:
        """根据名称获取属性类型"""
        result = await db.execute(
            select(PropertyType).where(PropertyType.name == name)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: str = None,
        data_type: str = None
    ) -> List[PropertyType]:
        """获取多个属性类型"""
        query = select(PropertyType)
        
        if status:
            query = query.where(PropertyType.status == status)
        if data_type:
            query = query.where(PropertyType.data_type == data_type)
        
        query = query.order_by(PropertyType.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def count(
        db: AsyncSession,
        status: str = None,
        data_type: str = None
    ) -> int:
        """统计属性类型数量"""
        query = select(func.count(PropertyType.id))
        
        if status:
            query = query.where(PropertyType.status == status)
        if data_type:
            query = query.where(PropertyType.data_type == data_type)
            
        result = await db.execute(query)
        return result.scalar()
    
    @staticmethod
    async def update(
        db: AsyncSession,
        db_obj: PropertyType,
        **kwargs
    ) -> PropertyType:
        """更新属性类型"""
        kwargs["updated_at"] = datetime.utcnow()
        
        for field, value in kwargs.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def delete(db: AsyncSession, id: int) -> bool:
        """删除属性类型（软删除）"""
        result = await db.execute(
            update(PropertyType)
            .where(PropertyType.id == id)
            .values(status="inactive", updated_at=datetime.utcnow())
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def hard_delete(db: AsyncSession, id: int) -> bool:
        """硬删除属性类型"""
        result = await db.execute(
            delete(PropertyType).where(PropertyType.id == id)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def get_usage_count(db: AsyncSession, property_type_id: int) -> int:
        """获取属性类型的使用次数"""
        from app.database import OntologyProperty
        
        result = await db.execute(
            select(func.count(OntologyProperty.id))
            .where(OntologyProperty.property_type_id == property_type_id)
        )
        return result.scalar()


# ==================== 文件记录CRUD ====================

class FileCRUD:
    """文件记录CRUD操作"""
    
    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> FileRecord:
        """创建文件记录"""
        db_obj = FileRecord(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def get_by_id(db: AsyncSession, id: int) -> Optional[FileRecord]:
        """根据ID获取文件记录"""
        result = await db.execute(
            select(FileRecord).where(FileRecord.id == id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: FileStatus = None,
        file_type: str = None
    ) -> List[FileRecord]:
        """获取多个文件记录"""
        query = select(FileRecord)
        
        if status:
            query = query.where(FileRecord.status == status)
        if file_type:
            query = query.where(FileRecord.file_type == file_type)
        
        query = query.order_by(FileRecord.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def count(db: AsyncSession, status: FileStatus = None) -> int:
        """统计文件数量"""
        query = select(func.count(FileRecord.id))
        if status:
            query = query.where(FileRecord.status == status)
        result = await db.execute(query)
        return result.scalar()
    
    @staticmethod
    async def update_status(
        db: AsyncSession,
        id: int,
        status: FileStatus,
        error: str = None
    ) -> bool:
        """更新文件状态"""
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        
        if status == FileStatus.PROCESSED:
            update_data["processed_at"] = datetime.utcnow()
        if error:
            update_data["processing_error"] = error
        
        result = await db.execute(
            update(FileRecord)
            .where(FileRecord.id == id)
            .values(**update_data)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def update_rag_status(
        db: AsyncSession,
        id: int,
        rag_processed: bool,
        chroma_doc_ids: List[str] = None
    ) -> bool:
        """更新RAG处理状态"""
        update_data = {
            "rag_processed": rag_processed,
            "updated_at": datetime.utcnow()
        }
        if chroma_doc_ids:
            update_data["chroma_doc_ids"] = chroma_doc_ids
        
        result = await db.execute(
            update(FileRecord)
            .where(FileRecord.id == id)
            .values(**update_data)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def delete(db: AsyncSession, id: int) -> bool:
        """删除文件记录"""
        result = await db.execute(
            delete(FileRecord).where(FileRecord.id == id)
        )
        await db.commit()
        return result.rowcount > 0


# ==================== 提取实体CRUD ====================

class ExtractedEntityCRUD:
    """提取实体CRUD操作"""
    
    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> ExtractedEntity:
        """创建提取的实体"""
        db_obj = ExtractedEntity(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def create_batch(db: AsyncSession, entities: List[Dict[str, Any]]) -> List[ExtractedEntity]:
        """批量创建提取的实体"""
        db_objs = [ExtractedEntity(**entity) for entity in entities]
        db.add_all(db_objs)
        await db.commit()
        for obj in db_objs:
            await db.refresh(obj)
        return db_objs
    
    @staticmethod
    async def get_by_id(db: AsyncSession, id: int) -> Optional[ExtractedEntity]:
        """根据ID获取提取的实体"""
        result = await db.execute(
            select(ExtractedEntity)
            .options(joinedload(ExtractedEntity.ontology))
            .where(ExtractedEntity.id == id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_file(db: AsyncSession, file_id: int) -> List[ExtractedEntity]:
        """根据文件ID获取提取的实体"""
        result = await db.execute(
            select(ExtractedEntity)
            .options(joinedload(ExtractedEntity.ontology))
            .where(ExtractedEntity.file_id == file_id)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_sync_status(
        db: AsyncSession,
        id: int,
        nebula_vertex_id: str,
        synced: bool = True
    ) -> bool:
        """更新同步状态"""
        result = await db.execute(
            update(ExtractedEntity)
            .where(ExtractedEntity.id == id)
            .values(
                nebula_vertex_id=nebula_vertex_id,
                synced_to_nebula=synced
            )
        )
        await db.commit()
        return result.rowcount > 0


class ExtractedRelationCRUD:
    """提取关系CRUD操作"""
    
    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> ExtractedRelation:
        """创建提取的关系"""
        db_obj = ExtractedRelation(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def create_batch(db: AsyncSession, relations: List[Dict[str, Any]]) -> List[ExtractedRelation]:
        """批量创建提取的关系"""
        db_objs = [ExtractedRelation(**relation) for relation in relations]
        db.add_all(db_objs)
        await db.commit()
        for obj in db_objs:
            await db.refresh(obj)
        return db_objs
    
    @staticmethod
    async def update_sync_status(
        db: AsyncSession,
        id: int,
        nebula_edge_id: str,
        synced: bool = True
    ) -> bool:
        """更新同步状态"""
        result = await db.execute(
            update(ExtractedRelation)
            .where(ExtractedRelation.id == id)
            .values(
                nebula_edge_id=nebula_edge_id,
                synced_to_nebula=synced
            )
        )
        await db.commit()
        return result.rowcount > 0


# ==================== 同步日志CRUD ====================

class SyncLogCRUD:
    """同步日志CRUD操作"""
    
    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> SyncLog:
        """创建同步日志"""
        db_obj = SyncLog(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[SyncLog]:
        """获取同步日志"""
        query = select(SyncLog).order_by(SyncLog.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()