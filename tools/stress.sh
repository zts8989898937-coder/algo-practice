#!/usr/bin/env bash
# 对拍：反复用 gen.py 生成随机数据，比较 sol 与 brute 的输出
# 用法：bash tools/stress.sh [sol.cpp] [brute.cpp]
#       N=500 bash tools/stress.sh        # 跑 500 组
set -uo pipefail

sol=${1:-sol.cpp}
brute=${2:-brute.cpp}
N=${N:-200}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

g++ -std=c++17 -O2 -o "$tmp/sol" "$sol" || exit 1
g++ -std=c++17 -O2 -o "$tmp/brute" "$brute" || exit 1

for ((i = 1; i <= N; ++i)); do
  python3 gen.py > "$tmp/in.txt" || { echo "gen.py 出错"; exit 1; }
  "$tmp/sol" < "$tmp/in.txt" > "$tmp/out1.txt"
  "$tmp/brute" < "$tmp/in.txt" > "$tmp/out2.txt"
  if ! diff -q "$tmp/out1.txt" "$tmp/out2.txt" > /dev/null; then
    echo "❌ 第 $i 组数据对不上"
    echo "---- 输入 ----"; cat "$tmp/in.txt"
    echo "---- sol ----";  cat "$tmp/out1.txt"
    echo "---- brute ----"; cat "$tmp/out2.txt"
    exit 1
  fi
done

echo "✅ $N 组全部一致"
