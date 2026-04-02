import asyncio

async def worker(stop_event: asyncio.Event, new_task_event: asyncio.Event):
    while not stop_event.is_set():
        # 检查是否有新任务到达
        if new_task_event.is_set():
            print("New task received, switching...")
            # 执行新任务前重置事件
            new_task_event.clear()
            # 这里可以启动新任务（例如调用另一个协程）
            await execute_new_task()
            continue

        # 正常执行当前工作
        print("Working...")
        await asyncio.sleep(1)  # 模拟工作

async def execute_new_task():
    print("Executing new task...")
    await asyncio.sleep(2)
    print("New task completed")

async def user_input_listener(new_task_event: asyncio.Event):
    while True:
        user_input = await asyncio.to_thread(input, "Enter command (n for new task, q to quit): ")
        if user_input == 'n':
            new_task_event.set()
        elif user_input == 'q':
            break

async def main():
    stop_event = asyncio.Event()
    new_task_event = asyncio.Event()

    worker_task = asyncio.create_task(worker(stop_event, new_task_event))
    listener_task = asyncio.create_task(user_input_listener(new_task_event))

    await listener_task
    stop_event.set()
    await worker_task

asyncio.run(main())