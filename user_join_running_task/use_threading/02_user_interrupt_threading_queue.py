"""
类似协程版本，线程也可以使用 queue.Queue 来传递命令
"""
import threading
import queue
import time

def worker(cmd_queue: queue.Queue):
    while True:
        try:
            cmd = cmd_queue.get(timeout=1)
        except queue.Empty:
            # 无命令时执行默认工作
            print("Working...")
            time.sleep(1)
            continue

        if cmd == "new_task":
            print("Switching to new task...")
            time.sleep(2)
            print("New task finished")
        elif cmd == "quit":
            break

def user_input_listener(cmd_queue: queue.Queue):
    while True:
        user_input = input("Enter command (n for new task, q to quit): ")
        if user_input == 'n':
            cmd_queue.put("new_task")
        elif user_input == 'q':
            cmd_queue.put("quit")
            break

def main():
    cmd_queue = queue.Queue()
    worker_thread = threading.Thread(target=worker, args=(cmd_queue,))
    listener_thread = threading.Thread(target=user_input_listener, args=(cmd_queue,))

    worker_thread.start()
    listener_thread.start()

    worker_thread.join()
    listener_thread.join()

if __name__ == "__main__":
    main()