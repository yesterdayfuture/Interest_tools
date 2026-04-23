"""
实体提取路由模块

本模块提供从文本中提取实体和关系的RESTful API接口。
使用大语言模型进行智能提取，并支持批量处理。

功能列表：
- POST /extraction/extract: 从单条文本中提取实体和关系
- POST /extraction/batch-extract: 批量提取多条文本
- GET /extraction/entities: 获取提取的实体列表
- GET /extraction/entities/{id}: 获取单个实体详情
- GET /extraction/relations: 获取提取的关系列表
- GET /extraction/relations/{id}: 获取单个关系详情
- POST /extraction/sync-to-nebula: 将提取结果同步到Nebula Graph

提取流程：
1. 接收文本内容和可选参数
2. 加载对应的本体定义作为模板
3. 调用大模型进行实体和关系识别
4. 解析模型输出并验证
5. 保存到数据库
6. 可选：同步到Nebula Graph

使用场景：
- 客服对话分析
- 文档内容结构化
- 知识图谱构建
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas import (
    EntityExtractRequest, BatchExtractResponse,
    ExtractedEntityResponse, ExtractedRelationResponse,
    APIResponse
)
from app.extraction_service import EntityExtractionService

# 创建API路由实例
router = APIRouter(prefix="/extraction", tags=["实体提取"])


@router.post("/extract", response_model=APIResponse)
async def extract_entities(
    request: EntityExtractRequest,
    db: AsyncSession = Depends(get_db)
):
    """从文本中提取实体和关系"""
    try:
        service = EntityExtractionService(db)
        result = await service.extract_from_text(
            text=request.text,
            file_id=request.file_id,
            ontology_ids=request.ontology_ids
        )
        
        if result["success"]:
            return APIResponse(
                message=f"提取成功，共提取 {len(result['entities'])} 个实体，{len(result['relations'])} 个关系",
                data=result
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "提取失败")
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"提取失败: {str(e)}"
        )


@router.post("/batch-extract", response_model=APIResponse)
async def batch_extract_entities(
    texts: List[str],
    file_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """批量提取多个文本"""
    try:
        service = EntityExtractionService(db)
        results = await service.batch_extract_from_texts(texts, file_id)
        
        total_entities = sum(len(r.get("entities", [])) for r in results)
        total_relations = sum(len(r.get("relations", [])) for r in results)
        
        return APIResponse(
            message=f"批量提取完成，共提取 {total_entities} 个实体，{total_relations} 个关系",
            data={
                "total_texts": len(texts),
                "total_entities": total_entities,
                "total_relations": total_relations,
                "results": results
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量提取失败: {str(e)}"
        )


@router.get("/entities", response_model=APIResponse)
async def list_extracted_entities(
    file_id: int = None,
    ontology_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """获取提取的实体列表"""
    from app.crud import ExtractedEntityCRUD
    
    if file_id:
        entities = await ExtractedEntityCRUD.get_by_file(db, file_id)
    else:
        # 简化实现，获取所有实体
        from sqlalchemy import select
        from app.database import ExtractedEntity
        from sqlalchemy.orm import joinedload
        
        query = select(ExtractedEntity).options(
            joinedload(ExtractedEntity.ontology)
        ).limit(100)
        result = await db.execute(query)
        entities = result.scalars().all()
    
    return APIResponse(
        data={
            "total": len(entities),
            "items": [ExtractedEntityResponse.model_validate(e) for e in entities]
        }
    )


@router.get("/entities/{entity_id}", response_model=APIResponse)
async def get_entity_detail(
    entity_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取实体详情"""
    from app.crud import ExtractedEntityCRUD
    
    entity = await ExtractedEntityCRUD.get_by_id(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    
    return APIResponse(
        data=ExtractedEntityResponse.model_validate(entity)
    )


@router.post("/entities/{entity_id}/sync-to-nebula", response_model=APIResponse)
async def sync_entity_to_nebula(
    entity_id: int,
    db: AsyncSession = Depends(get_db)
):
    """同步单个实体到Nebula Graph"""
    from app.sync_service import EntitySyncService
    from app.nebula_client import nebula_client
    
    try:
        sync_service = EntitySyncService(db, nebula_client)
        success = await sync_service.sync_entity_to_nebula(entity_id)
        
        if success:
            return APIResponse(message="同步成功")
        else:
            raise HTTPException(status_code=500, detail="同步失败")
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"同步失败: {str(e)}"
        )


@router.post("/sync-all-to-nebula", response_model=APIResponse)
async def sync_all_to_nebula(
    db: AsyncSession = Depends(get_db)
):
    """同步所有未同步的实体和关系到Nebula"""
    from app.sync_service import EntitySyncService
    from app.nebula_client import nebula_client
    from sqlalchemy import select
    from app.database import ExtractedEntity, ExtractedRelation
    
    try:
        sync_service = EntitySyncService(db, nebula_client)
        
        # 获取未同步的实体
        result = await db.execute(
            select(ExtractedEntity).where(ExtractedEntity.synced_to_nebula == False)
        )
        entities = result.scalars().all()
        
        # 获取未同步的关系
        result = await db.execute(
            select(ExtractedRelation).where(ExtractedRelation.synced_to_nebula == False)
        )
        relations = result.scalars().all()
        
        # 同步实体
        entity_success = 0
        for entity in entities:
            if await sync_service.sync_entity_to_nebula(entity.id):
                entity_success += 1
        
        # 同步关系
        relation_success = 0
        for relation in relations:
            if await sync_service.sync_relation_to_nebula(relation.id):
                relation_success += 1
        
        return APIResponse(
            message="批量同步完成",
            data={
                "entity_total": len(entities),
                "entity_success": entity_success,
                "relation_total": len(relations),
                "relation_success": relation_success
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量同步失败: {str(e)}"
        )