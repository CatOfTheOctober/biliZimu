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
