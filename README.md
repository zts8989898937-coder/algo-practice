# 算法练习工作区

用 C++ 写题、运行样例和随机对拍，附带 VS Code 任务以及查询 Codeforces 题目和提交记录的 Python 工具。

## 从终端运行样例

需要 Bash 和支持 C++17 的 g++。从仓库根目录运行下列命令，示例会输出 `6`。

```bash
cd problems/demo
g++ -std=c++17 -O2 -g -Wall sol.cpp -o sol
printf '3\n1 2 3\n' | ./sol
```

开始新题时，把 `template.cpp` 复制为题目目录下的 `sol.cpp`。不定义 `LOCAL` 时从标准输入读数据。定义 `LOCAL` 时，模板会从当前目录的 `in.txt` 读数据，请先准备该文件。

## VS Code 运行与调试

在 VS Code 中打开仓库根目录。任务面板中的「编译当前文件」直接使用 `g++`。「编译并运行」、样例输入与键盘输入任务依赖本机的 `vsc-run`，两套 gdb 启动配置依赖 `vsc-debug-build`。这两个脚本在公开仓库中未随附。移植这些任务时需配置本机工具，也可以直接使用上面的终端流程。gdb 调试配置使用 VS Code 的 C/C++ 扩展和 gdb。

## 随机对拍

需要 Python 3。每个题目目录准备 `sol.cpp`、`brute.cpp` 和 `gen.py`。从仓库根目录进入示例目录运行：

```bash
cd problems/demo
N=200 bash ../../tools/stress.sh
```

两份输出不一致时，脚本会打印触发错误的输入和对应输出。

## Codeforces 工具

运行 `python3 tools/cf_tool.py --help` 查看题目查询、提交记录和建题目录命令。需要指定账号的查询可用 `CF_HANDLE` 配置。

## 2026-11-18 公开版更新

移除编辑器备份、已编译的示例程序和 Python 缓存，保留模板、示例源码与刷题工具。 [查看更新提交](https://github.com/zts8989898937-coder/algo-practice/commit/95b12e874dd539eb18b68e768f21eeabf004ea1f)

[公开范围](PUBLIC_SCOPE.md) · [架构说明](docs/ARCHITECTURE.md) · [后续路线](docs/ROADMAP.md)
