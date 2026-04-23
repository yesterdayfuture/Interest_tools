"""
属性类型管理路由模块

本模块提供属性类型的RESTful API接口，支持对可复用属性类型的增删改查操作。

功能列表：
- POST /property-types: 创建属性类型
- GET /property-types: 获取属性类型列表（支持分页、筛选）
- GET /property-types/{id}: 获取单个属性类型详情
- PUT /property-types/{id}: 更新属性类型
- DELETE /property-types/{id}: 删除属性类型（软删除）
- GET /property-types/{id}/usage: 查看属性类型使用情况
- POST /property-types/init-defaults: 初始化默认属性类型

属性类型用于定义本体属性的数据类型、验证规则等，支持多种数据类型：
string, integer, float, boolean, datetime, enum, text等
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db, PropertyTypeStatus
from app.schemas import (
    PropertyTypeCreate, PropertyTypeUpdate, PropertyTypeResponse,
    PropertyTypeListResponse, APIResponse
)
from app.crud import PropertyTypeCRUD

# 创建API路由实例
# prefix: 路由前缀，所有端点会自动添加此前缀
# tags: API文档中的分组标签
router = APIRouter(prefix="/property-types", tags=["属性类型管理"])


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_property_type(
    obj_in: PropertyTypeCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建属性类型"""
    # 检查名称是否已存在
    existing = await PropertyTypeCRUD.get_by_name(db, obj_in.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"属性类型 '{obj_in.name}' 已存在"
        )
    
    # 创建属性类型
    db_obj = await PropertyTypeCRUD.create(
        db,
        name=obj_in.name,
        display_name=obj_in.display_name,
        description=obj_in.description,
        data_type=obj_in.data_type,
        default_value=obj_in.default_value,
        enum_values=obj_in.enum_values,
        validation_rules=obj_in.validation_rules,
        required=obj_in.required,
        unique=obj_in.unique,
        indexable=obj_in.indexable,
        status=PropertyTypeStatus.ACTIVE
    )
    
    # 获取使用次数
    usage_count = await PropertyTypeCRUD.get_usage_count(db, db_obj.id)
    
    response_data = PropertyTypeResponse.model_validate(db_obj)
    response_data.usage_count = usage_count
    
    return APIResponse(
        message="创建成功",
        data=response_data
    )


