#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Learning Schedule Generator Script
Generates a detailed, emoji-rich study plan.
"""

import random
from datetime import datetime

# Configurations
EMOJIS = ['📚', '🧠', '✍️', '💡', '⏰', '🎯', '🚀', '🎉', '✨', '💪']
MOTIVATIONAL_QUOTES = [
    "加油！你是最棒的！💪",
    "每天进步一点点！🌱",
    "坚持就是胜利！🏆",
    "知识改变命运！📖",
    "享受学习的乐趣吧！😄",
]
TIME_SLOTS = [
    "☀️ 上午精力充沛时段",
    "🌤️ 午后专注时刻",
    "🌙 晚间深度学习区"
]

def add_emoji(text):
    """Adds a random emoji to the start of the text."""
    return f"{random.choice(EMOJIS)} {text}"

def generate_daily_section(topic, time_slot, hours):
    """Generates a section for a specific time slot."""
    activities = []
    if "基础" in topic or len(topic) < 5:
        activities = [f"{topic} 基础知识阅读 ({hours//2}h)", f"观看相关视频教程 ({hours//2}h)"]
    else:
        activities = [f"深入探索 {topic} 核心概念", f"实践练习与案例分析"]
    
    lines = [add_emoji(time_slot)]
    for act in activities:
        lines.append(f"  • {act}")
    lines.append(f"  💬 {random.choice(MOTIVATIONAL_QUOTES)}")
    return "\n".join(lines)

def generate_schedule(subject, duration_days=1, daily_hours=4):
    """Main function to generate the full schedule."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    header = f"📅 日期：{date_str}\n🎯 主题：{subject}\n⏳ 周期：{duration_days}天\n⚡ 每日预计：{daily_hours}小时\n" + "="*30
    
    content_lines = [header]
    
    for day in range(1, duration_days + 1):
        content_lines.append(f"\n🗓️ 第 {day} 天")
        for slot in TIME_SLOTS:
            # Randomly assign hours for demo simplicity
            hours_in_slot = max(1, daily_hours // len(TIME_SLOTS))
            section = generate_daily_section(subject, slot, hours_in_slot)
            content_lines.append(section)
            content_lines.append("")
    
    footer = f"\n🎉 完成以上计划后，给自己一个小奖励吧！\n{'*' * 30}"
    content_lines.append(footer)
    
    return "\n".join(content_lines)

if __name__ == "__main__":
    import sys
    # Default values if no arguments
    topic = sys.argv[1] if len(sys.argv) > 1 else "通用学习"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    hours = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    
    try:
        plan = generate_schedule(topic, days, hours)
        print(plan)
    except Exception as e:
        print(f"❌ 生成计划时出错：{e}")
