"""
实体提取服务模块

本模块使用大语言模型（OpenAI API）从文本中自动提取实体和关系，
并将提取结果保存到数据库和Nebula Graph图数据库。

主要功能：
1. 实体提取：从文本中识别并提取符合本体定义的实体
2. 关系提取：识别实体之间的关系
3. 属性填充：为实体填充属性值
4. 结果验证：验证提取结果是否符合本体定义
5. 数据持久化：保存到SQLite和Nebula Graph

处理流程：
1. 加载本体定义作为提取模板
2. 构建Prompt，包含本体结构和示例
3. 调用大模型进行提取
4. 解析和验证模型输出
5. 保存实体和关系到数据库
6. 同步到Nebula Graph

依赖：
- OpenAI API: 大语言模型调用
- SQLAlchemy: 异步数据库操作
- NebulaClient: 图数据库同步
"""

from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import re

from app.config import settings
from app.database import OntologyType
from app.crud import OntologyCRUD, ExtractedEntityCRUD, ExtractedRelationCRUD
from app.sync_service import EntitySyncService
from app.nebula_client import nebula_client

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EntityExtractionService:
    """
    实体提取服务类
    
    封装了使用大模型从文本中提取实体和关系的完整流程。
    支持批量处理和单个文本处理。
    
    Attributes:
        db: 数据库会话
        client: OpenAI异步客户端
        model: 使用的模型名称
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL
    
    async def extract_from_text(
        self,
        text: str,
        file_id: Optional[int] = None,
        ontology_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        从文本中提取实体和关系
        
        Args:
            text: 输入文本
            file_id: 关联的文件ID
            ontology_ids: 指定的本体类型ID列表，为空则使用所有
        """
        # 获取本体定义
        if ontology_ids:
            ontologies = []
            for oid in ontology_ids:
                ont = await OntologyCRUD.get_by_id(self.db, oid)
                if ont:
                    ontologies.append(ont)
        else:
            ontologies = await OntologyCRUD.get_multi(
                self.db, ontology_type=OntologyType.ENTITY
            )
        
        # 获取关系定义
        relations = await self.db.execute(
            "SELECT * FROM ontology_relations WHERE status = 'active'"
        )
        
        # 构建提示词
        prompt = self._build_extraction_prompt(text, ontologies, relations)
        
        try:
            # 调用大模型
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的信息抽取助手，擅长从电商客服对话中提取实体和关系。请严格按照JSON格式输出结果。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # 解析结果
            result_text = response.choices[0].message.content
            extraction_result = json.loads(result_text)
            
            # 保存到数据库
            saved_entities, saved_relations = await self._save_extraction_results(
                extraction_result, file_id, text
            )
            
            # 同步到Nebula
            sync_service = EntitySyncService(self.db, nebula_client)
            for entity in saved_entities:
                await sync_service.sync_entity_to_nebula(entity.id)
            
            for relation in saved_relations:
                await sync_service.sync_relation_to_nebula(relation.id)
            
            return {
                "success": True,
                "entities": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "ontology_id": e.ontology_id,
                        "properties": e.properties,
                        "confidence": e.confidence
                    }
                    for e in saved_entities
                ],
                "relations": [
                    {
                        "id": r.id,
                        "source_entity_id": r.source_entity_id,
                        "target_entity_id": r.target_entity_id,
                        "relation_id": r.relation_id,
                        "confidence": r.confidence
                    }
                    for r in saved_relations
                ]
            }
            
        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "entities": [],
                "relations": []
            }
    
    def _build_extraction_prompt(
        self,
        text: str,
        ontologies: List[Any],
        relations: Any
    ) -> str:
        """构建提取提示词"""
        # 构建本体定义描述
        ontology_desc = []
        for ont in ontologies:
            props_desc = []
            if ont.properties:
                for prop_name, prop_def in ont.properties.items():
                    if isinstance(prop_def, dict):
                        desc = f"{prop_name}({prop_def.get('data_type', 'string')})"
                    else:
                        desc = f"{prop_name}(string)"
                    props_desc.append(desc)
            
            ontology_desc.append(
                f"- {ont.name}: {ont.description or '无描述'}\n"
                f"  属性: {', '.join(props_desc) if props_desc else '无'}"
            )
        
        # 构建关系定义描述
        relation_desc = []
        if relations:
            for rel in relations:
                relation_desc.append(
                    f"- {rel.name}: {rel.description or '无描述'}\n"
                    f"  从 [{rel.source_type.name}] 到 [{rel.target_type.name}]"
                )
        
        prompt = f"""请从以下电商客服对话文本中提取实体和关系。

## 文本内容
{text}

## 可提取的实体类型
{chr(10).join(ontology_desc) if ontology_desc else "无特定限制，请提取关键实体"}

## 可提取的关系类型
{chr(10).join(relation_desc) if relation_desc else "请根据语义自动识别关系"}

## 输出格式要求
请严格按照以下JSON格式输出：
{{
    "entities": [
        {{
            "name": "实体名称",
            "ontology_name": "对应的本体类型名称",
            "properties": {{
                "属性名": "属性值"
            }},
            "source_text": "原始文本片段"
        }}
    ],
    "relations": [
        {{
            "source_entity_name": "源实体名称",
            "target_entity_name": "目标实体名称",
            "relation_name": "关系类型名称",
            "properties": {{}}
        }}
    ]
}}

注意事项：
1. 只输出JSON，不要包含其他内容
2. 如果无法确定某个字段，使用null
3. 实体名称应该在原文中有明确提及
4. 关系必须在实体列表中存在对应的实体
"""
        return prompt
    
    async def _save_extraction_results(
        self,
        extraction_result: Dict[str, Any],
        file_id: Optional[int],
        source_text: str
    ) -> tuple:
        """保存提取结果到数据库"""
        saved_entities = []
        entity_name_to_id = {}  # 用于建立关系映射
        
        # 保存实体
        entities_data = extraction_result.get("entities", [])
        for entity_data in entities_data:
            try:
                # 查找对应的本体定义
                ontology = await OntologyCRUD.get_by_name(
                    self.db, entity_data.get("ontology_name", ""), OntologyType.ENTITY
                )
                
                if not ontology:
                    # 使用通用实体类型或创建新类型
                    logger.warning(f"未找到本体定义: {entity_data.get('ontology_name')}")
                    continue
                
                # 创建实体记录
                entity = await ExtractedEntityCRUD.create(
                    self.db,
                    name=entity_data["name"],
                    ontology_id=ontology.id,
                    file_id=file_id,
                    properties=entity_data.get("properties", {}),
                    source_text=entity_data.get("source_text", ""),
                    source_location=self._find_location(source_text, entity_data.get("source_text", "")),
                    confidence="high",
                    extracted_by=self.model
                )
                
                saved_entities.append(entity)
                entity_name_to_id[entity_data["name"]] = entity.id
                
            except Exception as e:
                logger.error(f"保存实体失败: {e}")
        
        # 保存关系
        saved_relations = []
        relations_data = extraction_result.get("relations", [])
        
        for relation_data in relations_data:
            try:
                source_name = relation_data.get("source_entity_name")
                target_name = relation_data.get("target_entity_name")
                
                # 查找源实体和目标实体
                source_id = entity_name_to_id.get(source_name)
                target_id = entity_name_to_id.get(target_name)
                
                if not source_id or not target_id:
                    logger.warning(f"关系中的实体未找到: {source_name} -> {target_name}")
                    continue
                
                # 查找关系定义
                from app.crud import OntologyRelationCRUD
                relation_def = await OntologyRelationCRUD.get_multi(
                    self.db, limit=1
                )
                
                if relation_def:
                    relation_type_id = relation_def[0].id
                else:
                    continue
                
                # 创建关系记录
                relation = await ExtractedRelationCRUD.create(
                    self.db,
                    relation_id=relation_type_id,
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    file_id=file_id,
                    properties=relation_data.get("properties", {}),
                    source_text=relation_data.get("source_text", ""),
                    confidence="high",
                    extracted_by=self.model
                )
                
                saved_relations.append(relation)
                
            except Exception as e:
                logger.error(f"保存关系失败: {e}")
        
        return saved_entities, saved_relations
    
    def _find_location(self, full_text: str, snippet: str) -> Optional[str]:
        """查找片段在全文中的位置"""
        if not snippet:
            return None
        
        # 简单实现：返回行号和字符位置
        try:
            idx = full_text.find(snippet)
            if idx >= 0:
                line_num = full_text[:idx].count('\n') + 1
                char_pos = idx - full_text.rfind('\n', 0, idx) if '\n' in full_text[:idx] else idx
                return f"Line {line_num}, Char {char_pos}"
        except:
            pass
        
        return None
    
    async def batch_extract_from_texts(
        self,
        texts: List[str],
        file_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """批量提取多个文本"""
        results = []
        for text in texts:
            result = await self.extract_from_text(text, file_id)
            results.append(result)
        return results


class ChatService:
    """客服对话服务 - 结合RAG和知识图谱的客服对话"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL
    
    async def chat(
        self,
        query: str,
        use_rag: bool = True,
        use_kg: bool = True
    ) -> Dict[str, Any]:
        """
        客服对话
        
        Args:
            query: 用户查询
            use_rag: 是否使用RAG
            use_kg: 是否使用知识图谱
        """
        context_parts = []
        
        # RAG检索
        if use_rag:
            from app.rag_service import RAGService
            rag_service = RAGService()
            rag_results = rag_service.query(query, top_k=3)
            
            if rag_results.get("documents"):
                context_parts.append("## 相关文档：")
                for i, doc in enumerate(rag_results["documents"], 1):
                    context_parts.append(f"{i}. {doc['content'][:300]}...")
        
        # 知识图谱查询
        if use_kg:
            kg_context = await self._query_knowledge_graph(query)
            if kg_context:
                context_parts.append("## 相关知识：")
                context_parts.append(kg_context)
        
        # 构建提示词
        context = "\n".join(context_parts) if context_parts else "暂无相关背景知识"
        
        prompt = f"""你是一位专业的电商客服助手。请根据以下背景知识回答用户问题。

## 背景知识
{context}

## 用户问题
{query}

请给出专业、准确、有帮助的回答。如果背景知识不足以回答问题，请明确告知。"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的电商客服助手，擅长解答商品、订单、售后等问题。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            return {
                "success": True,
                "answer": answer,
                "context": context_parts,
                "sources": {
                    "rag": use_rag,
                    "kg": use_kg
                }
            }
            
        except Exception as e:
            logger.error(f"对话失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，服务暂时不可用，请稍后重试。"
            }
    
    async def _query_knowledge_graph(self, query: str) -> Optional[str]:
        """查询知识图谱获取相关信息"""
        try:
            # 提取查询关键词
            keywords = jieba.analyse.extract_tags(query, topK=5)
            
            if not keywords:
                return None
            
            # 在SQLite中查找相关实体
            from sqlalchemy import select, or_
            from app.database import ExtractedEntity
            
            conditions = [ExtractedEntity.name.contains(kw) for kw in keywords]
            result = await self.db.execute(
                select(ExtractedEntity).where(or_(*conditions)).limit(5)
            )
            entities = result.scalars().all()
            
            if not entities:
                return None
            
            # 构建知识描述
            kg_parts = []
            for entity in entities:
                kg_parts.append(f"- {entity.name}: {json.dumps(entity.properties, ensure_ascii=False)}")
            
            return "\n".join(kg_parts)
            
        except Exception as e:
            logger.error(f"知识图谱查询失败: {e}")
            return None