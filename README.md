# 刷题工作区

## 入口

**入口地址：** `https://dsh.stillfloating.top/code/?tkn=<TOKEN>`（Token 存放于 `~/.config/secrets/code-web-token`，请勿写入公开仓库）

- 服务跑在香港的 VPS（4 核 / 8G），不再绕 SSH 隧道回 X230，省掉一整跳；
- 首次打开要再点一次「管理 → 信任」，因为工作区路径变了（/home/ubuntu/刷题）；
- X230 上留着一份自动备份，每 15 分钟从香港同步回来（`shiti-sync.timer`）；
- 香港服务器上的回退：`sudo systemctl restart vscode-web`。

## 中文界面

界面已经是中文（语言包 + 自托管翻译文件）。如果哪天又变回英文：

1. `F1` → `配置显示语言` → `中文(简体)` → 重启；
2. 还不行就在本机跑 `sudo systemctl restart vscode-web`；
3. 补丁丢失时跑 `sudo /usr/local/bin/vscode-web-nls-fix` 再重启。

原理：VS Code Web 的界面翻译默认从微软 CDN 拉取，那个 CDN 没给跨域头，浏览器静默失败就回退英文。我们把翻译文件放到了自己的 nginx（`/code/nls/…`），并把 `product.json` 的 `nlsCoreBaseUrl` 指过去。

## 怎么打开（网页版）

- 地址：`https://dsh.stillfloating.top/code/`
- 需要两样东西：
  1. 弹出 Basic Auth 时输 `zts` / 密码（存在 `~/.config/secrets/dsh-public.txt`）
  2. 页面地址后面带 token：`?tkn=<token>`，token 存在 `~/.config/secrets/code-web-token`
- 第一次打开会看到蓝色 **Restricted Mode** 横幅：点 `Manage` → `Trust`（“是的，我信任此文件夹的作者”）。信任状态按浏览器保存，点一次就够；不信任时扩展（clangd 补全）不会启动。
- 打开文件后等右下角 clangd 索引跑完（`bits/stdc++.h` 大约 10 秒），再按补全才有候选。

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

## 终端：fish + starship

- 默认 shell 已改成 fish（`/usr/bin/fish`），提示符由 starship 渲染：目录/分支/耗时/右侧时间，配色偏 Tokyo Night；
- 只用常见 Unicode 字符（`❯`），不依赖 Nerd Font，所以不会出现方框；
- 常用缩写：`ll`、`la`、`gs`、`gd`、`run`（跑 ./a.out）、`h`（hermes）、`hy`（hermes --yolo）；
- 配置文件：`~/.config/fish/config.fish`、`~/.config/starship.toml`；改完新开终端即生效。

## Hermes（AI agent，在香港服务器上）

```bash
hermes --version          # v0.22.5
hermes                     # 交互式
hermes --yolo              # 全自动：危险命令不再逐条确认
hermes chat -q "..." --yolo --max-turns 30
hy                         # 等价于 hermes --yolo
```

配置与密钥沿用 X230 那份（`~/.hermes/config.yaml` + `~/.hermes/.env`），默认模型 deepseek-v4-pro。
`--checkpoints` 可在破坏性文件操作前打快照，`/rollback` 恢复。
