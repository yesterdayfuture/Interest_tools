"""
视频处理任务管理系统
====================
功能：
1. 支持上传视频文件进行切分和关键帧提取
2. 多进程并行处理任务，最大并发数可配置
3. 实时任务进度监控和状态持久化
4. 超时自动终止机制
5. 提供 RESTful API 和前端界面

作者：AI Assistant
日期：2026
"""

import os
import uuid
import time
import cv2
import shutil
import signal
import json
from pathlib import Path
from multiprocessing import Process, Semaphore, Lock
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from moviepy.editor import VideoFileClip

# ===================== 核心配置 =====================
MAX_PARALLEL_TASKS = 2         # 最大并行任务数，限制同时处理的视频数量
TASK_TIMEOUT = 300              # 任务超时时间（秒），超过此时间的任务会被强制终止
MONITOR_INTERVAL = 1            # 监督进程检查间隔（秒）
SPLIT_DURATION = 10             # 视频切分时长（秒），每个分段视频的时长
FRAME_INTERVAL = 1              # 关键帧提取间隔（秒），每隔多少秒提取一帧
TASK_DIR = "./tasks"            # 任务数据存储目录
os.makedirs(TASK_DIR, exist_ok=True)  # 确保任务目录存在

# ===================== 全局任务管理 =====================
tasks = {}                      # 内存中的任务字典，用于快速查询（不包含 Process 对象）
task_lock = Lock()              # 任务锁，保护共享资源的多线程安全
semaphore = Semaphore(MAX_PARALLEL_TASKS)  # 信号量，控制最大并发任务数

app = FastAPI(title="视频处理任务系统（完整版）")

# 跨域中间件配置，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 允许所有来源访问（生产环境应该限制）
    allow_credentials=True,     # 允许携带认证信息
    allow_methods=["*"],        # 允许所有 HTTP 方法
    allow_headers=["*"],        # 允许所有请求头
)

# 静态文件服务（供前端下载/预览图片）
# 挂载 /tasks 路径到本地 TASK_DIR 目录，使得可以通过 HTTP 访问任务文件
app.mount("/tasks", StaticFiles(directory=TASK_DIR), name="tasks")

# ===================== 视频处理逻辑 =====================
def video_task_handler(task_id: str, video_path: str, task_data: dict):
    """
    视频处理任务主函数（在子进程中运行）
    
    参数:
        task_id: 任务唯一标识符
        video_path: 上传的视频文件路径
        task_data: 任务数据字典（包含状态、进度等信息）
    
    功能:
        1. 等待获取信号量（控制并发数）
        2. 将视频按固定时长切分成多个片段
        3. 对每个片段提取关键帧
        4. 实时更新任务状态到 JSON 文件
    
    并发控制:
        通过信号量控制，同一时间最多 MAX_PARALLEL_TASKS 个任务并发处理
        超出并发数的任务会等待，状态保持为 pending
    """
    # 获取信号量（如果达到最大并发数会阻塞等待）
    # 这样可以控制同一时间最多只有 MAX_PARALLEL_TASKS 个任务在处理
    semaphore.acquire()
    
    try:
        time.sleep(10)
        # 子进程中不需要更新共享的 tasks 字典，直接写入文件
        task_path = os.path.join(TASK_DIR, task_id)
        status_file = os.path.join(task_path, "status.json")
        
        # 创建分段视频和关键帧存储目录
        split_dir = os.path.join(task_path, "split_videos")
        frame_dir = os.path.join(task_path, "frames")
        os.makedirs(split_dir, exist_ok=True)
        os.makedirs(frame_dir, exist_ok=True)
        
        # 更新状态为运行中
        task_data["status"] = "running"
        task_data["progress"] = 0
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False)

        # 使用 moviepy 打开视频文件
        with VideoFileClip(video_path) as clip:
            total_duration = clip.duration  # 获取视频总时长
            total_parts = int(total_duration / SPLIT_DURATION) + 1  # 计算需要切分的段数
            current = 0  # 当前处理到的时间点（秒）
            part = 1     # 当前处理的段号
            frame_list = []  # 存储所有关键帧的路径

            task_data["total_parts"] = total_parts

            # 循环处理每个视频片段
            while current < total_duration:
                # 计算当前片段的结束时间
                end = min(current + SPLIT_DURATION, total_duration)
                
                # 截取视频片段
                sub_clip = clip.subclip(current, end)
                sub_video_path = os.path.join(split_dir, f"part_{part:03d}.mp4")
                
                # 保存视频片段（使用 H.264 编码和 AAC 音频）
                sub_clip.write_videofile(
                    sub_video_path, 
                    codec="libx264",      # 视频编码
                    audio_codec="aac",    # 音频编码
                    verbose=False,        # 关闭详细输出
                    logger=None           # 关闭日志
                )

                # 从该片段中提取关键帧
                frames = extract_frames(sub_video_path, frame_dir, part)
                frame_list.extend(frames)

                # 更新进度信息并写入状态文件
                task_data["current_part"] = part
                task_data["progress"] = int((part / total_parts) * 100)
                task_data["status"] = "running"
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump(task_data, f, ensure_ascii=False)

                current = end  # 移动到下一个时间段
                part += 1      # 段号递增

        # 任务完成，保存最终结果
        task_data["status"] = "completed"
        task_data["progress"] = 100
        task_data["data"] = {
            "total_parts": part - 1,          # 实际切分的段数
            "split_videos_dir": split_dir,    # 分段视频存储目录
            "frames_dir": frame_dir,          # 关键帧存储目录
            "frame_list": frame_list          # 所有关键帧的 URL 列表
        }
        # 移除不可序列化的字段（避免 JSON 序列化失败）
        task_data.pop("video_path", None)
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False)

    except Exception as e:
        # 任务失败，记录错误信息
        task_data["status"] = "failed"
        task_data["error"] = str(e)
        task_data.pop("video_path", None)
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False)
    finally:
        # 释放信号量，允许其他等待的任务执行
        semaphore.release()

