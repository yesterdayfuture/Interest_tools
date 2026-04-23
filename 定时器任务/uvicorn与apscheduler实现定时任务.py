
from fastapi import FastAPI, status
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
import uvicorn
import logging

# 创建FastAPI应用
app = FastAPI()

# 创建定时任务配置模型
scheduler = BackgroundScheduler()

#设置日志级别
logging.basicConfig(level=logging.INFO)


def task1():
    logging.info("执行任务1")
    print("执行任务1")

def task2():
    logging.info("执行任务2")
    print("执行任务2")


#任务函数字典
func_dict = {
    "task1": task1,
    "task2": task2
}

# 创建定时任务配置模型
class TaskConfig(BaseModel):
    # 任务函数名
    task_id: str
    # 任务间隔时间（秒）
    interval_seconds: int = 60

def job_executor(task_id: str):
    logging.info(f"执行任务: {task_id}")
    # 根据任务函数名调用对应的函数
    func_dict[task_id]()

# 启动定时任务
@app.post("/task/start")
def start_task(config: TaskConfig):
    if scheduler.get_job(config.task_id):
        return {"status": "error", "message": "任务已存在"}
    
    scheduler.add_job(
        job_executor,
        'interval',
        seconds=config.interval_seconds,
        id=config.task_id,
        args=[config.task_id]
    )
    return {"status": "success", "task_id": config.task_id}

# 停止定时任务
@app.post("/task/stop/{task_id}")
def stop_task(task_id: str):
    if not scheduler.get_job(task_id):
        return {"status": "error", "message": "任务不存在"}, status.HTTP_404_NOT_FOUND
    
    scheduler.remove_job(task_id)
    return {"status": "success", "task_id": task_id}

# 查看定时任务列表
@app.get("/task/list")
def list_tasks():
    jobs = [{"id": job.id, "next_run": str(job.next_run_time)} 
            for job in scheduler.get_jobs()]
    return {"tasks": jobs}


if __name__ == "__main__":
    # 启动任务调度器
    scheduler.start()
    #启动 uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
