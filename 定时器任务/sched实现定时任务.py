

import sched
import time

# 创建调度器对象
scheduler = sched.scheduler(time.time, time.sleep)

# 定义任务函数
def task():
    print("任务执行...")
    scheduler.enter(5, 1, task)  # 5秒后重复，相当于嵌套调用

# 添加任务到调度器
scheduler.enter(3, 1, task)  #第一次 3秒进入任务函数，开始执行

# 运行调度器
scheduler.run()





