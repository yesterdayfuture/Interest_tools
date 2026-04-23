from utils import Config


# 声明数据库表结构
class User(Config.database.Model):
    # 定义表名，不写则默认使用类名的小写
    __tablename__ = 'flask_users'

    id = Config.database.Column(Config.database.Integer, primary_key=True)
    username = Config.database.Column(Config.database.String(80), unique=True, nullable=False)
    email = Config.database.Column(Config.database.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'