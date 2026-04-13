#!/usr/bin/env python3
''
Generate comprehensive fitness plans
''
import sys
import random

def generate_fitness_plan(keywords, topic):
    '''生成健身计划'''    
    # 生成标题
    titles = [
        '💪' + topic + '健身计划|详细训练方案',
        '🔥' + topic + '专业训练计划|附饮食建议',
        '🏋️‍♂️' + topic + '健身指南|科学训练方法'
    ]
    title = random.choice(titles)

    # 生成训练计划
    training_plans = {
        '初学者': [
            '周一: 胸部+三头肌',
            '周二: 背部+二头肌',
            '周三: 休息',
            '周四: 腿部',
            '周五: 肩部',
            '周六: 全身训练',
            '周日: 休息'
        ],
        '中级': [
            '周一: 胸部+三头肌',
            '周二: 背部+二头肌',
            '周三: 腿部',
            '周四: 肩部+核心',
            '周五: 全身训练',
            '周六: 有氧训练',
            '周日: 休息'
        ],
        '高级': [
            '周一: 胸部+三头肌',
            '周二: 背部+二头肌',
            '周三: 腿部',
            '周四: 肩部+核心',
            '周五: 全身训练',
            '周六: 有氧训练',
            '周日: 主动恢复'
        ]
    }

    # 生成饮食建议
    diet_advice = [
        '早餐: 燕麦+蛋白质+水果',
        '午餐: 鸡胸肉+糙米+蔬菜',
        '晚餐: 鱼肉+红薯+蔬菜',
        '加餐: 蛋白质奶昔+坚果'
    ]

    # 生成内容结构
    content = '# ' + title + '

'
    content += '## 训练计划
'
    content += '### 初学者计划
'
    for plan in training_plans['初学者']:
        content += f'- {plan}
'
    content += '
### 中级计划
'
    for plan in training_plans['中级']:
        content += f'- {plan}
'
    content += '
### 高级计划
'
    for plan in training_plans['高级']:
        content += f'- {plan}
'
    content += '
## 饮食建议
'
    for advice in diet_advice:
        content += f'- {advice}
'
    content += '
## 注意事项
'
    content += '- 逐渐增加训练强度
'
    content += '- 保证充足的休息
'
    content += '- 保持均衡的饮食
'
    content += '- 如有不适，立即停止训练
'
    return content

def main():
    if len(sys.argv) > 1:
        topic = sys.argv[1]
    else:
        topic = '健身'

    keywords = sys.argv[2:] if len(sys.argv) > 2 else []
    content = generate_fitness_plan(keywords, topic)
    print(content)

if __name__ == '__main__':
    main()