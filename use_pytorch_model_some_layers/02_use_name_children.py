"""
学习 named_children 的用法
"""
import torch.nn as nn
import torchvision.models as models

# 加载预训练模型
resnet = models.resnet18(pretrained=True)

# 输出网络层的名称 和 对应的网络层对象
for name, child in resnet.named_children():
    print(f"名字为{name}的网络层为：{child}")


print("*"*50)
print(resnet)