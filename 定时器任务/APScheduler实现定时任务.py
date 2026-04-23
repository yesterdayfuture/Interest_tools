

from apscheduler.schedulers.background import BackgroundScheduler
import logging
import time
logging.basicConfig(level=logging.DEBUG)


# 定义一个任务函数
def job():
    print("任务执行...")

# 创建一个后台调度器
scheduler = BackgroundScheduler()

# 添加一个定时任务，每5秒执行一次
scheduler.add_job(job, 'interval', seconds=5)  # 每5秒执行

# 启动调度器
scheduler.start()


# 保持主线程运行
try:
    for i in range(40):
        time.sleep(1)
        print("主线程执行...")
except KeyboardInterrupt:
    scheduler.shutdown()





