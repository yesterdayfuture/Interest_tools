"""
文件管理路由模块

本模块提供文件上传、下载、管理和处理的RESTful API接口。
支持多种文件格式，并与RAG检索系统集成。

功能列表：
- POST /files/upload: 文件上传（支持多个文件）
- GET /files: 获取文件列表（支持分页、筛选）
- GET /files/{id}: 获取单个文件详情
- GET /files/{id}/download: 下载文件
- DELETE /files/{id}: 删除文件
- POST /files/{id}/process: 处理文件（提取文本、建立索引）
- GET /files/{id}/content: 获取文件内容

文件处理流程：
1. 上传文件到指定目录
2. 生成唯一文件名防止冲突
3. 记录文件元数据到数据库
4. 提取文件文本内容
5. 可选：建立RAG索引
6. 可选：提取实体和关系

支持格式：
- 文档：.txt, .pdf, .doc, .docx, .md
- 表格：.xls, .xlsx, .csv
- 演示：.ppt, .pptx
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os
import shutil
import uuid
from pathlib import Path
import aiofiles

from app.database import get_db, FileType, FileStatus
from app.schemas import (
    FileRecordResponse, FileListResponse, 
    APIResponse, RAGIndexRequest
)
from app.crud import FileCRUD
from app.config import settings

# 创建API路由实例
router = APIRouter(prefix="/files", tags=["文件管理"])


def get_file_type(extension: str) -> FileType:
    """根据扩展名获取文件类型"""
    document_exts = ['.txt', '.pdf', '.doc', '.docx', '.md', '.rtf']
    spreadsheet_exts = ['.xls', '.xlsx', '.csv']
    presentation_exts = ['.ppt', '.pptx']
    
    ext_lower = extension.lower()
    if ext_lower in document_exts:
        return FileType.DOCUMENT
    elif ext_lower in spreadsheet_exts:
        return FileType.SPREADSHEET
    elif ext_lower in presentation_exts:
        return FileType.PRESENTATION
    else:
        return FileType.OTHER


def get_mime_type(extension: str) -> str:
    """根据扩展名获取MIME类型"""
    mime_types = {
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.csv': 'text/csv',
        '.md': 'text/markdown',
    }
    return mime_types.get(extension.lower(), 'application/octet-stream')


@router.post("/upload", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传文件"""
    # 检查文件扩展名
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_extension}"
        )
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # 保存文件
    try:
        async with aiofiles.open(file_path, 'wb') as buffer:
            content = await file.read()
            await buffer.write(content)
            file_size = len(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 创建数据库记录
    db_obj = await FileCRUD.create(
        db,
        filename=unique_filename,
        original_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=get_file_type(file_extension),
        mime_type=get_mime_type(file_extension),
        file_extension=file_extension,
        status=FileStatus.UPLOADED
    )
    
    return APIResponse(
        message="上传成功",
        data=FileRecordResponse.model_validate(db_obj)
    )


@router.get("", response_model=APIResponse)
async def list_files(
    status: Optional[FileStatus] = None,
    file_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取文件列表"""
    skip = (page - 1) * page_size
    
    items = await FileCRUD.get_multi(
        db, skip=skip, limit=page_size,
        status=status,
        file_type=file_type
    )
    
    total = await FileCRUD.count(db, status=status)
    
    return APIResponse(
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [FileRecordResponse.model_validate(item) for item in items]
        }
    )


@router.get("/{file_id}", response_model=APIResponse)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取文件详情"""
    db_obj = await FileCRUD.get_by_id(db, file_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return APIResponse(
        data=FileRecordResponse.model_validate(db_obj)
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """下载文件"""
    db_obj = await FileCRUD.get_by_id(db, file_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not os.path.exists(db_obj.file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")
    
    return FileResponse(
        path=db_obj.file_path,
        filename=db_obj.original_name,
        media_type=db_obj.mime_type or 'application/octet-stream'
    )


@router.delete("/{file_id}", response_model=APIResponse)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除文件"""
    db_obj = await FileCRUD.get_by_id(db, file_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 删除物理文件
    if os.path.exists(db_obj.file_path):
        try:
            os.remove(db_obj.file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")
    
    # 删除数据库记录
    success = await FileCRUD.delete(db, file_id)
    
    if success:
        return APIResponse(message="删除成功")
    else:
        raise HTTPException(status_code=500, detail="删除失败")


@router.post("/{file_id}/process", response_model=APIResponse)
async def process_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """处理文件（提取文本内容）"""
    from app.file_processor import FileProcessor
    
    db_obj = await FileCRUD.get_by_id(db, file_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 更新状态为处理中
    await FileCRUD.update_status(db, file_id, FileStatus.PROCESSING)
    
    try:
        # 处理文件
        processor = FileProcessor()
        content_summary = await processor.process(db_obj.file_path, db_obj.file_extension)
        
        # 更新状态为已处理
        await FileCRUD.update_status(db, file_id, FileStatus.PROCESSED)
        
        # 更新内容摘要
        db_obj.content_summary = content_summary[:1000] if content_summary else None  # 限制长度
        await db.commit()
        
        return APIResponse(
            message="处理成功",
            data={"content_summary": content_summary[:500] if content_summary else None}
        )
        
    except Exception as e:
        await FileCRUD.update_status(db, file_id, FileStatus.FAILED, str(e))
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


@router.post("/{file_id}/index-rag", response_model=APIResponse)
async def index_file_rag(
    file_id: int,
    index_request: RAGIndexRequest,
    db: AsyncSession = Depends(get_db)
):
    """将文件加入RAG索引"""
    from app.rag_service import RAGService
    
    db_obj = await FileCRUD.get_by_id(db, file_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not db_obj.content_summary and db_obj.status != FileStatus.PROCESSED:
        raise HTTPException(status_code=400, detail="文件尚未处理，请先调用处理接口")
    
    try:
        rag_service = RAGService()
        doc_ids = await rag_service.index_file(
            file_id=file_id,
            file_path=db_obj.file_path,
            file_extension=db_obj.file_extension,
            metadata={
                "file_id": file_id,
                "filename": db_obj.original_name,
                "file_type": db_obj.file_type.value
            },
            chunk_size=index_request.chunk_size,
            chunk_overlap=index_request.chunk_overlap,
            use_parent_child=index_request.use_parent_child
        )
        
        # 更新RAG状态
        await FileCRUD.update_rag_status(db, file_id, True, doc_ids)
        
        return APIResponse(
            message="索引成功",
            data={"document_ids": doc_ids, "count": len(doc_ids)}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引失败: {str(e)}")