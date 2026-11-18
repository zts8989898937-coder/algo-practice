# 算法练习工作区

提供 C++ 模板、样例运行、调试与对拍工具。VS Code、g++、gdb、Python 等依赖需要使用者自行准备；工具中的环境相关路径需要按自己的机器配置。

## 快速开始

1. 把 `template.cpp` 复制到 `problems/题目名/sol.cpp`
2. 同目录建 `in.txt`，粘贴题目样例输入
3. `Ctrl+Shift+B` 编译（`g++ -std=c++17 -O2 -g -Wall -DLOCAL`）
4. `Ctrl+Shift+P` → `Tasks: Run Task` → **运行（读 in.txt）** 跑样例
5. `F5` 启动 gdb 调试（程序会自动 `freopen("in.txt")`，直接带着样例跑）

## 常用快捷键

| 操作 | 快捷键 |
| --- | --- |
| 编译当前文件 | `Ctrl+Shift+B` |
| 命令面板 | `Ctrl+Shift+P` |
| 调试 | `F5` |
| 断点 | 行号左侧点一下 |
| 全局搜索 | `Ctrl+Shift+F` |
| 打开终端 | `` Ctrl+` `` |

## 对拍（找 WA 的利器）

每个题目目录放三个文件：`sol.cpp`（你的解）、`brute.cpp`（暴力）、`gen.py`（随机数据）。

```
Ctrl+Shift+P → Tasks: Run Task → 对拍（sol vs brute）
```

终端里跑或者改 `N=500 bash tools/stress.sh` 跑更多组；不一致时会直接打印出错的输入、两个程序的输出。

## 代码补全

用 clangd（比 C/C++ 扩展轻，索引快）。第一次打开某个文件会在右下角显示索引进度，等它跑完 `Ctrl+Space` 就有补全、跳转、悬停提示。

## 目录

```
template.cpp        刷题模板（复制它开始）
in.txt              根目录示例输入
problems/demo/      对拍示例（sol + brute + gen + in.txt）
tools/stress.sh     对拍脚本
tools/gen.py        随机数据模板
.vscode/            编译/运行/调试任务与 clangd 配置
.clangd             clangd 编译参数
```


## 框架与路线

见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)、[docs/ROADMAP.md](docs/ROADMAP.md) 和 [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md)。
