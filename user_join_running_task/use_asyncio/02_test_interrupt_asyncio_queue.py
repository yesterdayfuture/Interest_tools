"""
使用队列，让协程从队列中获取命令，根据命令决定行为
"""
import asyncio

async def worker(command_queue: asyncio.Queue):
    while True:
        try:
            # 尝试获取命令，超时则执行默认工作
            cmd = await asyncio.wait_for(command_queue.get(), timeout=1)
        except asyncio.TimeoutError:
            # 没有命令时执行默认工作
            print("Working...")
            await asyncio.sleep(1)
            continue

        if cmd == "new_task":
            print("Switching to new task...")
            await asyncio.sleep(2)  # 模拟新任务
            print("New task finished")
        elif cmd == "quit":
            break

async def user_input_listener(command_queue: asyncio.Queue):
    while True:
        user_input = await asyncio.to_thread(input, "Enter command (n for new task, q to quit): ")
        if user_input == 'n':
            await command_queue.put("new_task")
        elif user_input == 'q':
            await command_queue.put("quit")
            break

async def main():
    command_queue = asyncio.Queue()
    worker_task = asyncio.create_task(worker(command_queue))
    listener_task = asyncio.create_task(user_input_listener(command_queue))
    await listener_task
    await worker_task

asyncio.run(main())