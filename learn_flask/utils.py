# 引入数据库orm
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


# 配置类
class Config:
    # 数据库客户端
    database = None
    upload_folder = './static'


# 数据库连接
def attach_database_to_app(app):
    """

    :param db: 配置类中接收数据库客户端的类变量
    :param app: flask的 Flask对象
    :return:
    """
    # 配置数据库连接URI
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://{os.getenv("pg_user")}:{os.getenv("pg_pass")}@{os.getenv("pg_url")}/{os.getenv("pg_db")}'
    # 为了性能，建议关闭这个追踪配置
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 数据库连接池配置
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,  # 连接池的大小，默认为5
        'pool_recycle': 3600,  # 连接回收时间（秒），避免数据库连接超时
        'pool_pre_ping': True,  # 使用前检查连接是否有效
    }

    Config.database = SQLAlchemy(app)

