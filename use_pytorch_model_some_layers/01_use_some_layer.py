"""
直接获取模型前几层
"""
import torch.nn as nn
import torchvision.models as models

# 加载预训练模型
resnet = models.resnet18(pretrained=True)

# 方法1：使用list(model.children())获取前3层
features = nn.Sequential(*list(resnet.children())[:3])
print(features)

# # 方法2：直接指定要保留的层
# print("*"*50)
# resnet.fc = nn.Sequential()  # 移除全连接层
# print(resnet)

print("*"*50)
print(*list(resnet.children()))