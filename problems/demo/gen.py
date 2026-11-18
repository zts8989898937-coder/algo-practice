import random
n = random.randint(1, 8)
print(n)
print(*[random.randint(-10, 10) for _ in range(n)])
