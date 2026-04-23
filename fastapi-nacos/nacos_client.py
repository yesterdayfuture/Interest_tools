from nacos import NacosClient
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NacosServiceRegistry:
    def __init__(
        self,
        server_addr: str,
        namespace: str,
        service_name: str,
        ip: str,
        port: int,
        cluster_name: str = "DEFAULT",
        weight: float = 1.0,
        username: str = None,
        password: str = None
    ):
        self.service_name = service_name
        self.ip = ip
        self.port = port
        self.cluster_name = cluster_name
        self.weight = weight

        # 初始化 Nacos 客户端
        self.client = NacosClient(
            server_addresses=server_addr,
            namespace=namespace,
            username=username,
            password=password
        )
        self._heartbeat_thread = None
        self._stop_heartbeat = False

    def register(self):
        """注册服务实例"""
        try:
            self.client.add_naming_instance(
                service_name=self.service_name,
                ip=self.ip,
                port=self.port,
                cluster_name=self.cluster_name,
                weight=self.weight,
                enable=True,
                healthy=True
            )
            logger.info(f"✅ 服务注册成功: {self.service_name} {self.ip}:{self.port}")
        except Exception as e:
            logger.error(f"❌ 服务注册失败: {e}")

    def _heartbeat_job(self):
        """心跳任务：每5秒上报一次"""
        while not self._stop_heartbeat:
            try:
                self.client.send_heartbeat(
                    service_name=self.service_name,
                    ip=self.ip,
                    port=self.port,
                    cluster_name=self.cluster_name
                )
            except Exception as e:
                logger.warning(f"⚠️ 心跳异常: {e}")
            time.sleep(5)

    def start_heartbeat(self):
        """启动后台心跳线程"""
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_job,
            daemon=True
        )
        self._heartbeat_thread.start()
        logger.info("🔁 Nacos 心跳已启动")

    def deregister(self):
        """服务注销（优雅下线）"""
        try:
            self.client.remove_naming_instance(
                service_name=self.service_name,
                ip=self.ip,
                port=self.port
            )
            logger.info(f"🛑 服务已下线: {self.service_name}")
        except Exception as e:
            logger.error(f"❌ 服务下线失败: {e}")