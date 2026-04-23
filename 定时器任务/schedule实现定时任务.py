


import schedule
import time
from threading import Thread

def job():
    print("I'm working...")

# 每隔5秒执行一次
schedule.every(5).seconds.do(job)

#每天的10:30执行一次
schedule.every().day.at("10:30").do(job)

# while True:
#     schedule.run_pending()
#     time.sleep(1)

# 在子线程中运行
def run():
    while True:
        schedule.run_pending()
        time.sleep(1)
    # schedule.run_all()
    # schedule.run_pending()

t = Thread(target=run)

t.setDaemon(True) # 设置为守护线程,当主线程结束时,子线程也会结束
t.start()


for i in range(50):
    time.sleep(1)

