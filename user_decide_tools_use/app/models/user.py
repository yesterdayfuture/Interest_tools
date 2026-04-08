"""
用户模型

定义用户相关的数据模型和业务逻辑。
"""

from datetime import datetime


class User:
    """
    用户模型类

    属性:
        user_id: 用户唯一标识符（UUID）
        username: 用户名
        password_hash: 密码的 SHA256 哈希值
        created_at: 用户创建时间
    """

    def __init__(self, user_id: str, username: str, password_hash: str):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.created_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "created_at": str(self.created_at)
        }
