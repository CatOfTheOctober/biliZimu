# Bilibili Video Text Extractor (B站视频文字提取系统)

> 唯一支持的下载入口：`python 下载字幕.py`
>
> `python -m bilibili_extractor` / `bilibili-extractor` 仅保留兼容壳入口，不再执行下载逻辑。

## 快速开始

### 1. 环境准备
- Python 3.8+
- BBDown（建议放在 `tools/BBDown/BBDown.exe`）
- FFmpeg（建议放在 `tools/ffmpeg/bin/`）

### 2. 安装依赖
```bash
pip install -e .
```

可选 ASR 依赖（仅无字幕视频需要）：
```bash
pip install funasr
# 或
pip install openai-whisper
```

### 3. 运行
```bash
python 下载字幕.py
```

脚本为交互式：输入 B 站 URL 或 BV 号即可。

## 当前行为说明

- `下载字幕.py`：主入口，支持 API 字幕优先，失败后可走 ASR 兜底。
- `python -m bilibili_extractor`：仅提示迁移信息并退出（退出码 0）。
- 保留库能力：你仍可在代码中使用 `TextExtractor`、`BilibiliAPI` 等模块。

## Cookie 说明

- 推荐先执行：
```bash
tools/BBDown/BBDown.exe --login
```
- 登录后 Cookie 默认在 `tools/BBDown/BBDown.data`。
- `下载字幕.py` 会自动读取该 Cookie，以提升 AI 字幕获取成功率。

## 项目结构（关键部分）

```text
src/bilibili_extractor/
  __main__.py            # 兼容壳入口（仅提示，不下载）
  core/                  # 核心控制与模型
  modules/               # API、字幕、下载、ASR 等模块
  utils/                 # 工具模块
下载字幕.py               # 唯一下载入口（推荐）
```

## 开发调用示例

```python
from bilibili_extractor.core.config import Config
from bilibili_extractor.core.extractor import TextExtractor

config = Config()
extractor = TextExtractor(config)
result = extractor.extract("https://www.bilibili.com/video/BV1xxxx")
```

## 测试

```bash
# 建议设置路径后运行
set PYTHONPATH=src
pytest -q
```

## 文档索引

- 安装：`docs/INSTALLATION_GUIDE.md`
- Cookie：`docs/COOKIE_GUIDE.md`
- 结构：`docs/PROJECT_STRUCTURE.md`
- 状态：`docs/CURRENT_STATUS.md`
- 第二流程模型接入：`docs/EPISODE_DRAFT_LLM_SETUP.md`

## 逐期回看模块

这个仓库现在额外包含一个本地优先的“《睡前消息》逐期回看”骨架，目标是把单期节目整理为结构化数据，并导出可直接用于录制的视频资料包。

核心原则：

- `1` 条你的新视频对应 `1` 期原节目。
- 该期中的每条新闻都建卡，但只追踪原节目提到的直接主线。
- 后续信息源只采用官方来源与头部主流媒体补充。
- 信息不足时明确写“公开信息不足”，不用小道消息补空。

常用命令：

```bash
python -m episode_draft draft-from-bundle output/<bundle_dir>
python review.py init samples/my_episode.json
python review.py validate samples/episode_2019-11-07.sample.json
python review.py export samples/episode_2019-11-07.sample.json --output output/review_demo
python review.py list-sources
```

制作规范见：[docs/episode_workflow.md](docs/episode_workflow.md)

## 第二流程模型配置

`episode_draft` 现在支持从项目根目录 `.env` 自动读取本地和远程模型配置。推荐做法：

1. 复制 `.env.example` 为 `.env`
2. 填写 `DeepSeek` 的 `EPISODE_DRAFT_API_KEY`
3. 确认本地 `Ollama` 正在运行，并已拉取 `qwen2.5:3b`

推荐环境变量：

```text
MODELSCOPE_CACHE=D:\Model\Funasr_model\modelscope_cache
OLLAMA_MODELS=D:\Model\ollama
EPISODE_DRAFT_LOCAL_API_BASE=http://127.0.0.1:11434/v1
EPISODE_DRAFT_LOCAL_MODEL=qwen2.5:3b
EPISODE_DRAFT_API_BASE=https://api.deepseek.com/v1
EPISODE_DRAFT_API_MODEL=deepseek-chat
EPISODE_DRAFT_API_KEY=<your_key>
```

运行示例：

```bash
python -m episode_draft draft-from-bundle output/<bundle_dir> --backend auto
python -m episode_draft doctor
```

- `auto`：优先本地 `Qwen2.5:3b`，必要时再走 `DeepSeek`
- `local`：只用本地模型
- `api`：只用远程模型
- `heuristic`：完全不用大模型
- `doctor`：检查 `.env`、本地 `Ollama` 和远程 `DeepSeek` 是否可用
