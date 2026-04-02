"""
Python 线程是抢占式多任务，但 无法从外部安全地强制停止一个线程（调用 threading.Thread 的 join() 只能等待其自然结束）。
因此线程的中断通常依赖于协作式设计：线程定期检查一个标志，如果标志改变，则主动退出或切换行为。

使用 threading.Event 或标志变量
"""
import threading
import time

def worker(stop_event, new_task_event):
    while not stop_event.is_set():
        if new_task_event.is_set():
            print("New task received, switching...")
            new_task_event.clear()
            # 执行新任务
            execute_new_task()
            continue

        print("Working...")
        time.sleep(1)

def execute_new_task():
    print("Executing new task...")
    time.sleep(2)
    print("New task completed")

def user_input_listener(stop_event, new_task_event):
    while True:
        user_input = input("Enter command (n for new task, q to quit): ")
        if user_input == 'n':
            new_task_event.set()
        elif user_input == 'q':
            stop_event.set()
            break

def main():
    stop_event = threading.Event()
    new_task_event = threading.Event()

    worker_thread = threading.Thread(target=worker, args=(stop_event, new_task_event))
    listener_thread = threading.Thread(target=user_input_listener, args=(stop_event, new_task_event))

    worker_thread.start()
    listener_thread.start()

    worker_thread.join()
    listener_thread.join()

if __name__ == "__main__":
    main()