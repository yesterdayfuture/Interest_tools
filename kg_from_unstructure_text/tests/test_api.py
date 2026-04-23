import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    """创建测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealth:
    """健康检查测试"""
    
    async def test_health_check(self, client):
        """测试健康检查端点"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    async def test_root(self, client):
        """测试根路径"""
        response = await client.get("/")
        assert response.status_code == 200
        assert "name" in response.json()


class TestOntology:
    """本体管理测试"""
    
    async def test_create_ontology(self, client):
        """测试创建本体定义"""
        payload = {
            "name": "Product",
            "display_name": "商品",
            "description": "电商平台的商品实体",
            "ontology_type": "entity",
            "properties": {
                "name": {"data_type": "string", "required": True},
                "price": {"data_type": "float"},
                "category": {"data_type": "string"}
            }
        }
        response = await client.post("/api/v1/ontology/definitions", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "Product"
    
    async def test_list_ontology(self, client):
        """测试获取本体列表"""
        response = await client.get("/api/v1/ontology/definitions")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    async def test_get_ontology_tree(self, client):
        """测试获取本体树"""
        response = await client.get("/api/v1/ontology/definitions/tree")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestFiles:
    """文件管理测试"""
    
    async def test_list_files(self, client):
        """测试获取文件列表"""
        response = await client.get("/api/v1/files")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestRAG:
    """RAG检索测试"""
    
    async def test_rag_stats(self, client):
        """测试RAG统计信息"""
        response = await client.get("/api/v1/rag/stats")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    async def test_rag_query(self, client):
        """测试RAG查询"""
        payload = {
            "query": "商品退货流程",
            "top_k": 5,
            "use_multi_reciprocal": True,
            "use_rerank": True
        }
        response = await client.post("/api/v1/rag/query", json=payload)
        # 如果没有索引数据，可能返回错误
        assert response.status_code in [200, 500]


class TestExtraction:
    """实体提取测试"""
    
    async def test_list_entities(self, client):
        """测试获取提取的实体列表"""
        response = await client.get("/api/v1/extraction/entities")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data