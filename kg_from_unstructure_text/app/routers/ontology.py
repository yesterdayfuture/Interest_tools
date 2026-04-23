"""
本体管理路由模块

本模块提供本体定义的RESTful API接口，支持对本体（实体、关系、属性）的增删改查操作。
本体支持树状结构，可进行合并操作，并支持与Nebula Graph的同步。

功能列表：
- POST /ontology/definitions: 创建本体定义
- GET /ontology/definitions: 获取本体定义列表
- GET /ontology/definitions/tree: 获取本体树结构
- GET /ontology/definitions/{id}: 获取单个本体详情
- PUT /ontology/definitions/{id}: 更新本体定义
- DELETE /ontology/definitions/{id}: 删除本体定义
- POST /ontology/definitions/{id}/merge: 合并本体

- POST /ontology/relations: 创建关系定义
- GET /ontology/relations: 获取关系列表
- GET /ontology/relations/{id}: 获取关系详情
- PUT /ontology/relations/{id}: 更新关系
- DELETE /ontology/relations/{id}: 删除关系

- POST /ontology/sync: 同步到Nebula Graph
- GET /ontology/sync/status: 获取同步状态

树状结构支持：
- 通过parent_id建立父子关系
- 自动计算level和path字段
- 支持获取完整树结构
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db, OntologyType, OntologyStatus
from app.schemas import (
    OntologyDefinitionCreate, OntologyDefinitionUpdate, OntologyDefinitionResponse,
    OntologyDefinitionTree, OntologyMergeRequest,
    OntologyRelationCreate, OntologyRelationUpdate, OntologyRelationResponse,
    APIResponse, ErrorResponse, SyncRequest, SyncResponse
)
from app.crud import OntologyCRUD, OntologyRelationCRUD
from app.nebula_client import nebula_client

# 创建API路由实例
router = APIRouter(prefix="/ontology", tags=["本体管理"])


# ==================== 本体定义API ====================

@router.post("/definitions", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_ontology_definition(
    obj_in: OntologyDefinitionCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建本体定义"""
    # 检查名称是否已存在
    existing = await OntologyCRUD.get_by_name(
        db, obj_in.name, obj_in.ontology_type
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"本体定义 '{obj_in.name}' 已存在"
        )
    
    # 检查父节点是否存在
    if obj_in.parent_id:
        parent = await OntologyCRUD.get_by_id(db, obj_in.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="父节点不存在")
    
    db_obj = await OntologyCRUD.create(db, obj_in)
    
    return APIResponse(
        message="创建成功",
        data=OntologyDefinitionResponse.model_validate(db_obj)
    )