@router.get("", response_model=APIResponse)
async def list_property_types(
    status: Optional[str] = None,
    data_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取属性类型列表"""
    skip = (page - 1) * page_size
    
    items = await PropertyTypeCRUD.get_multi(
        db,
        skip=skip,
        limit=page_size,
        status=status,
        data_type=data_type
    )
    
    total = await PropertyTypeCRUD.count(db, status=status, data_type=data_type)
    
    # 获取使用次数
    response_items = []
    for item in items:
        response_item = PropertyTypeResponse.model_validate(item)
        response_item.usage_count = await PropertyTypeCRUD.get_usage_count(db, item.id)
        response_items.append(response_item)
    
    return APIResponse(
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": response_items
        }
    )


@router.get("/{property_type_id}", response_model=APIResponse)
async def get_property_type(
    property_type_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取单个属性类型详情"""
    db_obj = await PropertyTypeCRUD.get_by_id(db, property_type_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="属性类型不存在")
    
    # 获取使用次数
    usage_count = await PropertyTypeCRUD.get_usage_count(db, db_obj.id)
    
    response_data = PropertyTypeResponse.model_validate(db_obj)
    response_data.usage_count = usage_count
    
    return APIResponse(
        data=response_data
    )


@router.put("/{property_type_id}", response_model=APIResponse)
async def update_property_type(
    property_type_id: int,
    obj_in: PropertyTypeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新属性类型"""
    db_obj = await PropertyTypeCRUD.get_by_id(db, property_type_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="属性类型不存在")
    
    # 检查是否为系统预定义类型
    if db_obj.is_system:
        raise HTTPException(
            status_code=400,
            detail="系统预定义的属性类型不能修改"
        )
    
    # 更新数据
    update_data = obj_in.model_dump(exclude_unset=True)
    updated = await PropertyTypeCRUD.update(db, db_obj, **update_data)
    
    # 获取使用次数
    usage_count = await PropertyTypeCRUD.get_usage_count(db, updated.id)
    
    response_data = PropertyTypeResponse.model_validate(updated)
    response_data.usage_count = usage_count
    
    return APIResponse(
        message="更新成功",
        data=response_data
    )


@router.delete("/{property_type_id}", response_model=APIResponse)
async def delete_property_type(
    property_type_id: int,
    hard: bool = Query(False, description="是否硬删除"),
    db: AsyncSession = Depends(get_db)
):
    """删除属性类型"""
    db_obj = await PropertyTypeCRUD.get_by_id(db, property_type_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="属性类型不存在")
    
    # 检查是否为系统预定义类型
    if db_obj.is_system:
        raise HTTPException(
            status_code=400,
            detail="系统预定义的属性类型不能删除"
        )
    
    # 检查是否有本体在使用该属性类型
    usage_count = await PropertyTypeCRUD.get_usage_count(db, property_type_id)
    if usage_count > 0 and hard:
        raise HTTPException(
            status_code=400,
            detail=f"该属性类型正被 {usage_count} 个本体使用，无法硬删除"
        )
    
    if hard:
        success = await PropertyTypeCRUD.hard_delete(db, property_type_id)
    else:
        success = await PropertyTypeCRUD.delete(db, property_type_id)
    
    if success:
        return APIResponse(message="删除成功")
    else:
        raise HTTPException(status_code=500, detail="删除失败")


@router.get("/{property_type_id}/usage", response_model=APIResponse)
async def get_property_type_usage(
    property_type_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取属性类型的使用情况"""
    db_obj = await PropertyTypeCRUD.get_by_id(db, property_type_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="属性类型不存在")
    
    # 获取使用次数
    usage_count = await PropertyTypeCRUD.get_usage_count(db, property_type_id)
    
    # 获取使用该属性类型的本体属性列表
    from sqlalchemy import select
    from app.database import OntologyProperty, OntologyDefinition
    from sqlalchemy.orm import joinedload
    
    result = await db.execute(
        select(OntologyProperty)
        .options(joinedload(OntologyProperty.ontology))
        .where(OntologyProperty.property_type_id == property_type_id)
    )
    ontology_properties = result.scalars().all()
    
    usage_list = []
    for prop in ontology_properties:
        if prop.ontology:
            usage_list.append({
                "ontology_id": prop.ontology_id,
                "ontology_name": prop.ontology.name,
                "ontology_display_name": prop.ontology.display_name,
                "property_name": prop.name,
                "property_display_name": prop.display_name
            })
    
    return APIResponse(
        data={
            "property_type_id": property_type_id,
            "property_type_name": db_obj.name,
            "usage_count": usage_count,
            "used_by": usage_list
        }
    )


@router.post("/init-defaults", response_model=APIResponse)
async def init_default_property_types(
    db: AsyncSession = Depends(get_db)
):
    """初始化默认属性类型"""
    default_types = [
        {
            "name": "string",
            "display_name": "字符串",
            "description": "文本字符串类型",
            "data_type": "string",
            "required": False,
            "unique": False,
            "indexable": True,
            "is_system": True
        },
        {
            "name": "integer",
            "display_name": "整数",
            "description": "整数类型",
            "data_type": "integer",
            "required": False,
            "unique": False,
            "indexable": True,
            "is_system": True
        },
        {
            "name": "float",
            "display_name": "浮点数",
            "description": "浮点数类型",
            "data_type": "float",
            "required": False,
            "unique": False,
            "indexable": True,
            "is_system": True
        },
        {
            "name": "boolean",
            "display_name": "布尔值",
            "description": "布尔值类型（是/否）",
            "data_type": "boolean",
            "required": False,
            "unique": False,
            "indexable": False,
            "is_system": True
        },
        {
            "name": "datetime",
            "display_name": "日期时间",
            "description": "日期时间类型",
            "data_type": "datetime",
            "required": False,
            "unique": False,
            "indexable": True,
            "is_system": True
        },
        {
            "name": "text",
            "display_name": "长文本",
            "description": "长文本类型，适用于大段文字",
            "data_type": "text",
            "required": False,
            "unique": False,
            "indexable": False,
            "is_system": True
        },
        {
            "name": "enum",
            "display_name": "枚举",
            "description": "枚举类型，从预定义选项中选择",
            "data_type": "enum",
            "required": False,
            "unique": False,
            "indexable": True,
            "is_system": True
        },
        {
            "name": "url",
            "display_name": "URL链接",
            "description": "URL链接类型",
            "data_type": "string",
            "required": False,
            "unique": False,
            "indexable": False,
            "is_system": True,
            "validation_rules": {"format": "url"}
        },
        {
            "name": "email",
            "display_name": "邮箱",
            "description": "电子邮箱类型",
            "data_type": "string",
            "required": False,
            "unique": True,
            "indexable": True,
            "is_system": True,
            "validation_rules": {"format": "email"}
        },
        {
            "name": "phone",
            "display_name": "电话",
            "description": "电话号码类型",
            "data_type": "string",
            "required": False,
            "unique": False,
            "indexable": True,
            "is_system": True,
            "validation_rules": {"format": "phone"}
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for type_data in default_types:
        # 检查是否已存在
        existing = await PropertyTypeCRUD.get_by_name(db, type_data["name"])
        if existing:
            skipped_count += 1
            continue
        
        # 创建属性类型
        await PropertyTypeCRUD.create(
            db,
            name=type_data["name"],
            display_name=type_data["display_name"],
            description=type_data.get("description"),
            data_type=type_data["data_type"],
            required=type_data.get("required", False),
            unique=type_data.get("unique", False),
            indexable=type_data.get("indexable", False),
            is_system=type_data.get("is_system", False),
            validation_rules=type_data.get("validation_rules"),
            status=PropertyTypeStatus.ACTIVE
        )
        created_count += 1
    
    return APIResponse(
        message="初始化完成",
        data={
            "created": created_count,
            "skipped": skipped_count,
            "total": len(default_types)
        }
    )