def extract_frames(video_path, save_dir, part_num):
    """
    从视频中提取关键帧
    
    参数:
        video_path: 视频文件路径
        save_dir: 关键帧保存目录
        part_num: 视频片段编号（用于命名）
    
    返回:
        list: 关键帧的 URL 列表
    
    原理:
        根据 FRAME_INTERVAL 配置，每隔 N 秒提取一帧
        例如 FRAME_INTERVAL=1 表示每秒提取 1 帧
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)  # 获取视频帧率
    interval = int(fps * FRAME_INTERVAL)  # 计算帧间隔（每隔多少帧取一帧）
    count = 0       # 当前帧计数
    frame_idx = 0   # 关键帧编号
    frames = []     # 存储关键帧 URL
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # 每隔 interval 帧提取一帧
        if count % interval == 0:
            fname = f"part_{part_num:03d}_frame_{frame_idx:04d}.jpg"
            fp = os.path.join(save_dir, fname)
            cv2.imwrite(fp, frame)  # 保存为 JPG 格式
            
            # 生成完整的 HTTP URL，供前端直接访问
            task_id = os.path.basename(os.path.dirname(save_dir))
            frames.append(f"http://127.0.0.1:8000/tasks/{task_id}/frames/{fname}")
            frame_idx += 1
        
        count += 1
    
    cap.release()  # 释放视频资源
    return frames

# ===================== 监督进程 =====================
def task_monitor_daemon():
    """
    任务监督守护进程（独立进程运行）
    
    功能:
        1. 定期检查所有运行中的任务
        2. 检测超时任务并强制终止
        3. 更新任务状态文件
    
    运行方式:
        在主进程启动时创建，作为守护进程持续运行
    
    注意:
        信号量由子进程自己管理，监督进程不负责释放信号量
    """
    while True:
        time.sleep(MONITOR_INTERVAL)  # 每隔 MONITOR_INTERVAL 秒检查一次
        now = time.time()
        
        with task_lock:
            for task_id, info in list(tasks.items()):
                if info["status"] != "running":
                    continue
                
                cost = now - info["start_time"]  # 计算任务已运行时间
                
                # 如果任务运行时间超过超时阈值，强制终止
                if cost > TASK_TIMEOUT:
                    try:
                        os.kill(info["pid"], signal.SIGKILL)  # 发送 KILL 信号
                        info["status"] = "timeout"
                        info["error"] = f"任务超时 ({TASK_TIMEOUT}s)"
                        
                        # 更新状态文件，保持数据一致性
                        task_path = os.path.join(TASK_DIR, task_id)
                        status_file = os.path.join(task_path, "status.json")
                        with open(status_file, "w", encoding="utf-8") as f:
                            json.dump(info, f, ensure_ascii=False)
                    except:
                        # 忽略终止进程时的异常（可能进程已经不存在）
                        pass

# ===================== 接口定义 =====================
@app.post("/add_task")
async def add_task(file: UploadFile = File(...)):
    """
    添加新的视频处理任务
    
    请求参数:
        file: 上传的视频文件（multipart/form-data）
    
    返回:
        {
            "task_id": "任务 ID",
            "status": "pending"
        }
    
    处理流程:
        1. 生成唯一任务 ID 并创建任务目录
        2. 保存上传的视频文件
        3. 初始化任务状态并写入 JSON 文件
        4. 创建子进程处理视频任务（不阻塞，立即返回）
    
    并发控制说明:
        - 此接口不阻塞，可以不断添加任务
        - 子进程内部会等待信号量，控制最多 MAX_PARALLEL_TASKS 个任务并发处理
        - 超出并发数的任务状态保持为 pending，等待处理
    """
    task_id = str(uuid.uuid4())  # 生成 UUID 作为任务 ID
    task_path = os.path.join(TASK_DIR, task_id)
    os.makedirs(task_path, exist_ok=True)
    
    # 保存上传的视频文件
    video_path = os.path.join(task_path, "source.mp4")
    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 初始化任务数据（只包含可序列化的数据）
    task_data = {
        "task_id": task_id,
        "status": "pending",
        "start_time": time.time(),
        "progress": 0,
        "total_parts": 0,
        "current_part": 0,
        "error": None,
        "data": None
    }

    # 写入初始状态文件（持久化存储）
    status_file = os.path.join(task_path, "status.json")
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(task_data, f, ensure_ascii=False)

    # 内存中只保存简化版本，不包含 Process 对象（避免序列化问题）
    with task_lock:
        tasks[task_id] = {
            "status": "pending",
            "start_time": task_data["start_time"],
            "progress": 0
        }

    # 创建子进程处理视频任务（不阻塞，立即返回）
    # 子进程内部会等待信号量，控制并发数
    p = Process(target=video_task_handler, args=(task_id, video_path, task_data), daemon=True)
    p.start()
    
    # 记录进程 ID 和进程对象
    with task_lock:
        tasks[task_id]["pid"] = p.pid
        tasks[task_id]["process"] = p
    
    return {"task_id": task_id, "status": "pending"}

@app.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """
    取消指定的视频处理任务
    
    路径参数:
        task_id: 任务 ID
    
    返回:
        {"msg": "已取消"}
    
    异常处理:
        404: 任务不存在
        400: 任务已结束（无法取消）
    
    处理流程:
        1. 验证任务是否存在
        2. 检查任务状态是否允许取消
        3. 如果是运行中任务，发送 KILL 信号终止进程
        4. 更新任务状态为 cancelled
    """
    task_path = os.path.join(TASK_DIR, task_id)
    status_file = os.path.join(task_path, "status.json")
    
    # 检查任务是否存在
    if not os.path.exists(status_file):
        raise HTTPException(404, detail="任务不存在")
    
    # 读取当前状态
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            task_info = json.load(f)
    except Exception:
        raise HTTPException(500, detail="无法读取任务状态")
    
    # 检查任务是否已经结束
    if task_info.get("status") in ["completed", "failed", "timeout", "cancelled"]:
        raise HTTPException(400, detail=f"任务已结束，无法取消 (当前状态：{task_info.get('status')})")
    
    # 尝试终止进程
    with task_lock:
        if task_id in tasks and "pid" in tasks[task_id]:
            try:
                os.kill(tasks[task_id]["pid"], signal.SIGKILL)
            except:
                pass
    
    # 更新状态为取消
    task_info["status"] = "cancelled"
    task_info["error"] = "用户取消"
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(task_info, f, ensure_ascii=False)
    
    return {"msg": "已取消"}

@app.get("/tasks")
async def get_all_tasks():
    """
    获取所有任务列表
    
    返回:
        {
            "tasks": [
                {
                    "task_id": "任务 ID",
                    "status": "任务状态",
                    "progress": 进度百分比，
                    "data": {...}  # 仅当任务完成时存在
                },
                ...
            ]
        }
    
    实现方式:
        遍历 tasks 目录下的所有子目录，读取每个任务的 status.json 文件
        这种方式保证了即使服务重启也能获取到历史任务信息
    """
    result = []
    
    with task_lock:
        # 遍历 tasks 目录，读取每个任务的 status.json
        if os.path.exists(TASK_DIR):
            for task_id in os.listdir(TASK_DIR):
                task_path = os.path.join(TASK_DIR, task_id)
                
                # 跳过非目录项
                if not os.path.isdir(task_path):
                    continue
                
                status_file = os.path.join(task_path, "status.json")
                
                # 读取状态文件
                if os.path.exists(status_file):
                    try:
                        with open(status_file, "r", encoding="utf-8") as f:
                            task_info = json.load(f)
                        result.append(task_info)
                    except Exception:
                        # 如果读取失败，至少返回基本信息
                        result.append({"task_id": task_id, "status": "unknown"})
    
    return {"tasks": result}

# ===================== 服务启动 =====================
if __name__ == "__main__":
    # 启动监督守护进程
    monitor = Process(target=task_monitor_daemon, daemon=True)
    monitor.start()
    
    # 启动 FastAPI 服务
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)