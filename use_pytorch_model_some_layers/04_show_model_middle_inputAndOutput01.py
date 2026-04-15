"""
展示模型中间的输入和输出的维度

pip install torchinfo
"""

from torchinfo import summary
import torch.nn as nn
import torch


# 定义模型
class MyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.fc = nn.Linear(32 * 32, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = torch.flatten(x, -2)
        x = self.fc(x)
        return x


model = MyCNN()
# 生成模型摘要（输入尺寸为3通道32x32图像）
# 生成详细模型摘要
summary(model,
        input_size=(1, 3, 32, 32),  # 包含batch_size
        col_names=("input_size", "output_size", "num_params"),
        depth=3)