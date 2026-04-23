"""
RAG (Retrieval-Augmented Generation) 检索服务模块

本模块实现了基于多路召回的文档检索系统，支持以下功能：
1. 向量检索：基于语义相似度的向量召回
2. 关键词检索：基于BM25的关键词匹配
3. QA检索：基于问答对的匹配
4. Trie树分词：支持自定义词典的前缀匹配
5. 父子文档索引：支持长文档的层级切分

检索流程：
1. 文档切分：将长文档切分为合适的chunk
2. 向量化：将文本转换为向量表示
3. 索引构建：构建多种索引（向量、BM25、Trie树）
4. 多路召回：同时从多个索引中召回结果
5. 重排序：对召回结果进行融合和排序
6. 返回结果：返回最相关的文档片段

依赖：
- ChromaDB: 向量数据库存储
- SentenceTransformer: 文本向量化
- jieba: 中文分词
- rank_bm25: BM25算法实现
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
import jieba
import jieba.analyse
from rank_bm25 import BM25Okapi
import re
from collections import defaultdict
import hashlib
import json

from app.config import settings

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrieNode:
    """Trie树节点"""
    def __init__(self):
        self.children = {}
        self.is_end = False
        self.doc_ids = set()  # 包含该词的文档ID


class TrieTree:
    """Trie树 - 用于前缀匹配和分词"""
    
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, word: str, doc_id: str = None):
        """插入单词"""
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        if doc_id:
            node.doc_ids.add(doc_id)
    
    def search(self, word: str) -> bool:
        """搜索单词"""
        node = self.root
        for char in word:
            if char not in node.children:
                return False
            node = node.children[char]
        return node.is_end
    
    def starts_with(self, prefix: str) -> List[str]:
        """前缀搜索"""
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        
        # DFS收集所有完整单词
        results = []
        self._dfs(node, prefix, results)
        return results
    
    def _dfs(self, node: TrieNode, prefix: str, results: List[str]):
        """DFS遍历"""
        if node.is_end:
            results.append(prefix)
        for char, child in node.children.items():
            self._dfs(child, prefix + char, results)
    
    def tokenize_with_dfs(self, text: str) -> List[Tuple[str, int, int]]:
        """
        使用DFS算法进行分词
        返回: [(词, 起始位置, 结束位置), ...]
        """
        tokens = []
        i = 0
        n = len(text)
        
        while i < n:
            # 尝试最长匹配
            node = self.root
            longest_match = None
            j = i
            
            while j < n and text[j] in node.children:
                node = node.children[text[j]]
                j += 1
                if node.is_end:
                    longest_match = (text[i:j], i, j)
            
            if longest_match:
                tokens.append(longest_match)
                i = longest_match[2]
            else:
                # 没有匹配到，按单字切分
                tokens.append((text[i], i, i + 1))
                i += 1
        
        return tokens
    
    def get_doc_ids_for_word(self, word: str) -> set:
        """获取包含该词的所有文档ID"""
        node = self.root
        for char in word:
            if char not in node.children:
                return set()
            node = node.children[char]
        return node.doc_ids if node.is_end else set()


class ParentChildIndexer:
    """父子文档索引器"""
    
    def __init__(self):
        self.parent_docs = {}  # parent_id -> parent_content
        self.child_to_parent = {}  # child_id -> parent_id
        self.parent_children = defaultdict(list)  # parent_id -> [child_ids]
    
    def add_parent(self, parent_id: str, content: str, metadata: Dict):
        """添加父文档"""
        self.parent_docs[parent_id] = {
            "content": content,
            "metadata": metadata
        }
    
    def add_child(self, child_id: str, parent_id: str, content: str, metadata: Dict):
        """添加子文档"""
        self.child_to_parent[child_id] = parent_id
        self.parent_children[parent_id].append(child_id)
    
    def get_parent(self, child_id: str) -> Optional[Dict]:
        """获取子文档的父文档"""
        parent_id = self.child_to_parent.get(child_id)
        if parent_id:
            return self.parent_docs.get(parent_id)
        return None
    
    def get_children(self, parent_id: str) -> List[str]:
        """获取父文档的所有子文档"""
        return self.parent_children.get(parent_id, [])


class RAGService:
    """RAG服务 - 支持多路召回、双向匹配等高级功能"""
    
    def __init__(self):
        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 获取或创建集合
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        
        # 初始化嵌入模型
        self.embedding_model = None
        self.openai_client = None
        self._init_embedding_model()
        
        # 初始化BM25
        self.bm25 = None
        self.corpus = []
        self.corpus_ids = []
        
        # 初始化Trie树
        self.trie = TrieTree()
        
        # 初始化父子文档索引
        self.parent_child_indexer = ParentChildIndexer()
        
        # QA缓存
        self.qa_cache = {}
        
        logger.info("RAG服务初始化完成")
    
    def _init_embedding_model(self):
        """初始化嵌入模型 - 支持本地模型或OpenAI API"""
        # 检查是否配置了独立的嵌入API
        embedding_api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY
        embedding_base_url = settings.EMBEDDING_BASE_URL or settings.OPENAI_BASE_URL
        embedding_model = settings.EMBEDDING_MODEL_NAME or settings.EMBEDDING_MODEL
        
        if embedding_api_key and settings.EMBEDDING_API_KEY:
            # 使用独立的OpenAI API配置
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(
                    api_key=embedding_api_key,
                    base_url=embedding_base_url
                )
                self.embedding_model_name = embedding_model
                logger.info(f"使用OpenAI API嵌入模型: {embedding_model}")
            except Exception as e:
                logger.error(f"初始化OpenAI嵌入失败: {e}，将使用本地模型")
                self._init_local_embedding()
        else:
            # 使用本地模型
            self._init_local_embedding()
    
    def _init_local_embedding(self):
        """初始化本地嵌入模型"""
        try:
            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("使用本地SentenceTransformer嵌入模型")
        except Exception as e:
            logger.error(f"初始化本地嵌入模型失败: {e}")
            self.embedding_model = None
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的嵌入向量"""
        if self.openai_client:
            # 使用OpenAI API
            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model_name,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI嵌入失败: {e}，回退到本地模型")
                if self.embedding_model:
                    return self.embedding_model.encode(text).tolist()
                raise
        elif self.embedding_model:
            # 使用本地模型
            return self.embedding_model.encode(text).tolist()
        else:
            raise RuntimeError("没有可用的嵌入模型")
    
    def _chunk_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """文本分块"""
        chunks = []
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前段落超过chunk_size，需要进一步分割
            if len(para) > chunk_size:
                # 先保存当前积累的chunk
                if current_chunk:
                    chunks.append({
                        "content": current_chunk,
                        "index": chunk_index,
                        "type": "paragraph"
                    })
                    chunk_index += 1
                    current_chunk = ""
                
                # 按句子分割长段落
                sentences = re.split(r'([。！？.!?])', para)
                current_sentence_chunk = ""
                
                for i in range(0, len(sentences) - 1, 2):
                    sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                    
                    if len(current_sentence_chunk) + len(sentence) > chunk_size:
                        if current_sentence_chunk:
                            chunks.append({
                                "content": current_sentence_chunk,
                                "index": chunk_index,
                                "type": "sentence_group"
                            })
                            chunk_index += 1
                            # 保留重叠部分
                            overlap_start = max(0, len(current_sentence_chunk) - chunk_overlap)
                            current_sentence_chunk = current_sentence_chunk[overlap_start:] + sentence
                        else:
                            current_sentence_chunk = sentence
                    else:
                        current_sentence_chunk += sentence
                
                if current_sentence_chunk:
                    current_chunk = current_sentence_chunk
            else:
                # 检查是否需要分割
                if len(current_chunk) + len(para) > chunk_size:
                    chunks.append({
                        "content": current_chunk,
                        "index": chunk_index,
                        "type": "paragraph"
                    })
                    chunk_index += 1
                    # 保留重叠部分
                    overlap_start = max(0, len(current_chunk) - chunk_overlap)
                    current_chunk = current_chunk[overlap_start:] + para + "\n"
                else:
                    current_chunk += para + "\n"
        
        # 添加最后一个chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "index": chunk_index,
                "type": "paragraph"
            })
        
        return chunks
    
    async def index_file(
        self,
        file_id: int,
        file_path: str,
        file_extension: str,
        metadata: Dict[str, Any],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        use_parent_child: bool = True
    ) -> List[str]:
        """索引文件到ChromaDB"""
        from app.file_processor import FileProcessor
        
        # 提取文本内容
        processor = FileProcessor()
        content = await processor.process(file_path, file_extension)
        
        if not content:
            logger.warning(f"文件 {file_id} 没有提取到内容")
            return []
        
        # 文本分块
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)
        
        doc_ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        if use_parent_child:
            # 使用父子文档索引
            parent_id = f"parent_{file_id}"
            self.parent_child_indexer.add_parent(
                parent_id,
                content[:2000],  # 父文档存储前2000字符作为摘要
                {**metadata, "is_parent": True}
            )
        
        for chunk in chunks:
            # 生成文档ID
            doc_id = f"{file_id}_{chunk['index']}"
            doc_ids.append(doc_id)
            documents.append(chunk["content"])
            
            # 生成向量
            embedding = self._get_embedding(chunk["content"])
            embeddings.append(embedding)
            
            # 构建元数据
            chunk_metadata = {
                **metadata,
                "chunk_index": chunk["index"],
                "chunk_type": chunk["type"],
                "file_id": file_id
            }
            
            if use_parent_child:
                chunk_metadata["parent_id"] = parent_id
                self.parent_child_indexer.add_child(
                    doc_id, parent_id, chunk["content"], chunk_metadata
                )
            
            metadatas.append(chunk_metadata)
            
            # 更新Trie树
            keywords = jieba.analyse.extract_tags(chunk["content"], topK=10)
            for keyword in keywords:
                self.trie.insert(keyword, doc_id)
        
        # 批量添加到ChromaDB
        if documents:
            self.collection.add(
                ids=doc_ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            # 更新BM25索引
            self._update_bm25_index(documents, doc_ids)
        
        logger.info(f"文件 {file_id} 索引完成，共 {len(documents)} 个分块")
        return doc_ids
    
    def _update_bm25_index(self, documents: List[str], doc_ids: List[str]):
        """更新BM25索引"""
        # 对文档进行分词
        tokenized_docs = []
        for doc in documents:
            tokens = list(jieba.cut(doc))
            tokenized_docs.append(tokens)
        
        # 更新语料库
        self.corpus.extend(tokenized_docs)
        self.corpus_ids.extend(doc_ids)
        
        # 重建BM25索引
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
    
    def _vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """向量召回"""
        # 生成查询向量
        query_embedding = self._get_embedding(query)
        
        # 查询ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        vector_results = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                vector_results.append({
                    "id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i],  # 转换为相似度
                    "source": "vector"
                })
        
        return vector_results
    
    def _bm25_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """BM25关键词召回"""
        if not self.bm25 or not self.corpus:
            return []
        
        # 对查询进行分词
        query_tokens = list(jieba.cut(query))
        
        # BM25评分
        scores = self.bm25.get_scores(query_tokens)
        
        # 获取Top-K
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        bm25_results = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc_id = self.corpus_ids[idx]
                doc_content = " ".join(self.corpus[idx])
                
                bm25_results.append({
                    "id": doc_id,
                    "content": doc_content[:500],  # 截断内容
                    "metadata": {},
                    "score": float(scores[idx]),
                    "source": "bm25"
                })
        
        return bm25_results
    
    def _qa_search(self, query: str) -> List[Dict[str, Any]]:
        """QA缓存召回"""
        # 简单实现：使用查询哈希匹配
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        # 检查是否有相似的QA
        qa_results = []
        for cached_query, answer in self.qa_cache.items():
            # 使用简单的字符串相似度
            similarity = self._jaccard_similarity(query, cached_query)
            if similarity > 0.8:  # 相似度阈值
                qa_results.append({
                    "id": f"qa_{query_hash}",
                    "content": answer,
                    "metadata": {"cached_query": cached_query},
                    "score": similarity,
                    "source": "qa_cache"
                })
        
        return qa_results
    
    def _jaccard_similarity(self, s1: str, s2: str) -> float:
        """计算Jaccard相似度"""
        set1 = set(jieba.cut(s1))
        set2 = set(jieba.cut(s2))
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0
    
    def _reciprocal_rank_fusion(self, results_lists: List[List[Dict]], k: int = 60) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 融合排序
        k: 常数，防止高排名文档得分过高
        """
        scores = defaultdict(float)
        doc_info = {}
        
        for results in results_lists:
            for rank, doc in enumerate(results):
                doc_id = doc["id"]
                # RRF分数公式: 1 / (k + rank)
                scores[doc_id] += 1 / (k + rank)
                if doc_id not in doc_info:
                    doc_info[doc_id] = doc
        
        # 按分数排序
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        fused_results = []
        for doc_id, score in sorted_docs:
            doc = doc_info[doc_id].copy()
            doc["score"] = score
            doc["source"] = "fused"
            fused_results.append(doc)
        
        return fused_results
    
    def _bidirectional_match(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        双向匹配 - 同时考虑查询到文档和文档到查询的匹配度
        """
        query_keywords = set(jieba.analyse.extract_tags(query, topK=10))
        
        for doc in documents:
            # 文档关键词
            doc_keywords = set(jieba.analyse.extract_tags(doc["content"], topK=20))
            
            # 正向匹配度：查询词在文档中的覆盖度
            forward_match = len(query_keywords & doc_keywords) / len(query_keywords) if query_keywords else 0
            
            # 反向匹配度：文档词在查询中的覆盖度
            backward_match = len(query_keywords & doc_keywords) / len(doc_keywords) if doc_keywords else 0
            
            # F1分数作为双向匹配度
            if forward_match + backward_match > 0:
                bidirectional_score = 2 * forward_match * backward_match / (forward_match + backward_match)
            else:
                bidirectional_score = 0
            
            # 结合原有分数
            doc["score"] = doc["score"] * 0.5 + bidirectional_score * 0.5
            doc["forward_match"] = forward_match
            doc["backward_match"] = backward_match
        
        # 重新排序
        documents.sort(key=lambda x: x["score"], reverse=True)
        return documents
    
    def _expand_with_parent(self, results: List[Dict]) -> List[Dict]:
        """使用父子文档索引扩展结果"""
        expanded = []
        seen_parents = set()
        
        for doc in results:
            parent_id = doc.get("metadata", {}).get("parent_id")
            
            if parent_id and parent_id not in seen_parents:
                # 获取父文档信息
                parent_doc = self.parent_child_indexer.get_parent(doc["id"])
                if parent_doc:
                    expanded.append({
                        "id": parent_id,
                        "content": parent_doc["content"],
                        "metadata": {**doc["metadata"], "is_parent": True},
                        "score": doc["score"],
                        "source": "parent_expansion"
                    })
                    seen_parents.add(parent_id)
            
            expanded.append(doc)
        
        return expanded
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
        use_multi_reciprocal: bool = True,
        use_rerank: bool = True,
        use_parent_child: bool = True,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        查询RAG系统
        
        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            use_multi_reciprocal: 是否使用多路召回融合
            use_rerank: 是否使用双向匹配重排序
            use_parent_child: 是否使用父子文档扩展
            filters: 过滤条件
        """
        results = []
        
        if use_multi_reciprocal:
            # 多路召回
            vector_results = self._vector_search(query_text, top_k=top_k * 2)
            bm25_results = self._bm25_search(query_text, top_k=top_k * 2)
            qa_results = self._qa_search(query_text)
            
            # 使用RRF融合
            fused_results = self._reciprocal_rank_fusion(
                [vector_results, bm25_results, qa_results]
            )
            results = fused_results[:top_k * 2]
        else:
            # 仅使用向量召回
            results = self._vector_search(query_text, top_k=top_k)
        
        # 双向匹配重排序
        if use_rerank:
            results = self._bidirectional_match(query_text, results)
        
        # 父子文档扩展
        if use_parent_child:
            results = self._expand_with_parent(results)
        
        # 应用过滤
        if filters:
            filtered_results = []
            for doc in results:
                metadata = doc.get("metadata", {})
                match = True
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_results.append(doc)
            results = filtered_results
        
        # 返回Top-K
        final_results = results[:top_k]
        
        return {
            "query": query_text,
            "documents": final_results,
            "total_results": len(final_results)
        }
    
    def add_qa_pair(self, question: str, answer: str):
        """添加QA对到缓存"""
        self.qa_cache[question] = answer
        logger.info(f"添加QA缓存: {question[:50]}...")
    
    def dfs_tokenize(self, text: str) -> List[Dict[str, Any]]:
        """
        使用DFS算法对文本进行分词
        返回分词结果和词频统计
        """
        tokens = self.trie.tokenize_with_dfs(text)
        
        # 统计词频
        word_freq = defaultdict(int)
        for word, start, end in tokens:
            word_freq[word] += 1
        
        # 转换为列表格式
        result = []
        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True):
            # 获取包含该词的文档
            doc_ids = list(self.trie.get_doc_ids_for_word(word))
            result.append({
                "word": word,
                "frequency": freq,
                "document_ids": doc_ids[:10]  # 最多返回10个文档
            })
        
        return result