@router.get("/definitions", response_model=APIResponse)
async def list_ontology_definitions(
    ontology_type: Optional[OntologyType] = None,
    parent_id: Optional[int] = None,
    status: Optional[OntologyStatus] = OntologyStatus.ACTIVE,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取本体定义列表"""
    items = await OntologyCRUD.get_multi(
        db, skip=skip, limit=limit,
        ontology_type=ontology_type,
        parent_id=parent_id,
        status=status
    )
    
    return APIResponse(
        data={
            "total": len(items),
            "items": [OntologyDefinitionResponse.model_validate(item) for item in items]
        }
    )


@router.get("/definitions/tree", response_model=APIResponse)
async def get_ontology_tree(
    ontology_type: Optional[OntologyType] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取本体定义树状结构"""
    trees = await OntologyCRUD.get_tree(db, ontology_type=ontology_type)
    
    def build_tree_response(node):
        response = OntologyDefinitionTree.model_validate(node)
        if node.children:
            response.children = [build_tree_response(child) for child in node.children if child]
        return response
    
    return APIResponse(
        data=[build_tree_response(tree) for tree in trees]
    )


@router.get("/definitions/{definition_id}", response_model=APIResponse)
async def get_ontology_definition(
    definition_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取单个本体定义详情"""
    db_obj = await OntologyCRUD.get_by_id(db, definition_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="本体定义不存在")
    
    return APIResponse(
        data=OntologyDefinitionResponse.model_validate(db_obj)
    )


@router.put("/definitions/{definition_id}", response_model=APIResponse)
async def update_ontology_definition(
    definition_id: int,
    obj_in: OntologyDefinitionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新本体定义"""
    db_obj = await OntologyCRUD.get_by_id(db, definition_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="本体定义不存在")
    
    updated = await OntologyCRUD.update(db, db_obj, obj_in)
    
    # TODO: 如果已同步到Nebula，需要同步更新Nebula中的定义
    
    return APIResponse(
        message="更新成功",
        data=OntologyDefinitionResponse.model_validate(updated)
    )


@router.delete("/definitions/{definition_id}", response_model=APIResponse)
async def delete_ontology_definition(
    definition_id: int,
    hard: bool = Query(False, description="是否硬删除"),
    db: AsyncSession = Depends(get_db)
):
    """删除本体定义"""
    db_obj = await OntologyCRUD.get_by_id(db, definition_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="本体定义不存在")
    
    # 检查是否有子节点
    if db_obj.children and not hard:
        raise HTTPException(
            status_code=400,
            detail="该本体定义包含子节点，无法删除"
        )
    
    if hard:
        success = await OntologyCRUD.hard_delete(db, definition_id)
    else:
        success = await OntologyCRUD.delete(db, definition_id)
    
    if success:
        return APIResponse(message="删除成功")
    else:
        raise HTTPException(status_code=500, detail="删除失败")


@router.post("/definitions/merge", response_model=APIResponse)
async def merge_ontology_definitions(
    merge_request: OntologyMergeRequest,
    db: AsyncSession = Depends(get_db)
):
    """合并本体定义"""
    # 检查目标本体是否存在
    target = await OntologyCRUD.get_by_id(db, merge_request.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="目标本体不存在")
    
    # 检查源本体是否都存在
    for source_id in merge_request.source_ids:
        source = await OntologyCRUD.get_by_id(db, source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"源本体 {source_id} 不存在")
    
    merged = await OntologyCRUD.merge(db, merge_request)
    
    return APIResponse(
        message="合并成功",
        data=OntologyDefinitionResponse.model_validate(merged)
    )


# ==================== 本体关系API ====================

@router.post("/relations", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_ontology_relation(
    obj_in: OntologyRelationCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建本体关系定义"""
    # 检查源和目标类型是否存在
    source = await OntologyCRUD.get_by_id(db, obj_in.source_type_id)
    target = await OntologyCRUD.get_by_id(db, obj_in.target_type_id)
    
    if not source:
        raise HTTPException(status_code=404, detail="源实体类型不存在")
    if not target:
        raise HTTPException(status_code=404, detail="目标实体类型不存在")
    
    db_obj = await OntologyRelationCRUD.create(db, obj_in)
    
    return APIResponse(
        message="创建成功",
        data=OntologyRelationResponse.model_validate(db_obj)
    )


@router.get("/relations", response_model=APIResponse)
async def list_ontology_relations(
    source_type_id: Optional[int] = None,
    target_type_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取本体关系列表"""
    items = await OntologyRelationCRUD.get_multi(
        db, skip=skip, limit=limit,
        source_type_id=source_type_id,
        target_type_id=target_type_id
    )
    
    return APIResponse(
        data={
            "total": len(items),
            "items": [OntologyRelationResponse.model_validate(item) for item in items]
        }
    )


@router.get("/relations/{relation_id}", response_model=APIResponse)
async def get_ontology_relation(
    relation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取单个本体关系详情"""
    db_obj = await OntologyRelationCRUD.get_by_id(db, relation_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="本体关系不存在")
    
    return APIResponse(
        data=OntologyRelationResponse.model_validate(db_obj)
    )


@router.put("/relations/{relation_id}", response_model=APIResponse)
async def update_ontology_relation(
    relation_id: int,
    obj_in: OntologyRelationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新本体关系"""
    db_obj = await OntologyRelationCRUD.get_by_id(db, relation_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="本体关系不存在")
    
    updated = await OntologyRelationCRUD.update(db, db_obj, obj_in)
    
    return APIResponse(
        message="更新成功",
        data=OntologyRelationResponse.model_validate(updated)
    )


@router.delete("/relations/{relation_id}", response_model=APIResponse)
async def delete_ontology_relation(
    relation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除本体关系"""
    success = await OntologyRelationCRUD.delete(db, relation_id)
    
    if success:
        return APIResponse(message="删除成功")
    else:
        raise HTTPException(status_code=404, detail="本体关系不存在")


# ==================== 同步API ====================

@router.post("/sync-to-nebula", response_model=APIResponse)
async def sync_to_nebula(
    sync_request: SyncRequest,
    db: AsyncSession = Depends(get_db)
):
    """同步本体定义到Nebula Graph"""
    from app.sync_service import OntologySyncService
    
    sync_service = OntologySyncService(db, nebula_client)
    result = await sync_service.sync_ontology_to_nebula(sync_request)
    
    return APIResponse(
        message=result["message"],
        data=result
    )