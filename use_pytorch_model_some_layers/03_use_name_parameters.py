"""
学习 named_parameters 用法
"""
import torch.nn as nn
import torchvision.models as models

# 加载预训练模型
resnet = models.resnet18(pretrained=True)

# 输出网络层的名称 和 对应的网络层参数
for name, params in resnet.named_parameters():
    print(f"名字为{name}的参数为：{params}")
    params.requires_grad = False


# 查看参数 的状态是否改变
for name, params in resnet.named_parameters():
    print(f"名字为{name}的参数为：{params}")
    break

print("*"*50)
print(resnet)