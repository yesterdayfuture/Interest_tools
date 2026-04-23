"""
RAG检索路由模块

本模块提供基于RAG(Retrieval-Augmented Generation)的文档检索和问答API接口。
支持多路召回、重排序、父子文档索引等高级检索功能。

功能列表：
- POST /rag/query: RAG查询 - 多路召回检索
- POST /rag/chat: 智能问答 - 结合检索和生成
- POST /rag/index: 为文件建立RAG索引
- DELETE /rag/index/{file_id}: 删除文件的RAG索引
- POST /rag/qa-pairs: 添加QA问答对
- GET /rag/stats: 获取RAG统计信息

检索技术：
1. 向量检索：基于语义相似度
2. BM25检索：基于关键词匹配
3. QA匹配：基于问答对匹配
4. 多路召回融合：综合多种检索结果
5. 重排序：对结果进行精排
6. 父子文档：支持长文档的层级检索

使用场景：
- 智能客服问答
- 文档知识库检索
- 内容推荐
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.database import get_db
from app.schemas import (
    RAGQueryRequest, RAGQueryResponse,
    APIResponse
)
from app.rag_service import RAGService
from app.extraction_service import ChatService

# 创建API路由实例
router = APIRouter(prefix="/rag", tags=["RAG检索"])


@router.post("/query", response_model=APIResponse)
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """RAG查询 - 多路召回检索"""
    try:
        rag_service = RAGService()
        
        results = rag_service.query(
            query_text=request.query,
            top_k=request.top_k,
            use_multi_reciprocal=request.use_multi_reciprocal,
            use_rerank=request.use_rerank,
            use_parent_child=True,
            filters=request.filters
        )
        
        return APIResponse(
            message=f"检索完成，共找到 {results['total_results']} 个相关文档",
            data=results
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"检索失败: {str(e)}"
        )


@router.post("/chat", response_model=APIResponse)
async def rag_chat(
    query: str,
    use_rag: bool = True,
    use_kg: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """客服对话 - 结合RAG和知识图谱"""
    try:
        chat_service = ChatService(db)
        result = await chat_service.chat(
            query=query,
            use_rag=use_rag,
            use_kg=use_kg
        )
        
        if result["success"]:
            return APIResponse(
                message="对话成功",
                data=result
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "对话失败")
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"对话失败: {str(e)}"
        )


@router.post("/add-qa", response_model=APIResponse)
async def add_qa_pair(
    question: str,
    answer: str
):
    """添加QA对到缓存"""
    try:
        rag_service = RAGService()
        rag_service.add_qa_pair(question, answer)
        
        return APIResponse(message="QA对添加成功")
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"添加失败: {str(e)}"
        )


@router.post("/tokenize", response_model=APIResponse)
async def dfs_tokenize(
    text: str
):
    """使用DFS算法进行分词"""
    try:
        rag_service = RAGService()
        tokens = rag_service.dfs_tokenize(text)
        
        return APIResponse(
            message=f"分词完成，共 {len(tokens)} 个词",
            data={
                "text": text,
                "tokens": tokens
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"分词失败: {str(e)}"
        )


@router.get("/stats", response_model=APIResponse)
async def get_rag_stats():
    """获取RAG系统统计信息"""
    try:
        rag_service = RAGService()
        
        # 获取ChromaDB统计
        collection_stats = rag_service.collection.count()
        
        return APIResponse(
            data={
                "document_count": collection_stats,
                "qa_cache_size": len(rag_service.qa_cache),
                "bm25_corpus_size": len(rag_service.corpus)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计失败: {str(e)}"
        )