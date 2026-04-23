from flask import Flask, send_file, make_response
from flask import render_template, Response, jsonify, request, stream_with_context
from datetime import datetime
import os
import time

# 引入工具模块信息
from utils import Config, attach_database_to_app

app = Flask(__name__)

# 配置数据库连接
attach_database_to_app(app)

# 引入初始化好的蓝图
from user_manager.user_manager_main import user_route

# 引入所有声明好的表结构
from user_manager.medols import *


# 在 Flask 应用上下文中执行 db.create_all() 来创建所有定义好的表
with app.app_context():
    Config.database.create_all()

# 添加蓝图
app.register_blueprint(user_route)


@app.route('/', methods=['GET', 'POST'])
def health():
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({"status": "OK", "time": time_str})


# 下载文件 方式一
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(Config.upload_folder, filename)
    if not os.path.exists(file_path):
        return "文件不存在", 404

    # as_attachment=True 是关键，强制浏览器下载而不是打开
    return send_file(file_path, as_attachment=True, download_name=filename)


# 下载文件 方式二
@app.route('/download-custom/<filename>', methods=['GET'])
def download_custom(filename):
    file_path = os.path.join(Config.upload_folder, filename)
    response = make_response(send_file(file_path, as_attachment=False))
    # 手动设置响应头，强制下载
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


# 模拟流式数据, 进行流式输出
@app.route('/stream')
def stream_numbers():
    def generate_numbers():
        for number in range(1, 6):
            # 模拟耗时操作
            time.sleep(1)
            # 使用 yield 返回数据块，换行符 \n 是客户端区分消息的常用约定
            yield f"当前数字是：{number}\n"
    # 关键步骤：用 Response 包装生成器
    return Response(generate_numbers(), content_type='text/plain;charset=utf-8')


# 在生成器函数中，若需访问 Flask 的全局对象（如 request、session），需用 stream_with_context 保持请求上下文
# 调用方式：curl -N 'http://127.0.0.1:8000/stream-greet?name=Flask'
@app.route('/stream-greet')
def stream_greet():
    def generate():
        name = request.args.get('name', 'World')
        for i in range(1, 6):
            time.sleep(1)
            yield f'<p>Hello, {name}!</p>'

    return Response(stream_with_context(generate()), content_type='text/plain;charset=utf-8')


# SSE 流式输出
@app.route('/events')
def stream_events():
    def event_stream():
        for i in range(1, 6):
            time.sleep(1)
            # SSE 数据格式： data: ...\n\n
            yield f"data: Server time: {time.ctime()}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == '__main__':
    # 原生启动方式
    # app.run(host='0.0.0.0', port=8000)

    # gunicorn 启动方式
    from gevent.pywsgi import WSGIServer

    http_server = WSGIServer(('127.0.0.1', 8000), app)
    http_server.serve_forever()