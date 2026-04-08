#!/usr/bin/env python3
"""多进程调度器测试脚本."""

import asyncio
import sys
import time

# 设置日志级别
import logging
logging.basicConfig(level=logging.INFO)


async def test_multi_process_scheduler():
    """测试多进程调度器."""
    from app.services.multi_process_scheduler import multi_process_scheduler
    from app.services.task_service import TaskService
    from app.schemas.task import TaskCreate

    print("=" * 60)
    print("多进程调度器测试")
    print("=" * 60)

    # 启动调度器
    print("\n1. 启动多进程调度器...")
    await multi_process_scheduler.start()
    print("   调度器已启动")

    # 获取初始状态
    status = multi_process_scheduler.get_scheduler_status()
    print(f"\n2. 调度器初始状态:")
    print(f"   - 运行中: {status['running']}")
    print(f"   - 工作进程数: {status['alive_workers']}")
    print(f"   - 待处理任务: {status['pending_tasks']}")

    # 创建任务服务
    task_service = TaskService()

    # 提交多个不同类型的任务
    print("\n3. 提交测试任务...")

    task_types = [
        ("default", {"duration": 2}),
        ("cpu_intensive", {"iterations": 1000000}),
        ("io_simulation", {"operations": 3, "delay": 0.5}),
        ("data_processing", {"data_size": 5000}),
    ]

    task_ids = []
    for i, (task_type, payload) in enumerate(task_types):
        task_create = TaskCreate(
            name=f"Test Task {i+1}",
            description=f"A {task_type} test task",
            task_type=task_type,
            priority=5,
            payload=payload,
        )

        # 创建任务
        task = await task_service.create_task(task_create)
        print(f"   创建任务: {task.id} (类型: {task_type})")

        # 提交到调度器
        success = await multi_process_scheduler.submit_task(task)
        if success:
            print(f"   ✓ 任务 {task.id} 已提交到调度器")
            task_ids.append(str(task.id))
        else:
            print(f"   ✗ 任务 {task.id} 提交失败")

    # 等待任务执行
    print("\n4. 等待任务执行...")
    for i in range(10):
        await asyncio.sleep(1)
        status = multi_process_scheduler.get_scheduler_status()
        print(f"   第 {i+1} 秒 - 运行中: {status['running_tasks']}, "
              f"待处理: {status['pending_tasks']}, "
              f"已完成: {status['completed_tasks']}")

        if status['pending_tasks'] == 0 and status['running_tasks'] == 0:
            print("   所有任务已处理完成!")
            break

    # 获取最终状态
    print("\n5. 最终调度器状态:")
    status = multi_process_scheduler.get_scheduler_status()
    print(f"   - 工作进程数: {status['alive_workers']}")
    print(f"   - 待处理任务: {status['pending_tasks']}")
    print(f"   - 运行中任务: {status['running_tasks']}")
    print(f"   - 已完成任务: {status['completed_tasks']}")

    # 查看工作进程状态
    print("\n6. 工作进程详情:")
    for worker in status['workers']:
        print(f"   - {worker['worker_id']}: {worker['status']}, "
              f"完成任务: {worker['tasks_completed']}, "
              f"失败任务: {worker['tasks_failed']}")

    # 关闭调度器
    print("\n7. 关闭调度器...")
    await multi_process_scheduler.shutdown()
    print("   调度器已关闭")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    # 初始化数据库
    print("初始化数据库...")
    from app.db.session import init_db

    async def main():
        await init_db()
        success = await test_multi_process_scheduler()
        sys.exit(0 if success else 1)

    asyncio.run(main())
