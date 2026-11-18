#!/usr/bin/env python3
# 随机数据生成器模板：对拍时 stress.sh 会调用它，输出打到 stdout。
# 按题目改写即可（下面以「n 个整数求和」为例）。
import random
import sys

n = random.randint(1, 8)
nums = [random.randint(-10, 10) for _ in range(n)]
print(n)
print(*nums)
